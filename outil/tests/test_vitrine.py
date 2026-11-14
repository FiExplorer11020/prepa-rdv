"""La vitrine : site statique tiré d'une fiche du faux pipeline, sans réseau ni jeton."""
import json

import pytest
from pypdf import PdfWriter

from prepa_rdv import audit, run, vitrine
from tests.test_pipeline import FauxLecteur, FauxModele, FauxResolveur
from prepa_rdv.jetons import Registre

LIEN = "https://github.com/exemple/prepa-rdv"


@pytest.fixture
def sorties(tmp_path, monkeypatch):
    """Les sorties d'un lot d'une société (Nokia), traitée par le faux pipeline."""
    s = tmp_path / "sorties"
    monkeypatch.setenv("PREPA_RDV_SORTIES", str(s))
    reg = Registre(s / "journal" / "jetons.jsonl")
    ctx = run.Contexte(sorties=s, lecteur=FauxLecteur(), resolveur=FauxResolveur(), modele=FauxModele(reg), registre=reg,
                       run_id="essai", phase="essai")
    run.traiter("Nokia", ctx)
    return s


def _modifier_fiche(sorties, changer):
    chemin = sorties / "societes" / "nokia" / "fiche.json"
    f = json.loads(chemin.read_text(encoding="utf-8"))
    changer(f)
    chemin.write_text(json.dumps(f, ensure_ascii=False), encoding="utf-8")
    return f


def _pdf(chemin, pages: int):
    chemin.parent.mkdir(parents=True, exist_ok=True)
    w = PdfWriter()
    for _ in range(pages):
        w.add_blank_page(width=595, height=842)
    with open(chemin, "wb") as fh:
        w.write(fh)


def test_le_site_a_ses_pages_et_passe_ses_controles(sorties, tmp_path):
    r = vitrine.construire(tmp_path / "site", sorties, LIEN)
    site = tmp_path / "site"
    assert r["problemes"] == [] and r["pages"] == 2
    assert (site / "index.html").is_file() and (site / "societes" / "nokia.html").is_file()
    assert sorted(p.name for p in (site / "polices").iterdir() if p.suffix == ".ttf") == sorted(
        p.name for p in vitrine.POLICES.iterdir() if p.suffix == ".ttf")
    entete = json.loads((site / "vercel.json").read_text(encoding="utf-8"))["headers"][0]["headers"][0]
    assert entete == {"key": "X-Robots-Tag", "value": "noindex"}
    for page in site.rglob("*.html"):
        texte = page.read_text(encoding="utf-8")
        assert vitrine.NOINDEX in texte and "<script" not in texte and vitrine.BANDEAU in texte
        assert f'href="{LIEN}"' in texte


def test_la_page_d_une_societe_montre_la_citation_la_source_et_le_verdict(sorties, tmp_path, monkeypatch):
    f = json.loads((sorties / "societes" / "nokia" / "fiche.json").read_text(encoding="utf-8"))
    erp = next(t for t in f["trouvailles"] if t["champ"] == "erp")
    tms = next(t for t in f["trouvailles"] if t["champ"] == "tms")
    jugement = {"id": erp["id"], "page_ouverte": True, "citation_presente": True, "verdict": "partiel",
                "ecart": "précision non soutenue", "raison": "La page parle de RISE sans en donner la date."}
    monkeypatch.setattr(audit, "verdicts", lambda s=None, tirage="premier": {erp["id"]: jugement} if tirage == "premier" else {})
    vitrine.construire(tmp_path / "site", sorties, LIEN)
    page = (tmp_path / "site" / "societes" / "nokia.html").read_text(encoding="utf-8")
    assert erp["citation"] in page and erp["url"] in page
    assert "Audit à l'aveugle : partiel, précision non soutenue." in page and "sans en donner la date" in page
    assert tms["citation"] not in page                       # la citation rejetée reste au tableur, pas sur la page
    assert "Sur les 3 trouvailles des six champs, 2 passent les contrôles du code." in page
    accueil = (tmp_path / "site" / "index.html").read_text(encoding="utf-8")
    assert '<p class="n">0 <small>sur 1</small></p><p class="l">cellules jugées justes' in accueil


def test_le_texte_de_la_fiche_est_echappe(sorties, tmp_path):
    def piege(f):
        t = next(t for t in f["trouvailles"] if t["champ"] == "erp")
        t["citation"] = 'SAP <script>alert("x")</script> & co'
    _modifier_fiche(sorties, piege)
    r = vitrine.construire(tmp_path / "site", sorties, LIEN)
    page = (tmp_path / "site" / "societes" / "nokia.html").read_text(encoding="utf-8")
    assert "&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt; &amp; co" in page
    assert r["problemes"] == []                            # aucune balise script n'a passé


