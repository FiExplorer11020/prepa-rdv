"""Circuit par sous-agents : demande écrite, réponse validée, jetons attribués. Sans réseau ni modèle."""
import json
from pathlib import Path

import pytest

from prepa_rdv import jetons_dev, run, sous_agents
from prepa_rdv.jetons import Registre
from prepa_rdv.modele import ErreurModele
from prepa_rdv.resolveur import Entite
from tests.test_pipeline import FauxLecteur, FauxResolveur, SORTIE

ENTITE = Entite(nom_saisi="Nokia", nom_retenu="Nokia Oyj", pays="Finland", statut="coté", site="https://www.nokia.com", domaines=["nokia.com"])


@pytest.fixture
def sorties(tmp_path, monkeypatch):
    monkeypatch.setenv("PREPA_RDV_SORTIES", str(tmp_path))
    return tmp_path


@pytest.fixture
def ctx(sorties):
    reg = Registre(sorties / "journal" / "jetons.jsonl")
    return run.Contexte(sorties=sorties, lecteur=FauxLecteur(), resolveur=FauxResolveur(), modele=None, registre=reg, run_id="essai", phase="sonde")


def test_la_demande_porte_les_consignes_le_schema_et_le_chemin_de_la_reponse(tmp_path):
    chemin = sous_agents.ecrire_demande(tmp_path, ENTITE)
    texte = chemin.read_text(encoding="utf-8")
    assert "Société : Nokia" in texte and "Plan de requêtes" in texte
    assert "citation" in texte and "entite_nommee" in texte           # schéma fermé
    assert str((tmp_path / "agent-sortie.json").resolve()) in texte  # où écrire
    assert "agent-reach" in texte                                      # interdit au sous-agent
    assert json.loads((tmp_path / "demande.json").read_text())["societe"] == "Nokia"


def test_une_societe_sans_reponse_attend_un_sous_agent(ctx, sorties):
    with pytest.raises(sous_agents.AttenteAgent) as e:
        run.traiter("Nokia", ctx)
    assert (sorties / "societes" / "nokia" / "demande.md").exists() and e.value.societe == "Nokia"
    fiches, echecs, attentes = run.lot_detail(["Nokia"], ctx)
    assert fiches == [] and echecs == {} and "Nokia" in attentes


def test_recevoir_valide_ecrit_le_cache_et_enregistre_l_agent(ctx, sorties):
    with pytest.raises(sous_agents.AttenteAgent):
        run.traiter("Nokia", ctx)
    dossier = sorties / "societes" / "nokia"
    (dossier / "agent-sortie.json").write_text("Voici la réponse :\n```json\n" + json.dumps(SORTIE) + "\n```", encoding="utf-8")
    entite = Entite(**json.loads((dossier / "entite.json").read_text()))
    sortie = sous_agents.recevoir(dossier, entite, agent_id="abc123", phase="sonde")
    assert len(sortie.trouvailles) == 3
    assert sous_agents.correspondance()["abc123"] == {**sous_agents.correspondance()["abc123"], "societe": "Nokia", "phase": "sonde"}
    f = run.traiter("Nokia", ctx)                  # le circuit reprend, sans nouvelle demande
    assert f["synthese"]["erp"]["niveau"] == "confirmé" and f["synthese"]["tms"]["niveau"] == "non trouvé"
    assert json.loads((dossier / "agent.json").read_text())["acces"] == "sous-agent"


@pytest.mark.parametrize("contenu, raison", [
    (None, "Pas de réponse"),
    ("pas du json", "sans JSON valide"),
    (json.dumps({"trouvailles": [{"champ": "erp"}], "champs_sans_resultat": [], "remarques": []}), "hors schéma"),
    (json.dumps({"trouvailles": [], "champs_sans_resultat": ["inconnu"], "remarques": []}), "hors schéma"),
])
def test_une_reponse_invalide_est_refusee_avec_sa_raison(tmp_path, contenu, raison):
    if contenu is not None:
        (tmp_path / "agent-sortie.json").write_text(contenu, encoding="utf-8")
    with pytest.raises(ErreurModele) as e:
        sous_agents.lire_sortie(tmp_path)
    assert raison in str(e.value)


def test_un_agent_n_est_enregistre_qu_une_fois(sorties):
    sous_agents.enregistrer_agent("a1", "Nokia", "sonde")
    sous_agents.enregistrer_agent("a1", "Nokia", "run")
    assert len(sous_agents.chemin_correspondance().read_text().splitlines()) == 1


# --- Jetons des agents de l'outil ----------------------------------------------------------------

def ligne(mid, ts, out):
    return json.dumps({"type": "assistant", "timestamp": ts, "uuid": mid,
                       "message": {"id": mid, "model": "claude-sonnet-5-5", "usage": {
                           "input_tokens": 2, "output_tokens": out, "cache_read_input_tokens": 1000, "cache_creation_input_tokens": 100,
                           "server_tool_use": {"web_search_requests": 1}}}})


def test_les_jetons_d_un_agent_de_l_outil_ne_comptent_pas_comme_developpement(tmp_path):
    projet = tmp_path / "projet"
    (projet / "sess" / "subagents").mkdir(parents=True)
    (projet / "sess.jsonl").write_text(ligne("m0", "2026-11-13T22:00:00.000Z", 50), encoding="utf-8")
    (projet / "sess" / "subagents" / "agent-xyz.jsonl").write_text("\n".join([ligne("a1", "2026-11-13T22:05:00.000Z", 200), ligne("a2", "2026-11-13T22:06:00.000Z", 300)]), encoding="utf-8")
    lignes = jetons_dev.importer(projet, correspondance={"xyz": {"societe": "Nokia", "phase": "sonde"}})
    agent = [l for l in lignes if l["agent"] == "sous-agent-xyz"][0]
    assert agent["source"] == "outil" and agent["societe"] == "Nokia" and agent["phase"] == "sonde" and agent["sortie"] == 500
    assert [l["source"] for l in lignes if l["agent"] == "principal"] == ["dev"]


