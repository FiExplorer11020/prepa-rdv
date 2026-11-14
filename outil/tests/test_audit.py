"""Audit par un sous-agent : demande à l'aveugle du niveau, réponse validée, verdicts dans la feuille « Audit ». Hors ligne."""
import json

import pytest
from openpyxl import load_workbook

from prepa_rdv import audit, jetons_dev, sous_agents, tableur
from prepa_rdv.modele import ErreurModele


def _fiche(societe: str, n: int) -> dict:
    """Une fiche minimale : une valeur par champ de la cartographie, chacune avec sa trouvaille."""
    trouvailles, synthese = [], {}
    for k, champ in enumerate(tableur.CHAMPS_CARTO):
        tid = f"{societe.lower()}-{champ.value}-{k}"
        trouvailles.append({"id": tid, "citation": f"{societe} runs product {k}", "url": f"https://{societe.lower()}.example/{k}",
                            "verifs": {"citation_trouvee": True}})
        synthese[champ.value] = {"niveau": "probable", "valeurs": [{"valeur": f"Produit {k}", "precision": None, "niveau": "probable",
                                                                    "ids": [tid], "statut": "en_place"}]}
    return {"societe": societe, "trouvailles": trouvailles, "synthese": synthese, "date_fiche": "2026-11-14", "version_outil": "0",
            "jetons": {}, "entite": {"pays": "Finland", "statut": "coté", "isin": [], "lei": None, "site": None}}


@pytest.fixture
def sorties(tmp_path, monkeypatch):
    monkeypatch.setenv("PREPA_RDV_SORTIES", str(tmp_path))
    return tmp_path


@pytest.fixture
def fiches():
    return [_fiche(s, i) for i, s in enumerate(["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Eta"])]


def _jugement(i: str, verdict: str = "juste", ecart=None, ouverte: bool = True) -> dict:
    return {"id": i, "page_ouverte": ouverte, "citation_presente": True if ouverte else None, "verdict": verdict, "ecart": ecart,
            "raison": "La page le dit.", "passage": "runs product"}


def _repondre(sorties, k: int, transformer=lambda js: js) -> list[str]:
    demande = json.loads((sorties / "audit" / f"demande-{k}.json").read_text(encoding="utf-8"))
    ids = [c["id"] for c in demande["cellules"]]
    (sorties / "audit" / f"sortie-{k}.json").write_text(json.dumps({"jugements": transformer([_jugement(i) for i in ids])}), encoding="utf-8")
    return ids


def test_la_demande_reprend_le_tirage_sans_le_niveau(sorties, fiches):
    chemins = audit.ecrire_demandes(fiches, n=3)
    assert len(chemins) == 3
    tirage = tableur.echantillon_audit(fiches)
    demandes = [json.loads((sorties / "audit" / f"demande-{k}.json").read_text(encoding="utf-8")) for k in (1, 2, 3)]
    assert [c["id"] for d in demandes for c in d["cellules"]] == [c["id"] for c in tirage]   # le tirage de la feuille, dans l'ordre
    assert all("niveau" not in c for d in demandes for c in d["cellules"])                   # l'auditeur juge à l'aveugle du niveau
    texte = chemins[0].read_text(encoding="utf-8")
    assert "probable" not in texte and "confirmé" not in texte
    assert str((sorties / "audit" / "sortie-1.json").resolve()) in texte and "WebSearch" in texte and "invérifiable" in texte


def test_recevoir_valide_ecrit_les_verdicts_et_compte_l_agent_dans_la_phase_audit(sorties, fiches):
    audit.ecrire_demandes(fiches, n=3)
    ids = _repondre(sorties, 1, lambda js: [*js[:-1], _jugement(js[-1]["id"], "partiel", "filiale ou division")])
    r = audit.recevoir(1, agent_id="aud1")
    assert r["juste"] == len(ids) - 1 and r["partiel"] == 1 and r["ecarts"] == {"filiale ou division": 1}
    v = json.loads((sorties / "audit" / "verdicts.json").read_text(encoding="utf-8"))
    assert set(v["premier"]["jugements"]) == set(ids) and v["premier"]["jugements"][ids[0]]["societe"]   # société et champ gardés
    ligne = sous_agents.correspondance()["aud1"]
    assert ligne["phase"] == "audit" and ligne["societe"] == ""