def test_le_lien_vers_la_page_du_brief_suit_le_pdf(sorties, tmp_path):
    _pdf(sorties / "livrables" / "briefs.pdf", 1)
    r = vitrine.construire(tmp_path / "site", sorties, LIEN)
    assert r["page_par_brief"] and (tmp_path / "site" / "telechargements" / "briefs.pdf").is_file()
    assert 'href="../telechargements/briefs.pdf#page=1"' in (tmp_path / "site" / "societes" / "nokia.html").read_text(encoding="utf-8")
    _pdf(sorties / "livrables" / "briefs.pdf", 3)          # un PDF qui ne compte pas une page par brief : pas de numéro de page
    r = vitrine.construire(tmp_path / "site", sorties, LIEN)
    page = (tmp_path / "site" / "societes" / "nokia.html").read_text(encoding="utf-8")
    assert not r["page_par_brief"] and "#page=" not in page and 'href="../telechargements/briefs.pdf"' in page


def test_les_textes_deviennent_des_pages(sorties, tmp_path):
    md = ("# Ton outil : essai\n\nLe code est publié : https://github.com/exemple/prepa-rdv.\n\n"
          "| Société | Durée |\n|---|---|\n| Nokia | 16,4 min |\n")
    (sorties / "livrables").mkdir(parents=True, exist_ok=True)
    (sorties / "livrables" / "ton-outil.md").write_text(md, encoding="utf-8")
    _pdf(sorties / "livrables" / "ton-outil.pdf", 2)
    r = vitrine.construire(tmp_path / "site", sorties, LIEN)
    page = (tmp_path / "site" / "ton-outil.html").read_text(encoding="utf-8")
    assert r["problemes"] == [] and "<title>Ton outil : essai · prepa-rdv</title>" in page
    assert '<a href="https://github.com/exemple/prepa-rdv">https://github.com/exemple/prepa-rdv</a>.' in page
    assert '<div class="defile"><table>' in page and 'href="telechargements/ton-outil.pdf"' in page
    assert not (tmp_path / "site" / "a-200-societes.html").exists()   # un texte absent n'a pas de page


def test_un_dossier_qui_n_est_pas_une_vitrine_n_est_pas_efface(sorties, tmp_path):
    dest = tmp_path / "autre"
    dest.mkdir()
    (dest / "notes.md").write_text("à garder", encoding="utf-8")
    with pytest.raises(ValueError, match="rien n'est effacé"):
        vitrine.construire(dest, sorties, LIEN)
    assert (dest / "notes.md").read_text(encoding="utf-8") == "à garder"
    vitrine.construire(tmp_path / "site", sorties, LIEN)    # une vitrine précédente, elle, est remplacée
    (tmp_path / "site" / "vieux.html").write_text("ancien", encoding="utf-8")
    vitrine.construire(tmp_path / "site", sorties, LIEN)
    assert not (tmp_path / "site" / "vieux.html").exists()


def test_verifier_signale_lien_casse_ancre_absente_et_script(sorties, tmp_path):
    site = tmp_path / "site"
    vitrine.construire(site, sorties, LIEN)
    (site / "casse.html").write_text(f'{vitrine.NOINDEX}<a href="absent.html">x</a><a href="index.html#nulle-part">y</a>'
                                     f'<script>1</script>', encoding="utf-8")
    (site / "sans.html").write_text("<p>rien</p>", encoding="utf-8")
    problemes = vitrine.verifier(site)
    assert "casse.html : lien cassé absent.html" in problemes and "casse.html : ancre absente index.html#nulle-part" in problemes
    assert "casse.html : script" in problemes and "sans.html : pas de noindex" in problemes


@pytest.mark.parametrize("gardees, ecartees, attendu", [
    (0, 0, "Aucune trouvaille pour les six champs de la cartographie."),
    (0, 1, "La seule trouvaille des six champs ne passe pas les contrôles du code. Elle reste"),
    (0, 3, "Aucune des 3 trouvailles des six champs ne passe les contrôles du code. Elles restent"),
    (1, 0, "La seule trouvaille des six champs passe les contrôles du code. Elle garde"),
    (5, 1, "Sur les 6 trouvailles des six champs, 5 passent les contrôles du code. Chacune garde"),
    (5, 2, "Les 2 autres, écartées, restent dans le tableur des trouvailles avec leur motif."),
])
def test_la_phrase_des_trouvailles_s_accorde(gardees, ecartees, attendu):
    assert attendu in vitrine._compte_trouvailles(gardees, ecartees)