def test_totaux_d_un_agent(tmp_path):
    (tmp_path / "p" / "s" / "subagents").mkdir(parents=True)
    (tmp_path / "p" / "s" / "subagents" / "agent-xyz.jsonl").write_text(ligne("a1", "2026-11-13T22:05:00.000Z", 200), encoding="utf-8")
    t = jetons_dev.totaux_agents(["xyz"], racine=tmp_path)
    assert t["appels"] == 1 and t["sortie"] == 200 and t["cache_lu"] == 1000 and t["traites"] == 2 + 100 + 1000 + 200
    assert t["recherches_web"] == 1 and t["cout_estime_usd"] > 0
    assert jetons_dev.totaux_agents(["inconnu"], racine=tmp_path)["appels"] == 0


# --- Seconde lecture à l'aveugle ---------------------------------------------------------------------

class LecteurRefuse(FauxLecteur):
    """Refuse la page de l'éditeur (HTTP 403), lit les autres."""

    def lire(self, url, forcer=False):
        if "sap.com" in url:
            from prepa_rdv.lecteur import Page
            return Page(url=url, statut=403, erreur="HTTP 403")
        return super().lire(url, forcer)


def test_les_pages_refusees_attendent_une_seconde_lecture_puis_passent_a_probable(sorties):
    from prepa_rdv import relecture
    reg = Registre(sorties / "journal" / "jetons.jsonl")
    ctx = run.Contexte(sorties=sorties, lecteur=LecteurRefuse(), resolveur=FauxResolveur(), modele=None, registre=reg, run_id="essai", phase="sonde")
    with pytest.raises(sous_agents.AttenteAgent):
        run.traiter("Nokia", ctx)
    dossier = sorties / "societes" / "nokia"
    (dossier / "agent-sortie.json").write_text(json.dumps(SORTIE), encoding="utf-8")
    sous_agents.recevoir(dossier, Entite(**json.loads((dossier / "entite.json").read_text())), "ag1", "sonde")

    f = run.traiter("Nokia", ctx)  # la page de SAP est refusée au code : rejetée, mais une seconde lecture est demandée
    assert f["synthese"]["erp"]["niveau"] == "non trouvé"
    assert f["relecture"]["a_relire"] == 2 and f["relecture"]["en_attente"] == 2  # l'ERP et le TMS portent sur la même page
    demande = (dossier / relecture.FICHIER_DEMANDE).read_text(encoding="utf-8")
    assert "https://news.sap.com/2026/06/nokia" in demande and "erp" in demande
    assert "SAP will operate and manage" not in demande  # à l'aveugle : la citation du premier agent n'y figure pas

    passage = "SAP will operate and manage its SAP S/4HANA software environment hosted on Microsoft Azure"
    (dossier / relecture.FICHIER_SORTIE).write_text(json.dumps({"lectures": [
        {"id": "nokia-erp-1", "lue": True, "passage": passage, "contexte": "Nokia and SAP. " + passage + ". Nokia has selected Azure.",
         "titre": "Nokia, SAP and Microsoft", "date_page": "2026-06-30"}]}), encoding="utf-8")
    f = run.traiter("Nokia", ctx)
    erp = next(t for t in f["trouvailles"] if t["champ"] == "erp")
    assert erp["niveau"] == "probable"                       # plafonné : jamais « confirmé » par seconde lecture
    assert erp["verifs"]["mode_verification"] == "seconde_lecture" and erp["verifs"]["citation_trouvee"]
    assert f["relecture"]["faites"] == 1 and f["relecture"]["en_attente"] == 1  # le TMS reste à relire


def test_une_seconde_lecture_qui_ne_concorde_pas_est_rejetee(sorties):
    from prepa_rdv import relecture
    reg = Registre(sorties / "journal" / "jetons.jsonl")
    ctx = run.Contexte(sorties=sorties, lecteur=LecteurRefuse(), resolveur=FauxResolveur(), modele=None, registre=reg, run_id="essai", phase="sonde")
    with pytest.raises(sous_agents.AttenteAgent):
        run.traiter("Nokia", ctx)
    dossier = sorties / "societes" / "nokia"
    (dossier / "agent-sortie.json").write_text(json.dumps(SORTIE), encoding="utf-8")
    sous_agents.recevoir(dossier, Entite(**json.loads((dossier / "entite.json").read_text())), "ag1", "sonde")
    (dossier / relecture.FICHIER_SORTIE).write_text(json.dumps({"lectures": [
        {"id": "nokia-erp-1", "lue": True, "passage": "Nokia moves its finance to Oracle Cloud ERP next year", "contexte": None,
         "titre": "Nokia", "date_page": "2026-06-30"}]}), encoding="utf-8")
    f = run.traiter("Nokia", ctx)
    erp = next(t for t in f["trouvailles"] if t["champ"] == "erp")
    assert erp["niveau"] == "non trouvé" and not erp["verifs"]["citation_trouvee"]


def test_seconde_lecture_hors_schema_refusee(tmp_path):
    from prepa_rdv import relecture
    (tmp_path / relecture.FICHIER_SORTIE).write_text(json.dumps({"lectures": [{"id": "x"}]}), encoding="utf-8")
    with pytest.raises(ErreurModele):
        relecture.lire_sortie(tmp_path)