@pytest.mark.parametrize("transformer, motif", [
    (lambda js: js[1:], "sans jugement"),
    (lambda js: [*js, js[0]], "jugée 2 fois"),
    (lambda js: [{**js[0], "id": "inconnue"}, *js[1:]], "hors du lot"),
    (lambda js: [_jugement(js[0]["id"], "faux"), *js[1:]], "sans écart"),
    (lambda js: [_jugement(js[0]["id"], "juste", "extrapolation"), *js[1:]], "avec un écart"),
    (lambda js: [{**_jugement(js[0]["id"]), "page_ouverte": False}, *js[1:]], "page fermée"),
])
def test_une_reponse_incoherente_est_refusee(sorties, fiches, transformer, motif):
    audit.ecrire_demandes(fiches, n=3)
    _repondre(sorties, 2, transformer)
    with pytest.raises(ErreurModele, match=motif):
        audit.recevoir(2, agent_id="aud2")
    assert "aud2" not in sous_agents.correspondance() and audit.verdicts(sorties) == {}


def test_un_ecart_hors_liste_est_hors_schema(sorties, fiches):
    audit.ecrire_demandes(fiches, n=3)
    _repondre(sorties, 1, lambda js: [{**js[0], "verdict": "faux", "ecart": "erreur de goût"}, *js[1:]])
    with pytest.raises(ErreurModele, match="hors schéma"):
        audit.recevoir(1)


def test_la_feuille_audit_porte_le_verdict_et_la_note(sorties, fiches, tmp_path):
    audit.ecrire_demandes(fiches, n=3)
    for k in (1, 2, 3):
        _repondre(sorties, k, (lambda js: [_jugement(js[0]["id"], "faux", "autre produit"), *js[1:]]) if k == 3 else (lambda js: js))
        audit.recevoir(k)
    v = audit.verdicts(sorties)
    chemin = tableur.ecrire_cartographie(fiches, tmp_path / "carto.xlsx", verdicts=v, auditeur="Opus 5.5")
    ws = load_workbook(chemin)["Audit"]
    en_tete = [c.value for c in ws[1]]
    assert "Verdict de l'auditeur" in en_tete and "Raison de l'auditeur" in en_tete
    col = en_tete.index("Verdict de l'auditeur")
    lignes = [r for r in ws.iter_rows(min_row=2, values_only=True) if r[-1]]
    assert len(lignes) == 36 and sum(1 for r in lignes if r[col] == "faux") == 1
    textes = " ".join(str(c.value) for r in ws.iter_rows() for c in r if c.value)
    assert "pas une relecture par une personne" in textes and "fausses : 1" in textes


def test_sans_verdicts_la_feuille_reste_a_remplir(fiches, tmp_path):
    ws = load_workbook(tableur.ecrire_cartographie(fiches, tmp_path / "carto.xlsx"))["Audit"]
    assert "Juste ou faux (à remplir)" in [c.value for c in ws[1]]


def test_les_jetons_de_l_auditeur_vont_a_la_phase_audit_pas_a_une_societe(tmp_path):
    session = tmp_path / "s1"
    (session / "subagents").mkdir(parents=True)
    (tmp_path / "s1.jsonl").write_text("", encoding="utf-8")
    appel = {"type": "assistant", "timestamp": "2026-11-14T02:10:00Z", "message": {"id": "m1", "model": "claude-opus-5-5", "usage": {
        "input_tokens": 1000, "output_tokens": 100, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}}}
    (session / "subagents" / "agent-aud9.jsonl").write_text(json.dumps(appel) + "\n", encoding="utf-8")
    lignes = jetons_dev.importer(tmp_path, correspondance={"aud9": {"societe": "", "phase": "audit"}})
    assert len(lignes) == 1 and lignes[0]["source"] == "outil" and lignes[0]["phase"] == "audit" and not lignes[0]["societe"]


