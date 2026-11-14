"""Pipeline complet avec un faux modèle, de fausses pages et un faux résolveur : aucun appel réseau, aucun jeton."""
import json
from pathlib import Path

import pytest

from prepa_rdv import agent, brief, fiche as fiche_mod, run, tableur
from prepa_rdv.jetons import Registre
from prepa_rdv.lecteur import Page
from prepa_rdv.modele import Reponse
from prepa_rdv.resolveur import Entite
from prepa_rdv.schema import Champ

PAGE_SAP = "https://news.sap.com/2026/06/nokia"
PAGE_ARIBA = "https://www.nokia.com/sites/default/files/2024-07/nokia-sap-ariba-guide.pdf"
TEXTE_SAP = ("Nokia has selected Microsoft Azure as the cloud platform underpinning the transformation. "
             "SAP will operate and manage its SAP S/4HANA software environment hosted on Microsoft Azure. " * 4)
TEXTE_ARIBA = "Nokia suppliers register on SAP Ariba to answer sourcing events. " * 20

SORTIE = {
    "trouvailles": [
        {"champ": "erp", "valeur": "RISE with SAP", "precision": None, "statut_valeur": "present",
         "citation": "SAP will operate and manage its SAP S/4HANA software environment hosted on Microsoft Azure",
         "citation_langue": "en", "traduction_fr": None, "url": PAGE_SAP, "entite_nommee": "Nokia", "type_source": "P2", "date_source": "2026-06-30"},
        {"champ": "achats", "valeur": "Ariba", "precision": None, "statut_valeur": "present",
         "citation": "Nokia suppliers register on SAP Ariba to answer sourcing events",
         "citation_langue": "en", "traduction_fr": None, "url": PAGE_ARIBA, "entite_nommee": "Nokia", "type_source": "P1", "date_source": "2024-07"},
        {"champ": "tms", "valeur": "Kyriba", "precision": None, "statut_valeur": "present",
         "citation": "Nokia uses Kyriba to centralise cash positions across all of its entities worldwide",
         "citation_langue": "en", "traduction_fr": None, "url": PAGE_SAP, "entite_nommee": "Nokia", "type_source": "P2", "date_source": "2026-06-30"},
    ],
    "champs_sans_resultat": ["financement", "direction_financiere"],
    "remarques": [],
}


class FauxResolveur:
    def resoudre(self, nom):
        return Entite(nom_saisi=nom, nom_retenu="Nokia Oyj", pays="Finland", statut="coté", site="https://www.nokia.com",
                      domaines=["nokia.com"], source="faux")


class FauxLecteur:
    def __init__(self):
        self.appels = 0

    def lire(self, url, forcer=False):
        self.appels += 1
        textes = {PAGE_SAP: (TEXTE_SAP, "2026-06-30"), PAGE_ARIBA: (TEXTE_ARIBA, "2024-07-15")}
        if url in textes:
            t, d = textes[url]
            return Page(url=url, url_finale=url, statut=200, type_contenu="text/html", texte=t, date_page=d, titre="Nokia", empreinte="e")
        return Page(url=url, statut=404, erreur="HTTP 404")


class FauxModele:
    modele = "claude-sonnet-5-5"

    def __init__(self, registre: Registre):
        self.registre, self.appels = registre, 0

    def appeler(self, prompt, *, schema=None, systeme=None, outils=None, phase="run", societe=None, note=""):
        self.appels += 1
        self.registre.ajouter(source="outil", backend="faux", phase=phase, societe=societe, modele=self.modele, appels=1,
                              entree=10, sortie=500, cache_lu=2000, cache_ecrit=100, recherches_web=3, cout_estime_usd=0.01, note=note)
        return Reponse(modele=self.modele, texte="", donnees=json.loads(json.dumps(SORTIE)), usage={}, cout_declare_usd=None,
                       duree_ms=1000, tours=4, session="s1")


@pytest.fixture
def ctx(tmp_path):
    reg = Registre(tmp_path / "journal" / "jetons.jsonl")
    return run.Contexte(sorties=tmp_path, lecteur=FauxLecteur(), resolveur=FauxResolveur(), modele=FauxModele(reg), registre=reg,
                        run_id="essai", phase="essai")


