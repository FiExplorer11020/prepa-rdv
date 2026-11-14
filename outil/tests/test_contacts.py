import json
from pathlib import Path

import pytest

from prepa_rdv import contacts
from prepa_rdv.resolveur import Entite

TEXTE = ("Relations investisseurs. Investor Relations : investors@exemple.com. "
         "Anna Berg, Investor Relations : anna.berg@exemple.com. Lars Ek, Press : lars.ek@exemple.com. "
         "Autre domaine : john.doe@ailleurs.org.")


def cache(tmp_path: Path, texte=TEXTE, url="https://www.exemple.com/investors/contact"):
    (tmp_path / "a.json").write_text(json.dumps({"url": url, "url_finale": url, "texte": texte}), encoding="utf-8")
    return tmp_path


def fiche(nom="Maria Holm, directrice financière", niveau="confirmé", age=3, type_source="P1", contradiction=False):
    return {"synthese": {"direction_financiere": {"niveau": niveau, "contradiction": contradiction,
                                                    "valeurs": [{"valeur": nom, "ids": ["t1"]}]}},
            "trouvailles": [{"id": "t1", "verifs": {"age_mois": age, "type_source_code": type_source}}]}


ENTITE = Entite(nom_saisi="Exemple", nom_retenu="Exemple SA", pays="France", domaines=["exemple.com"])


def test_releve_les_adresses_du_domaine_de_la_societe(tmp_path):
    a = contacts.relever(contacts._pages_de_la_societe(cache(tmp_path), ENTITE.domaines), ENTITE.domaines)
    adresses = {x["adresse"]: x for x in a}
    assert "john.doe@ailleurs.org" not in adresses
    assert adresses["investors@exemple.com"]["generique"] and not adresses["anna.berg@exemple.com"]["generique"]
    assert adresses["anna.berg@exemple.com"]["nom"] == "Anna Berg"


def test_motif_d_apres_le_nom_ecrit_a_cote():
    assert contacts.motif("anna.berg", "Anna Berg") == "prenom.nom"
    assert contacts.motif("berg.anna", "Anna Berg") == "nom.prenom"
    assert contacts.motif("a.berg", "Anna Berg") == "p.nom"
    assert contacts.motif("investors", None) is None


def test_suggestion_avec_deux_adresses_au_meme_motif(tmp_path, monkeypatch):
    monkeypatch.setattr(contacts, "mx_existe", lambda d: True)
    c = contacts.construire(fiche(), ENTITE, cache(tmp_path))
    assert c["generiques"] == ["investors@exemple.com"]
    assert c["suggestion"]["adresse"] == "maria.holm@exemple.com" and c["suggestion"]["mention"] == "déduite, non vérifiée"
    assert "déduite, non vérifiée" in contacts.ligne(c)


def test_pas_de_suggestion_avec_une_seule_adresse_nominative(tmp_path, monkeypatch):  # cas de Verallia
    monkeypatch.setattr(contacts, "mx_existe", lambda d: True)
    texte = "Investor Relations : investors@exemple.com. David Placet, Investor relations contact : david.placet@exemple.com."
    c = contacts.construire(fiche(), ENTITE, cache(tmp_path, texte))
    assert c["suggestion"] is None and c["generiques"] == ["investors@exemple.com"]


def test_pas_de_suggestion_sans_mx(tmp_path, monkeypatch):
    monkeypatch.setattr(contacts, "mx_existe", lambda d: False)
    assert contacts.construire(fiche(), ENTITE, cache(tmp_path))["suggestion"] is None


@pytest.mark.parametrize("kw", [dict(age=18), dict(type_source="P3"), dict(niveau="non trouvé"), dict(contradiction=True), dict(nom="Direction financière")])
def test_pas_de_suggestion_si_le_dirigeant_n_est_pas_bien_etabli(tmp_path, monkeypatch, kw):
    monkeypatch.setattr(contacts, "mx_existe", lambda d: True)
    assert contacts.construire(fiche(**kw), ENTITE, cache(tmp_path))["suggestion"] is None


def test_interrupteur(tmp_path):
    assert contacts.construire(fiche(), ENTITE, cache(tmp_path), sans_contacts=True) is None
    assert contacts.ligne(None) is None


def test_mention_pour_l_allemagne(tmp_path, monkeypatch):
    monkeypatch.setattr(contacts, "mx_existe", lambda d: True)
    de = Entite(nom_saisi="Exemple", pays="Germany", domaines=["exemple.com"])
    c = contacts.construire(fiche(), de, cache(tmp_path))
    assert "consentement préalable" in contacts.ligne(c)
