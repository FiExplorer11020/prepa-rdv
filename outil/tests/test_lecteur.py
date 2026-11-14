"""Lecture polie, hors ligne : les réponses réseau sont simulées."""
import httpx
import pytest

from prepa_rdv.lecteur import Lecteur, domaine_racine, fenetres

HTML = """<html><head><title>Nokia, SAP et Microsoft</title>
<meta property="article:published_time" content="2026-06-30"></head>
<body><article><h1>Accord pluriannuel</h1>
<p>Nokia exploite SAP S/4HANA pour la finance centrale et choisit Microsoft Azure comme plateforme cloud.</p>
<p>""" + "Texte de remplissage pour dépasser le seuil de lecture. " * 12 + """</p></article></body></html>"""


def lecteur(tmp_path, gestionnaire):
    l = Lecteur(dossier_cache=tmp_path, pause_s=0, contact="essai")
    l.client = httpx.Client(transport=httpx.MockTransport(gestionnaire), follow_redirects=True)
    return l


def serveur(robots="User-agent: *\nAllow: /", page=HTML, statut=200, type_contenu="text/html"):
    def h(req: httpx.Request) -> httpx.Response:
        if req.url.path == "/robots.txt":
            return httpx.Response(200, text=robots)
        return httpx.Response(statut, text=page, headers={"content-type": type_contenu})
    return h


def test_lecture_html(tmp_path):
    p = lecteur(tmp_path, serveur()).lire("https://exemple.test/a")
    assert p.ok and "SAP S/4HANA" in p.texte
    assert p.date_page == "2026-06-30" and p.empreinte


def test_cache_evite_le_reseau(tmp_path):
    appels = []
    base = serveur()

    def h(req):
        appels.append(str(req.url))
        return base(req)
    l = lecteur(tmp_path, h)
    l.lire("https://exemple.test/a")
    n = len(appels)
    p = l.lire("https://exemple.test/a")
    assert p.depuis_cache and len(appels) == n


def test_robots_refuse_sans_contournement(tmp_path):
    p = lecteur(tmp_path, serveur(robots="User-agent: *\nDisallow: /")).lire("https://exemple.test/a")
    assert not p.ok and p.erreur == "refusé par robots.txt"


def test_403_n_est_pas_contourne(tmp_path):
    p = lecteur(tmp_path, serveur(statut=403, page="Forbidden")).lire("https://exemple.test/a")
    assert not p.ok and p.statut == 403 and p.via == "direct"


def test_robots_en_panne_arrete_la_lecture(tmp_path):
    def h(req):
        return httpx.Response(503) if req.url.path == "/robots.txt" else httpx.Response(200, text=HTML)
    p = lecteur(tmp_path, h).lire("https://exemple.test/a")
    assert p.erreur == "refusé par robots.txt"


def test_adresse_non_web(tmp_path):
    assert lecteur(tmp_path, serveur()).lire("file:///etc/passwd").erreur == "adresse non web"


def test_domaine_racine():
    assert domaine_racine("www.saint-gobain.com") == "saint-gobain.com"
    assert domaine_racine("investors.nokia.com") == "nokia.com"
    assert domaine_racine("www.bbc.co.uk") == "bbc.co.uk"


def test_fenetres_fusionnent_et_classent():
    pages = ["Introduction sans rapport. " * 30,
             "Le groupe a recours au factoring et à la titrisation de créances. Le supplier finance est limité. " + "x " * 800]
    w = fenetres(pages, ("factoring", "supplier finance", "titrisation"), largeur=60)
    assert w and w[0].page == 2
    assert set(w[0].mots) == {"factoring", "supplier finance", "titrisation"}


def test_fenetres_respectent_les_mots_entiers():
    assert fenetres(["Le mot ERPS et SAPIN ne comptent pas."], ("ERP", "SAP")) == []