def test_pipeline_d_une_societe(ctx, tmp_path):
    f = run.traiter("Nokia", ctx)
    niveaux = {c: f["synthese"][c]["niveau"] for c in f["synthese"]}
    assert niveaux["erp"] == "confirmé"          # P2 de juin 2026, dans la fenêtre
    assert niveaux["achats"] == "probable"        # P1 de juillet 2024, hors fenêtre de 24 mois
    assert niveaux["tms"] == "non trouvé"         # citation inventée, rejetée par le code
    assert niveaux["financement"] == "non trouvé"
    assert f["jetons"]["traites"] > 0 and f["jetons"]["appels"] == 1
    dossier = tmp_path / "societes" / "nokia"
    assert (dossier / "fiche.json").exists() and (dossier / "brief.html").exists() and (dossier / "journal.jsonl").exists()
    etapes = [json.loads(l)["etape"] for l in (dossier / "journal.jsonl").read_text().splitlines()]
    assert etapes == ["resoudre", "agent", "verifier", "ecrire"]


def test_la_citation_inventee_est_comptee_et_visible(ctx):
    f = run.traiter("Nokia", ctx)
    rejetee = next(t for t in f["trouvailles"] if t["champ"] == "tms")
    assert rejetee["niveau"] == "non trouvé" and not rejetee["verifs"]["citation_trouvee"]
    assert any("introuvable" in e for e in rejetee["verifs"]["erreurs"])


def test_une_relance_ne_rappelle_pas_le_modele(ctx):
    run.traiter("Nokia", ctx)
    assert ctx.modele.appels == 1
    run.traiter("Nokia", ctx)
    assert ctx.modele.appels == 1
    run.traiter("Nokia", ctx, forcer=True)
    assert ctx.modele.appels == 2


def test_lot_continue_malgre_un_echec(ctx):
    class Casse(FauxModele):
        def appeler(self, prompt, **kw):
            if "Casse" in prompt:
                from prepa_rdv.modele import ErreurModele
                raise ErreurModele("panne")
            return super().appeler(prompt, **kw)
    ctx.modele = Casse(ctx.registre)
    fiches, echecs = run.lot(["Nokia", "Casse"], ctx, paralleles=2)
    assert [f["societe"] for f in fiches] == ["Nokia"] and "Casse" in echecs


def test_brief_une_page_et_controles(ctx):
    f = run.traiter("Nokia", ctx)
    c = brief.composer(f)
    assert brief.verifier_brief(c, f) == []
    assert len(brief.texte_visible(c).split()) <= brief.MAX_MOTS
    lignes = {l["champ"]: l for l in c["lignes"]}
    assert "SAP S/4HANA" in lignes["ERP"]["valeur"] and lignes["TMS et trésorerie"]["valeur"] == "Non trouvé"
    assert c["angle"][0].startswith("Hypothèse")
    assert 3 <= len(c["questions"]) <= 5


def test_les_questions_ne_presupposent_aucun_fait():
    """Une question de rendez-vous ne donne pas pour acquis un projet ou une migration que la fiche n'établit pas."""
    from prepa_rdv import fiche as fiche_mod
    toutes = [*fiche_mod.QUESTIONS_TYPES.values(), *fiche_mod.QUESTIONS_COMPLEMENT]
    assert toutes and not [q for q in toutes if "en cours" in q]


