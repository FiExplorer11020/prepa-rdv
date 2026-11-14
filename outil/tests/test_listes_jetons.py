import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from prepa_rdv.jetons import Registre, cout_estime, totaux
from prepa_rdv.jetons_dev import importer, lire_appels
from prepa_rdv.listes import normaliser_valeur
from prepa_rdv.schema import Champ


# --- Listes fermées --------------------------------------------------------------------------

@pytest.mark.parametrize("champ, valeur, attendu", [
    (Champ.ERP, "SAP S/4HANA", "SAP S/4HANA"),
    (Champ.ERP, "RISE with SAP", "SAP S/4HANA"),
    (Champ.ERP, "SAP S/4HANA Cloud sur Microsoft Azure", "SAP S/4HANA"),
    (Champ.ERP, "SAP S/4 HANA", "SAP S/4HANA"),
    (Champ.ERP, "SAP R/3", "SAP ECC"),
    (Champ.ERP, "Une maison maison inconnue", "autre"),
    (Champ.ACHATS, "SAP Business Network", "SAP Ariba"),
    (Champ.ACHATS, "Ariba", "SAP Ariba"),
    (Champ.TMS, "Kyriba", "Kyriba"),
    (Champ.TMS, "Reval", "ION"),
    (Champ.FINANCEMENT, "Dynamic Discounting", "Escompte dynamique"),
    (Champ.FINANCEMENT, "supply chain finance programmes", "Affacturage inversé (supply chain finance)"),
    (Champ.FINANCEMENT, "non-recourse factoring", "Affacturage sans recours"),
    (Champ.FINANCEMENT, "factoring", "Affacturage (recours non précisé)"),
    (Champ.FINANCEMENT, "receivables securitisation programme", "Titrisation de créances"),
])
def test_normaliser_valeur(champ, valeur, attendu):
    assert normaliser_valeur(champ, valeur)[0] == attendu


def test_une_valeur_autre_garde_son_nom():
    valeur, precision = normaliser_valeur(Champ.ERP, "Prodigy 9000")
    assert valeur == "autre" and precision == "Prodigy 9000"


def test_un_champ_libre_n_est_pas_modifie():
    assert normaliser_valeur(Champ.DIRECTION_FINANCIERE, " Jeanne Martin ")[0] == "Jeanne Martin"


# --- Coût estimé -----------------------------------------------------------------------------

def test_cout_sonnet():
    # 1 M en entrée (2 $) + 1 M en sortie (10 $) + 1 M lus en cache (0,10 $)
    assert cout_estime("claude-sonnet-5-5", 1_000_000, 1_000_000, 1_000_000) == pytest.approx(12.10)


def test_cout_ecriture_du_cache():
    assert cout_estime("claude-sonnet-5-5", cache_ecrit_5m=1_000_000) == pytest.approx(2.5)
    assert cout_estime("claude-sonnet-5-5", cache_ecrit_1h=1_000_000) == pytest.approx(4.0)


def test_cout_recherches():
    assert cout_estime("claude-opus-5-5", recherches_web=100) == pytest.approx(1.0)


def test_cout_haiku_palier_long():
    court = cout_estime("claude-haiku-5-5", 50_000, 1_000)
    long = cout_estime("claude-haiku-5-5", 150_000, 1_000)
    assert long > court * 3


def test_modele_inconnu():
    assert cout_estime("modele-inconnu", 10, 10) is None


def test_identifiant_date_reconnu_par_prefixe():
    assert cout_estime("claude-sonnet-5-5-20261001", 1_000_000) == pytest.approx(2.0)


# --- Registre --------------------------------------------------------------------------------

def test_registre_en_ajout_seul(tmp_path):
    r = Registre(tmp_path / "j.jsonl")
    r.ajouter(phase="essai", societe="A", entree=10, sortie=5, cache_lu=100, cache_ecrit=0, recherches_web=1, cout_estime_usd=0.5)
    r.ajouter(phase="run", societe="A", entree=20, sortie=5, cache_lu=0, cache_ecrit=7, recherches_web=0, cout_estime_usd=0.25)
    r.ajouter(phase="run", societe="B", entree=1, sortie=1, cout_estime_usd=0.01)
    assert len(r.lignes()) == 3
    par_phase = {t["phase"]: t for t in totaux(r.lignes(), ("phase",))}
    assert par_phase["run"]["entree"] == 21 and par_phase["run"]["appels"] == 2
    assert par_phase["essai"]["cout_estime_usd"] == 0.5


# --- Transcriptions de Claude Code -----------------------------------------------------------

def ligne(mid, ts, usage, modele="claude-sonnet-5-5"):
    return json.dumps({"type": "assistant", "timestamp": ts, "uuid": mid + ts,
                       "message": {"id": mid, "model": modele, "usage": usage}})