def test_les_textes_reprennent_les_verdicts_et_le_cout(sorties, fiches):
    from prepa_rdv import textes
    assert "à marquer juste ou faux par une personne" in textes._audit(fiches)   # avant l'audit
    audit.ecrire_demandes(fiches, n=3)
    for k in (1, 2, 3):
        _repondre(sorties, k, (lambda js: [{**_jugement(js[0]["id"], "partiel", "filiale ou division"), "citation_presente": False},
                                           *js[1:]]) if k == 1 else (lambda js: js))
        audit.recevoir(k)
    t = textes._audit(fiches)
    assert "35 justes, 1 partielle, 0 fausse, 0 invérifiable" in t and "(partiel, filiale ou division)" in t
    assert "Sur 1 page, l'auditeur dit ne pas retrouver la citation ; le code l'avait retrouvée mot pour mot sur 1," in t
    assert "—" not in t
    assert "Mesuré ici : 35 justes sur 36 vérifiables, 0,10 $ estimés par cellule." in textes._audit_200(3.6)
    lignes = [{"source": "outil", "phase": "audit", "cout_estime_usd": 1.2}, {"source": "outil", "phase": "audit", "cout_estime_usd": 2.4},
              {"source": "outil", "phase": "run", "cout_estime_usd": 9.0}, {"source": "dev", "phase": "audit", "cout_estime_usd": 5.0}]
    assert textes.cout_phase(lignes, "audit") == 3.6 and textes.cout_phase(lignes, "sonde") is None


def test_le_second_passage_rejuge_les_ecarts_et_tire_des_cellules_neuves(sorties, fiches):
    audit.ecrire_demandes(fiches, n=3)
    for k in (1, 2, 3):
        _repondre(sorties, k, (lambda js: [_jugement(js[0]["id"], "faux", "projet ou évaluation"), *js[1:]]) if k == 2 else (lambda js: js))
        audit.recevoir(k)
    relance, second = audit.ecrire_second(fiches, n=12)
    d4 = json.loads((sorties / "audit" / "demande-4.json").read_text(encoding="utf-8"))
    d5 = json.loads((sorties / "audit" / "demande-5.json").read_text(encoding="utf-8"))
    premier = set(audit.verdicts(sorties, "premier"))
    assert d4["tirage"] == "relance" and len(d4["cellules"]) == 1 and d4["cellules"][0]["id"] in premier
    assert d5["tirage"] == "second" and len(d5["cellules"]) == 42 - 36 and not {c["id"] for c in d5["cellules"]} & premier
    _repondre(sorties, 4)
    audit.recevoir(4)
    assert audit.verdicts(sorties, "relance")[d4["cellules"][0]["id"]]["verdict"] == "juste"
    assert audit.verdicts(sorties, "premier")[d4["cellules"][0]["id"]]["verdict"] == "faux"   # le premier verdict reste
    _repondre(sorties, 5)
    audit.recevoir(5)
    v = json.loads((sorties / "audit" / "verdicts.json").read_text(encoding="utf-8"))
    assert set(v) == {"modele", "premier", "relance", "second"} and v["second"]["resume"]["juste"] == 42 - 36


def test_les_feuilles_et_les_textes_reprennent_la_relance_et_le_second_tirage(sorties, fiches, tmp_path):
    from prepa_rdv import textes
    audit.ecrire_demandes(fiches, n=3)
    for k in (1, 2, 3):
        _repondre(sorties, k, (lambda js: [_jugement(js[0]["id"], "faux", "projet ou évaluation"), *js[1:]]) if k == 2 else (lambda js: js))
        audit.recevoir(k)
    audit.ecrire_second(fiches, n=12)
    for k in (4, 5):
        _repondre(sorties, k)
        audit.recevoir(k)
    relance, second = audit.verdicts(sorties, "relance"), audit.verdicts(sorties, "second")
    wb = load_workbook(tableur.ecrire_cartographie(fiches, tmp_path / "carto.xlsx", verdicts=audit.verdicts(sorties),
                                                   auditeur="Opus 5.5", relance=relance, second=second))
    ws = wb["Audit"]
    en_tete = [c.value for c in ws[1]]
    col = en_tete.index("Après correction : verdict")
    rejugee = [r for r in ws.iter_rows(min_row=2, values_only=True) if r[-1] in relance]
    assert len(rejugee) == 1 and rejugee[0][col] == "juste" and rejugee[0][en_tete.index("Verdict de l'auditeur")] == "faux"
    ws2 = wb["Audit, second tirage"]
    assert len([r for r in ws2.iter_rows(min_row=2, values_only=True) if r[-1] in second]) == 42 - 36
    t = textes._audit(fiches)
    assert "(D21)" in t
    assert "Le premier tirage passe ainsi à 36 sur 36 vérifiables (100 %)" in t
    assert "Un second tirage de 6 cellules nouvelles (graine 2027)" in t
    assert ("La porte G4, fixée à 90 %, se mesure sur ce tirage plutôt que sur le premier, qui a servi à écrire les règles, "
            "et elle est passée.") in t
    assert "Avec la règle du projet, 1 sur 1 cellule « projet ou évaluation » devient juste." in t
    assert "la filiale signalée" not in t   # aucune cellule de filiale en écart : pas de phrase sur le périmètre
    assert "—" not in t
    assert "35 justes sur 36 vérifiables au premier tirage, 36 après deux règles d'affichage, 6 sur 6 au second, 0,10 $ estimés par cellule." in textes._audit_200(4.3)