def test_le_signal_le_plus_recent_entre_dans_le_brief():
    def tr(i, valeur, date, dans_fenetre=True):
        return {"id": i, "verifs": {"date_retenue": date, "dans_fenetre": dans_fenetre}, "valeur": valeur}
    fiche = {
        "trouvailles": [tr("a", "Nomination d'un directeur financier", "2025-03-01"), tr("b", "Migration vers un nouvel ERP annoncée", "2026-09-15"),
                        tr("c", "Un leader mondial qui a gagné en efficacité", "2026-10-01")],
        "synthese": {"signal": {"niveau": "probable", "contradiction": False, "valeurs": [
            {"valeur": "Nomination d'un directeur financier", "precision": None, "statut": "present", "niveau": "confirmé", "ids": ["a"]},
            {"valeur": "Migration vers un nouvel ERP annoncée", "precision": None, "statut": "present", "niveau": "probable", "ids": ["b"]},
            {"valeur": "Un leader mondial qui a gagné en efficacité", "precision": None, "statut": "present", "niveau": "confirmé", "ids": ["c"]},
        ]}},
    }
    retenu = brief.signal_retenu(fiche)
    # le plus récent est écarté par le contrôle de langue (« leader ») : le suivant passe, même s'il est moins bien prouvé
    assert [v["ids"] for v in retenu["valeurs"]] == [["b"]] and retenu["niveau"] == "probable"
    fiche["synthese"]["signal"]["valeurs"] = fiche["synthese"]["signal"]["valeurs"][2:]
    assert brief.signal_retenu(fiche)["niveau"] == "non trouvé"
    # une page hors de sa fenêtre (date de 2001 dans les métadonnées, par exemple) n'est pas un signal récent
    fiche["trouvailles"][1]["verifs"]["dans_fenetre"] = False
    fiche["synthese"]["signal"]["valeurs"] = [
        {"valeur": "Migration vers un nouvel ERP annoncée", "precision": None, "statut": "present", "niveau": "probable", "ids": ["b"]}]
    assert brief.signal_retenu(fiche)["niveau"] == "non trouvé"


def test_controle_de_langue():
    assert brief.controle_langue("Nokia utilise SAP.") == []
    assert any("cadratin" in p for p in brief.controle_langue("Un résultat — clair."))
    assert any("mot interdit" in p for p in brief.controle_langue("Un outil très puissant."))
    assert any("phrase de" in p for p in brief.controle_langue(" ".join(["mot"] * 31) + "."))
    # Un saut de ligne finit une phrase : deux cellules de 20 mots ne font pas une phrase de 40 mots.
    deux_cellules = "\n".join([" ".join(["mot"] * 20), " ".join(["mot"] * 20)])
    assert brief.controle_langue(deux_cellules) == []


def test_controle_des_nombres(ctx):
    f = run.traiter("Nokia", ctx)
    c = brief.composer(f)
    c["angle"].append("Le gain attendu est de 37 % sur le fonds de roulement.")
    assert any("nombre absent de la fiche : 37" in p for p in brief.verifier_brief(c, f))


def test_tableurs(ctx, tmp_path):
    from openpyxl import load_workbook
    f = run.traiter("Nokia", ctx)
    carto = tableur.ecrire_cartographie([f], tmp_path / "cartographie.xlsx", lien_outil="https://exemple.test/outil")
    long = tableur.ecrire_trouvailles([f], tmp_path / "trouvailles.xlsx")
    wb = load_workbook(carto)
    assert wb.sheetnames == ["Cartographie", "Légende", "Audit"]
    ws = wb["Cartographie"]
    en_tete = [c.value for c in ws[1]]
    ligne = dict(zip(en_tete, [c.value for c in ws[2]]))
    assert ligne["ERP : valeur"] == "SAP S/4HANA" and ligne["ERP : niveau"] == "confirmé"
    assert ligne["TMS et trésorerie : niveau"] == "non trouvé"
    assert ws.cell(row=2, column=en_tete.index("ERP : source") + 1).hyperlink is not None
    assert load_workbook(long)["Trouvailles"].max_row == 4
    assert carto.stat().st_size < 10_000_000


def test_audit_a_graine_fixe(ctx):
    f = run.traiter("Nokia", ctx)
    a1 = tableur.echantillon_audit([f], n=2, graine=7)
    a2 = tableur.echantillon_audit([f], n=2, graine=7)
    assert a1 == a2 and len(a1) == 2


def test_plan_de_requetes_suit_la_langue_du_siege():
    e = Entite(nom_saisi="Fresenius", pays="Germany")
    plan = agent.plan_de_requetes(e)
    assert any("Finanzvorstand" in q for q in plan["direction_financiere"])
    assert all(len(v) >= 2 for v in plan.values())
    assert agent.empreinte_prompt() == agent.empreinte_prompt()


def test_bilan_du_lot(ctx):
    from prepa_rdv import bilan
    f = run.traiter("Nokia", ctx)
    b = bilan.bilan_lot([f])
    s = b["societes"][0]
    assert s["trouvailles"] == 3 and s["niveaux"] == {"confirmé": 1, "probable": 1, "non trouvé": 1}
    assert s["rejets"] == {"citation introuvable": 1} and s["hors_fenetre"] == 1
    assert b["total"]["gardees"] == 2 and b["total"]["part_hors_fenetre_ou_sans_date"] == 0.5
    assert "Nokia" in bilan.formater(b)