def test_lire_appels_depouille_les_iterations_et_les_doublons(tmp_path):
    f = tmp_path / "s.jsonl"
    vide = {"input_tokens": 0, "output_tokens": 0, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0,
            "iterations": [{"type": "message", "input_tokens": 2, "output_tokens": 100, "cache_read_input_tokens": 5000,
                            "cache_creation_input_tokens": 300, "cache_creation": {"ephemeral_1h_input_tokens": 300, "ephemeral_5m_input_tokens": 0}}]}
    f.write_text("\n".join([
        ligne("m1", "2026-11-13T10:00:00.000Z", vide),
        ligne("m1", "2026-11-13T10:00:01.000Z", vide),  # deuxième bloc du même message
        ligne("m2", "2026-11-13T10:01:00.000Z", {"input_tokens": 3, "output_tokens": 10, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}),
        json.dumps({"type": "user", "message": {"role": "user"}}),
        ligne("m3", "2026-11-13T10:02:00.000Z", {"input_tokens": 1, "output_tokens": 1}, modele="<synthetic>"),
    ]), encoding="utf-8")
    appels = lire_appels(f)
    assert len(appels) == 2
    m1 = next(a for a in appels if a["output_tokens"] == 100)
    assert m1["cache_read_input_tokens"] == 5000 and m1["cache_1h"] == 300


def test_importer_separe_phases_et_portees(tmp_path):
    projet = tmp_path / "projet"
    (projet / "abc" / "subagents").mkdir(parents=True)
    u = {"input_tokens": 1, "output_tokens": 10, "cache_read_input_tokens": 100, "cache_creation_input_tokens": 0}
    (projet / "abc.jsonl").write_text("\n".join([
        ligne("a", "2026-11-13T10:00:00.000Z", u), ligne("b", "2026-11-13T21:40:00.000Z", u)]), encoding="utf-8")
    (projet / "abc" / "subagents" / "agent-xyz.jsonl").write_text(ligne("c", "2026-11-13T11:00:00.000Z", u), encoding="utf-8")
    (projet / "ancienne.jsonl").write_text(ligne("d", "2026-10-28T10:00:00.000Z", u), encoding="utf-8")
    debut = datetime(2026, 11, 13, 21, 36, tzinfo=timezone.utc)
    lignes = importer(projet, debut)
    par = {(l["session"], l["agent"], l["phase"]): l for l in lignes}
    assert ("abc", "principal", "planification") in par and ("abc", "principal", "construction") in par
    assert ("abc", "sous-agent-xyz", "planification") in par
    assert par[("ancienne", "principal", "hors-cas")]["portee"] == "hors-cas"
    assert sum(l["appels"] for l in lignes if l["portee"] == "cas") == 3


@pytest.mark.parametrize("brut, attendu", [
    ("Aprovall : plateforme KYS (Know Your Supplier) de collecte et d'exploitation des données fournisseurs", "Aprovall"),
    ("Nomentia. Page client de l'éditeur, sans date, qui reprend les phrases de l'article de 2019", "Nomentia"),
    ("SAP ERP, version non précisée par la page (ni ECC ni S/4HANA nommés). Migration des données", "SAP ERP"),
    ("SAP (produit et version non précisés dans la source ; SAP est cité aux côtés de Salesforce ; article de 2017)", "SAP"),
    ("Committed back-stop facilities, lignes de crédit confirmées de soutien", "Committed back-stop facilities"),
    ("Betriebskredite (crédits d'exploitation), 124,5 M CHF : cause principale de la variation", "Betriebskredite (crédits d'exploitation)"),
    ("Plateforme de gestion des fournisseurs et des contrats de la société", "Plateforme de gestion des fournisseurs"),
    ("Kyriba", "Kyriba"),
])
def test_nom_court_garde_le_nom_et_laisse_le_commentaire(brut, attendu):
    from prepa_rdv.listes import nom_court
    assert nom_court(brut) == attendu


def test_personne_courte_garde_le_titre_et_la_date_mais_pas_la_remarque():
    from prepa_rdv.listes import personne_courte
    assert personne_courte("Joop Jansen, Senior Vice President Finance de Deutsche Telekom IT (filiale informatique, pas le groupe)") \
        == "Joop Jansen, Senior Vice President Finance de Deutsche Telekom IT"
    assert personne_courte("Dhananjay Mirchandani, directeur financier désigné (CFO), en fonction à compter du 1er mai 2027") \
        == "Dhananjay Mirchandani, directeur financier désigné (CFO), en fonction à compter du 1er mai 2027"


def test_les_initiales_et_les_titres_ne_coupent_pas_un_nom():
    from prepa_rdv.listes import nom_court, personne_courte
    assert personne_courte("Christian P. Illek, membre du directoire responsable des finances") == "Christian P. Illek, membre du directoire responsable des finances"
    assert personne_courte("Dr. Hans Müller, Finanzvorstand") == "Dr. Hans Müller, Finanzvorstand"
    assert nom_court("Prof. Müller GmbH. Page d'accueil") == "Prof. Müller GmbH"