def test_une_cellule_de_filiale_reste_un_signal_et_la_porte_se_mesure_sur_le_second_tirage(sorties, fiches):
    """Choix d'Oscar du 14 novembre 2026 (D22) : une page sur une filiale garde sa cellule, la filiale signalée."""
    from prepa_rdv import textes
    audit.ecrire_demandes(fiches, n=3)
    filiale = lambda js: [_jugement(j["id"], "partiel", "filiale ou division") for j in js[:4]] + js[4:]   # noqa: E731
    for k in (1, 2, 3):
        _repondre(sorties, k, filiale if k == 1 else (lambda js: js))
        audit.recevoir(k)
    audit.ecrire_second(fiches, n=12)
    _repondre(sorties, 4, lambda js: [_jugement(j["id"], "partiel", "filiale ou division") for j in js])   # l'auditeur maintient
    audit.recevoir(4)
    _repondre(sorties, 5)
    audit.recevoir(5)
    t = textes._audit(fiches)
    assert "aucun des 4 verdicts « filiale ou division » ne change" in t
    assert ("Une cellule tirée d'une page sur une filiale reste dans la fiche, la filiale signalée comme le prévoit le cahier "
            "des charges, et sa valeur se vérifie pour le groupe pendant le rendez-vous (D22).") in t
    assert "Le premier tirage passe ainsi à 32 sur 36 vérifiables (89 %)." in t
    assert ("La porte G4, fixée à 90 %, se mesure sur ce tirage plutôt que sur le premier, qui a servi à écrire les règles, "
            "et elle est passée.") in t
    assert "—" not in t


def test_la_cellule_dit_l_entite_nommee_et_la_migration_prevue():
    from prepa_rdv import affichage
    lvmh = {"nom_saisi": "LVMH", "nom_retenu": "LVMH Moët Hennessy Louis Vuitton SE", "alias": []}
    stadler = {"nom_saisi": "Stadler Rail", "nom_retenu": "Stadler Rail AG", "alias": []}
    nokia = {"nom_saisi": "Nokia", "nom_retenu": "Nokia Oyj", "alias": []}
    assert affichage.entite_autre("Moët Hennessy", lvmh) == "Moët Hennessy"            # division, même au milieu du nom légal
    assert affichage.entite_autre("LVMH", lvmh) is None
    assert affichage.entite_autre("Stadler", stadler) is None                          # forme courte de la société
    assert affichage.entite_autre("Nokia Corporation", nokia) is None
    assert affichage.entite_autre("NOKIA UK LIMITED", nokia) == "NOKIA UK LIMITED"
    assert affichage.entite_autre("Barilla Vendor Portal", {"nom_saisi": "Barilla"}) is None   # un portail, pas une filiale
    projet = {"champ": "erp", "precision": "Consolidation des ERP pour préparer la migration vers S/4HANA."}
    en_place = {"champ": "erp", "precision": "Deux instances SAP ECC existantes, migration vers S/4HANA visée début 2024."}
    financement = {"champ": "financement", "precision": "Programme en cours, plafond de 1 Md€."}
    assert affichage.en_projet(projet) and not affichage.en_projet(en_place) and not affichage.en_projet(financement)
    t = {"champ": "erp", "entite_nommee": "Tibnor", "precision": None}
    assert affichage.marques(t, {"nom_saisi": "SSAB", "nom_retenu": "SSAB AB"}) == " (entité nommée : Tibnor)"