def test_journal_d_erreurs(ctx, tmp_path, monkeypatch):
    from prepa_rdv import erreurs
    monkeypatch.setenv("PREPA_RDV_SORTIES", str(tmp_path))
    f = run.traiter("Nokia", ctx)
    nouvelles = erreurs.releve([f], ctx.lecteur)
    assert len(nouvelles) == 1 and nouvelles[0]["champ"] == "tms" and nouvelles[0]["cause"] in ("citation inventée", "citation reformulée")
    assert "contrôle 1" in nouvelles[0]["detecteur"] and nouvelles[0]["changement"] is None
    assert erreurs.releve([f], ctx.lecteur) == []                       # pas de doublon
    assert erreurs.comptes() == {"erreurs": 1, "corrigees": 0}          # sans changement, pas corrigée
    erreurs.corriger("nokia-tms-3", "règle : un TMS exige une citation qui nomme le produit", "société relancée, champ tms")
    assert erreurs.comptes() == {"erreurs": 1, "corrigees": 1}
    with pytest.raises(KeyError):
        erreurs.corriger("inconnu", "x", "y")


def test_textes_produits_depuis_les_journaux(ctx, tmp_path, monkeypatch):
    from prepa_rdv import erreurs, textes
    monkeypatch.setenv("PREPA_RDV_SORTIES", str(tmp_path))
    f = run.traiter("Nokia", ctx)
    erreurs.releve([f], ctx.lecteur)
    erreurs.corriger("nokia-tms-3", "règle : un TMS exige une citation qui nomme le produit", "société relancée")
    outil = textes.ton_outil([f], erreurs.lire(), "(rapport des jetons)")
    assert "## Où l'outil s'est trompé" in outil and "Cause : citation" in outil and "société relancée" in outil
    assert "Sur 1 sociétés" in outil and "3 trouvailles" in outil and agent.empreinte_prompt() in outil
    deux_cents = textes.a_200([f])
    assert "Et à 200 sociétés" in deux_cents and "relecture humaine" in deux_cents.lower() and "33" in deux_cents
    html = textes.md_vers_html(outil)
    assert "<table>" in html and "<pre>" in html and "<h1>" in html


def test_le_poste_vient_de_la_citation_quand_la_valeur_n_est_que_le_nom():
    v = {"valeur": "Cédric DONDAIN", "precision": None, "statut": "present", "niveau": "probable", "ids": ["x"]}
    t = {"citation": "Cédric DONDAIN, trésorier international en charge de la gestion de crédit du groupe Servier"}
    assert brief._valeur_affichee(v, Champ.DIRECTION_FINANCIERE, t).startswith("Cédric DONDAIN, trésorier international en charge de la gestion")
    v2 = {"valeur": "Gerald Mayer", "precision": None, "statut": "present", "niveau": "confirmé", "ids": ["y"]}
    t2 = {"citation": "Mag. Gerald Mayer Chief Financial Officer (CFO)"}
    assert brief._valeur_affichee(v2, Champ.DIRECTION_FINANCIERE, t2) == "Gerald Mayer, Chief Financial Officer (CFO)"


def test_les_pdf_prennent_le_gabarit_commun():
    """D23 : bandeau au nom de l'outil, titre court, mention et numéro en pied, tableaux zébrés."""
    from prepa_rdv import gabarit, textes
    html = textes.md_vers_html("# Ton outil : comment il fonctionne\n\n| A | B |\n|---|---|\n| 1 | 2 |\n")
    assert '@top-left { content: "prepa-rdv"' in html and '@top-right { content: "Ton outil"' in html
    assert "counter(page)" in html and gabarit.PIED in html and gabarit.BLEU_VERT in html
    assert gabarit.titre_court("Et à 200 sociétés ? Ce qui casse") == "Et à 200 sociétés ?"
    doc = brief.html_document([{"societe": "Nokia", "entete": "Finland", "lignes": [], "angle": [], "questions": [],
                                "contact": None, "sources": []}])
    assert "class='bandeau'" in doc and "<th>Valeur et source</th>" in doc and "<span>1</span>" in doc
