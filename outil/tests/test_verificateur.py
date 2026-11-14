"""Contrôles du code sur les trouvailles, avec des pages simulées. Date de référence : 13 novembre 2026."""
from datetime import date

import pytest

from prepa_rdv.lecteur import Page
from prepa_rdv.resolveur import Entite
from prepa_rdv.schema import Champ, Niveau, StatutValeur, TrouvailleBrute, TypeSource
from prepa_rdv.verificateur import (classer_source, forme_courte, noms_societe, normaliser_texte,
                                    segments_citation, verifier, verifier_citation)

AUJOURDHUI = date(2026, 11, 13)

NOKIA = Entite(nom_saisi="Nokia", nom_retenu="Nokia Oyj", domaines=["nokia.com"], site="https://www.nokia.com")
TEXTE_SAP = ("Nokia, SAP and Microsoft enter strategic multi-year agreement. Nokia has selected Microsoft Azure as the "
             "cloud platform underpinning the transformation. SAP will operate and manage its SAP S/4HANA software "
             "environment hosted on Microsoft Azure. " * 3)


class FauxLecteur:
    def __init__(self, pages: dict[str, Page]):
        self.pages = pages

    def lire(self, url, forcer=False):
        return self.pages.get(url) or Page(url=url, statut=404, erreur="HTTP 404")


def page(url="https://news.sap.com/2026/06/nokia", texte=TEXTE_SAP, date_page="2026-06-30", pages=None, titre="Nokia, SAP and Microsoft"):
    return Page(url=url, url_finale=url, statut=200, type_contenu="text/html", texte=texte, pages=pages or [],
                date_page=date_page, titre=titre, empreinte="abc")


def brute(**kw) -> TrouvailleBrute:
    base = dict(champ=Champ.ERP, valeur="SAP S/4HANA", precision=None, statut_valeur=StatutValeur.PRESENT,
                citation="SAP will operate and manage its SAP S/4HANA software environment hosted on Microsoft Azure",
                citation_langue="en", traduction_fr=None, url="https://news.sap.com/2026/06/nokia", entite_nommee="Nokia",
                type_source=TypeSource.P2, date_source="2026-06-30")
    base.update(kw)
    return TrouvailleBrute(**base)


def verif(b, pages, entite=NOKIA):
    return verifier(b, societe="Nokia", rang=1, entite=entite, lecteur=FauxLecteur(pages), modele="test",
                    version_outil="0", empreinte_prompt="p", aujourdhui=AUJOURDHUI)


# --- Citation ---------------------------------------------------------------------------------

def test_citation_exacte_est_trouvee_et_confirmee():
    t = verif(brute(), {"https://news.sap.com/2026/06/nokia": page()})
    assert t.verifs.citation_trouvee and t.verifs.score_similarite == 1.0
    assert t.verifs.entite == "groupe" and t.niveau == Niveau.CONFIRME
    assert t.valeur_normalisee == "SAP S/4HANA" and t.id == "nokia-erp-1"


def test_citation_inventee_est_rejetee():
    b = brute(citation="Nokia runs Oracle Fusion Cloud ERP across all its finance operations worldwide today")
    t = verif(b, {"https://news.sap.com/2026/06/nokia": page()})
    assert not t.verifs.citation_trouvee and t.niveau == Niveau.NON_TROUVE


def test_citation_reformulee_est_reparee_par_un_passage_de_la_page():
    """Le modèle reformule : le code garde la phrase de la page qui porte le produit, au plus « probable »."""
    b = brute(citation="SAP operates the S/4HANA environment of Nokia on the Azure cloud platform")
    t = verif(b, {"https://news.sap.com/2026/06/nokia": page()})
    assert t.verifs.mode_verification == "citation_remplacee" and t.verifs.citation_du_modele == b.citation
    assert t.verifs.citation_trouvee and t.verifs.score_similarite >= 0.95 and t.citation != b.citation
    assert t.citation.startswith("SAP will operate and manage its SAP S/4HANA")
    assert t.verifs.entite == "groupe" and t.niveau == Niveau.PROBABLE  # jamais « confirmé » : le lien citation-affirmation a changé


def test_citation_qui_n_a_rien_de_la_page_n_est_pas_reparee():
    b = brute(citation="Nokia runs Oracle Fusion Cloud ERP across all its finance operations worldwide today")
    t = verif(b, {"https://news.sap.com/2026/06/nokia": page(texte="Nokia a publié ses résultats du troisième trimestre. " * 6)})
    assert t.verifs.mode_verification == "code" and t.niveau == Niveau.NON_TROUVE


def test_la_reparation_exige_le_produit_dans_le_passage():
    # la page parle de Nokia mais ne nomme pas le produit affirmé : rien à garder
    b = brute(citation="SAP S/4HANA runs the finance of Nokia")
    t = verif(b, {"https://news.sap.com/2026/06/nokia": page(texte="Nokia moves its finance operations to the cloud this year. " * 5)})
    assert t.niveau == Niveau.NON_TROUVE


def test_citation_traduite_depuis_une_autre_langue_est_reparee():
    """Cas Barilla : le modèle écrit en italien une phrase lue en anglais ; la page italienne dit la même chose autrement."""
    texte = ("Barilla, azienda leader al mondo del settore alimentare, ha scelto Kyriba come unica piattaforma di Supply Chain Finance, "
             "Treasury e Risk Management del Gruppo. Kyriba è una realtà attiva a livello worldwide.")
    url = "https://lineaedp.it/rubriche/case-history/barilla-sceglie-kyriba"
    entite = Entite(nom_saisi="Barilla", nom_retenu="Barilla G. e R. Fratelli S.p.A.", domaines=["barillagroup.com"])
    b = brute(champ=Champ.TMS, valeur="Kyriba", url=url, entite_nommee="Barilla", type_source=TypeSource.P3, date_source="2022-02-15",
              citation="Kyriba è stata scelta da Barilla per fornire una piattaforma globale di Working Capital, Treasury e Risk Management",
              citation_langue="it")
    t = verif(b, {url: page(url=url, texte=texte, titre="Barilla sceglie Kyriba per il treasury management", date_page="2022-02-15")}, entite)
    assert t.verifs.mode_verification == "citation_remplacee" and t.niveau == Niveau.PROBABLE
    # le titre de la page ou sa première phrase : l'un et l'autre nomment la société et le produit, et sont recopiés tels quels
    assert "Kyriba" in t.citation and "Barilla" in t.citation and t.verifs.entite == "groupe" and t.verifs.score_similarite >= 0.95


def test_direction_financiere_se_repare_par_le_nom_de_la_personne():
    texte = "Maud Thuaudet, Chief Financial Officer of Compagnie de Saint-Gobain, joined the Group in 2019. " * 2
    url = "https://www.saint-gobain.com/en/group/executive-committee"
    entite = Entite(nom_saisi="Saint-Gobain", nom_retenu="Compagnie de Saint-Gobain", domaines=["saint-gobain.com"])
    b = brute(champ=Champ.DIRECTION_FINANCIERE, valeur="Maud Thuaudet, Chief Financial Officer", url=url, entite_nommee="Saint-Gobain",
              type_source=TypeSource.P1, citation="Maud Thuaudet is the CFO of Saint-Gobain since 2019", citation_langue="en")
    t = verif(b, {url: page(url=url, texte=texte, titre="Executive Committee")}, entite)
    assert t.verifs.mode_verification == "citation_remplacee" and "Maud Thuaudet, Chief Financial Officer" in t.citation


def test_signal_se_repare_par_les_noms_propres_de_la_valeur():
    """Cas Saint-Gobain : le modèle prête à la page de glassonweb une phrase du communiqué ; le titre de la page porte la nomination."""
    texte = "Date: 15 September 2026\nIn this newly created role, Annica Hagen will lead the Group's AI ambitions in support of the strategic objectives."
    url = "https://www.glassonweb.com/news/saint-gobain-appoints-annica-hagen"
    entite = Entite(nom_saisi="Saint-Gobain", nom_retenu="Compagnie de Saint-Gobain", domaines=["saint-gobain.com"])
    b = brute(champ=Champ.SIGNAL, valeur="Nomination d'Annica Hagen comme Chief Artificial Intelligence Officer", url=url, entite_nommee="Saint-Gobain",
              type_source=TypeSource.P3, date_source="2026-09-15", citation_langue="en",
              citation="Annica Hagen has been appointed Chief Artificial Intelligence Officer (CAIO) and member of the Group Executive Committee")
    titre = "Saint-Gobain appoints Annica Hagen as Chief Artificial Intelligence Officer and accelerates AI deployment"
    t = verif(b, {url: page(url=url, texte=texte, titre=titre, date_page="2026-09-15")}, entite)
    assert t.verifs.mode_verification == "citation_remplacee" and "Annica Hagen" in t.citation and t.niveau == Niveau.PROBABLE


def test_une_citation_absente_n_est_pas_reparee_en_mode_seconde_lecture():
    b = brute(citation="SAP operates the S/4HANA environment of Nokia on the Azure cloud platform")
    t = verifier(b, societe="Nokia", rang=1, entite=NOKIA, lecteur=FauxLecteur({}), modele="test", version_outil="0", empreinte_prompt="p",
                 aujourdhui=AUJOURDHUI, lecture=page(), mode="seconde_lecture")
    assert t.verifs.mode_verification == "seconde_lecture" and t.niveau == Niveau.NON_TROUVE


BARILLA = Entite(nom_saisi="Barilla", nom_retenu="Barilla G. e R. Fratelli S.p.A.", domaines=["barillagroup.com"])
URL_SAPINSIDER = "https://sapinsider.org/success-story/barilla-group-shares-the-recipe-for-treasury-success/"
C1_KYRIBA = ("With this project, Barilla Group is adopting Kyriba's innovative digital platform to manage liquidity across "
             "the enterprise")


def relue(passage, b):
    """La page reconstituée d'une seconde lecture : le seul passage recopié par le second agent, et le titre qu'il a lu."""
    p = page(url=b.url, texte=passage, titre="Barilla Group Shares the Recipe for Treasury Success", date_page=None)
    return verifier(b, societe="Barilla", rang=10, entite=BARILLA, lecteur=FauxLecteur({}), modele="test", version_outil="0",
                    empreinte_prompt="p", aujourdhui=AUJOURDHUI, lecture=p, mode="seconde_lecture")


def test_seconde_lecture_plus_courte_que_la_citation_s_accorde():
    """Cas Barilla, relu par Opus : le passage de 8 mots est dans la citation de 17 mots du premier agent."""
    b = brute(champ=Champ.TMS, valeur="Kyriba", url=URL_SAPINSIDER, entite_nommee="Barilla", citation=C1_KYRIBA,
              type_source=TypeSource.P2, date_source="2026-06-30")
    t = relue("Barilla Group is adopting Kyriba’s innovative digital platform", b)
    assert t.verifs.mode_verification == "seconde_lecture" and t.verifs.citation_trouvee
    assert t.citation == "Barilla Group is adopting Kyriba’s innovative digital platform" and t.verifs.citation_du_modele == C1_KYRIBA
    assert t.verifs.score_avant_reparation < 0.95 and t.verifs.entite == "groupe"
    assert t.niveau == Niveau.PROBABLE  # jamais « confirmé » : le code n'a pas lu la page lui-même


@pytest.mark.parametrize("valeur, citation, passage", [
    # quatre mots : l'accord se réduirait au produit et à une date
    ("Kyriba", "Barilla Group recently adopted applications including SAP S/4 HANA in 2025, Kyriba Treasury in 2022",
     "Kyriba Treasury in 2022"),
    # six mots lus deux fois, mais sans le produit affirmé
    ("Kyriba", "With this project, Barilla Group is adopting an innovative digital platform from Kyriba",
     "Barilla Group is adopting an innovative digital platform"),
    # une autre phrase de la même page : rien n'a été lu deux fois
    ("SAP Business Suite", "In 2005 Barilla Group implemented SAP Business Suite as its ERP Financial backbone",
     "Barilla Group has purchased the following applications: SAP Business Suite"),
])
def test_seconde_lecture_sans_accord_reste_rejetee(valeur, citation, passage):
    champ = Champ.TMS if valeur == "Kyriba" else Champ.ERP
    b = brute(champ=champ, valeur=valeur, url=URL_SAPINSIDER, entite_nommee="Barilla", citation=citation,
              type_source=TypeSource.P2, date_source="2026-06-30")
    t = relue(passage, b)
    assert t.niveau == Niveau.NON_TROUVE and t.citation == citation and t.verifs.citation_du_modele is None


def test_citation_de_plus_de_25_mots_est_refusee():
    longue = " ".join(["mot"] * 26)
    t = verif(brute(citation=longue), {"https://news.sap.com/2026/06/nokia": page(texte=longue + " Nokia")})
    assert not t.verifs.citation_longueur_ok and t.niveau == Niveau.NON_TROUVE


def test_ligatures_cesures_et_espaces_sont_neutralises():
    texte = "Le groupe utilise le progi-\nciel de ges­tion SAP S/4HANA  pour la finance ﬁnancière de Nokia."
    assert "progiciel de gestion sap s/4hana pour la finance financière" in normaliser_texte(texte)


def test_citation_a_trous_se_verifie_par_morceaux():
    segs = segments_citation("Nokia has selected Microsoft Azure ... SAP S/4HANA software environment hosted")
    assert len(segs) == 2
    score, _, _ = verifier_citation("Nokia has selected Microsoft Azure ... SAP S/4HANA software environment hosted", page())
    assert score == 1.0


def test_numero_de_page_d_un_pdf():
    pages = ["Rapport annuel. Sommaire.", "Rien ici.", "Le groupe finance ses fournisseurs par un programme de reverse factoring avec trois banques."]
    p = Page(url="https://x.test/r.pdf", url_finale="https://x.test/r.pdf", statut=200, type_contenu="application/pdf",
             texte="\n\f".join(pages), pages=pages)
    score, _, numero = verifier_citation("programme de reverse factoring avec trois banques", p)
    assert score == 1.0 and numero == 3


# --- Adresse et type ------------------------------------------------------------------------------

def test_adresse_qui_repond_mal_est_rejetee():
    t = verif(brute(url="https://introuvable.test/x"), {})
    assert not t.verifs.adresse_ok and t.niveau == Niveau.NON_TROUVE


@pytest.mark.parametrize("url, attendu", [
    ("https://www.nokia.com/about-us/investors/", TypeSource.P1),
    ("https://www.nokia.com/careers/finance-analyst", TypeSource.P4),
    ("https://jobs.nokia.com/finance", TypeSource.P4),
    ("https://news.sap.com/2026/06/nokia", TypeSource.P2),
    ("https://www.kyriba.com/news/barilla", TypeSource.P2),
    ("https://www.lineaedp.it/barilla", TypeSource.P3),
    ("https://www.indeed.com/viewjob?jk=1", TypeSource.P4),
    ("https://www.youtube.com/watch?v=1", TypeSource.P4),
])
def test_type_de_source_recalcule_d_apres_le_domaine(url, attendu):
    assert classer_source(url, ["nokia.com"], TypeSource.P1) == attendu


def test_le_type_propose_par_le_modele_est_corrige():
    b = brute(url="https://exemple.test/blog", type_source=TypeSource.P1)
    t = verif(b, {"https://exemple.test/blog": page(url="https://exemple.test/blog")})
    assert t.verifs.type_source_code == TypeSource.P3 and t.verifs.type_corrige
    assert t.niveau == Niveau.PROBABLE


# --- Entité -----------------------------------------------------------------------------------------

def test_societe_non_nommee_est_rejetee():
    texte = TEXTE_SAP.replace("Nokia", "Une société")
    t = verif(brute(), {"https://news.sap.com/2026/06/nokia": page(texte=texte, titre="Accord", url="https://news.sap.com/2026/06/x")})
    assert t.verifs.entite == "absente" and t.niveau == Niveau.NON_TROUVE


def test_filiale_plafonne_a_probable():
    texte = "Louis Vuitton has deployed SAP S/4HANA software environment across its workshops in France and Spain. " * 3
    b = brute(citation="Louis Vuitton has deployed SAP S/4HANA software environment across its workshops",
              entite_nommee="Louis Vuitton", url="https://news.sap.com/2026/06/lv")
    lvmh = Entite(nom_saisi="LVMH", nom_retenu="LVMH Moët Hennessy Louis Vuitton SE", domaines=["lvmh.com"])
    t = verif(b, {"https://news.sap.com/2026/06/lv": page(url="https://news.sap.com/2026/06/lv", texte=texte, titre="Atelier")}, entite=lvmh)
    assert t.verifs.entite in ("groupe", "filiale") and t.niveau in (Niveau.PROBABLE, Niveau.CONFIRME)


def test_formes_courtes_des_noms():
    assert forme_courte("Compagnie de Saint-Gobain") == "Saint-Gobain"
    assert forme_courte("Nokia Oyj") == "Nokia"
    assert forme_courte("Fresenius SE & Co. KGaA") == "Fresenius"
    assert forme_courte("Barilla G. e R. Fratelli S.p.A.") == "Barilla"
    assert "Fresenius" in noms_societe(Entite(nom_saisi="Fresenius", nom_retenu="Fresenius SE & Co. KGaA"))


# --- Date -------------------------------------------------------------------------------------------

def test_page_qui_affiche_la_date_du_jour_ne_date_rien():
    b = brute(date_source=None)
    t = verif(b, {"https://news.sap.com/2026/06/nokia": page(date_page="2026-11-13")})
    assert t.verifs.date_page is None and t.verifs.sans_date and t.niveau == Niveau.PROBABLE


@pytest.mark.parametrize("url, vivante", [
    ("https://www.nokia.com/about-us/leadership/", True),
    ("https://www.verallia.com/en/investors/investor-contact/", True),
    ("https://www.nokia.com/about-us/news/releases/2024/07/12/accord/", False),
    ("https://www.nokia.com/sites/default/files/annual-report.pdf", False),
    ("https://www.nokia.com/investors/results-q3", False),
])
def test_page_vivante(url, vivante):
    from prepa_rdv.verificateur import est_page_vivante
    assert est_page_vivante(url, TypeSource.P1, "text/html") is vivante
    assert est_page_vivante(url, TypeSource.P2, "text/html") is False


def test_page_vivante_vaut_a_la_date_de_lecture():
    url = "https://www.nokia.com/about-us/leadership/"
    b = brute(url=url, type_source=TypeSource.P1, date_source=None, champ=Champ.DIRECTION_FINANCIERE,
              citation="SAP will operate and manage its SAP S/4HANA software environment hosted on Microsoft Azure")
    t = verif(b, {url: page(url=url, date_page="2020-12-01")})
    assert t.verifs.page_vivante and t.verifs.date_page is None and t.niveau == Niveau.CONFIRME


def test_page_ancienne_est_probable():
    t = verif(brute(), {"https://news.sap.com/2026/06/nokia": page(date_page="2022-02-15")})
    assert t.niveau == Niveau.PROBABLE and t.verifs.age_mois == 56 and t.verifs.dans_fenetre is False


def test_entite_d_un_pdf_se_juge_sur_la_page_de_la_citation():
    """La position de la citation vaut dans sa page : la société doit être nommée sur cette page, pas ailleurs dans le rapport."""
    pages = ["Rapport annuel de Nokia. Sommaire. " + "x " * 600,
             "Le groupe finance ses fournisseurs par un programme de reverse factoring avec trois banques partenaires. " * 2]
    p = Page(url="https://nokia.com/r.pdf", url_finale="https://nokia.com/r.pdf", statut=200, type_contenu="application/pdf",
             texte="\n\f".join(pages), pages=pages, titre="Annual report", empreinte="e")
    b = brute(champ=Champ.FINANCEMENT, valeur="reverse factoring", citation="programme de reverse factoring avec trois banques partenaires",
              url="https://nokia.com/r.pdf", type_source=TypeSource.P1, date_source="2026-03-01", entite_nommee="Nokia")
    t = verif(b, {"https://nokia.com/r.pdf": p})
    assert t.verifs.page_numero == 2
    # Nokia n'est nommée qu'en page 1 : le titre du fichier ne la nomme pas, la citation non plus -> pas « groupe »
    assert t.verifs.entite in ("groupe", "filiale")


@pytest.mark.parametrize("url, texte, propose, attendu", [
    ("https://www.saint-gobain.com.cn/en/news", None, TypeSource.P3, TypeSource.P1),          # site régional de la société
    ("https://www.finanzwire.com/press-release/x", "Contact : ir@saint-gobain.com", TypeSource.P1, TypeSource.P1),
    ("https://www.businesswire.com/news/x", "Media contact : press@kyriba.com", TypeSource.P1, TypeSource.P2),  # communiqué d'un éditeur
    ("https://www.businesswire.com/news/x", "Aucune adresse", TypeSource.P1, TypeSource.P3),
    ("https://www.appsruntheworld.com/customers/x", None, TypeSource.P4, TypeSource.P5),
    ("https://www.jobteaser.com/job/x", None, TypeSource.P3, TypeSource.P4),
    ("https://blog-inconnu.example/x", None, TypeSource.P4, TypeSource.P4),                    # le modèle peut descendre à P4
    ("https://blog-inconnu.example/x", None, TypeSource.P1, TypeSource.P3),                    # mais jamais monter
    ("https://blog-inconnu.example/x", None, TypeSource.P2, TypeSource.P3),
])
def test_classement_de_la_source(url, texte, propose, attendu):
    assert classer_source(url, ["saint-gobain.com"], propose, texte) == attendu


@pytest.mark.parametrize("nommee, attendu", [
    ("Saint-Gobain China", "filiale"),
    ("Saint-Gobain Germany", "filiale"),
    ("Saint-Gobain", "groupe"),
    ("Compagnie de Saint-Gobain", "groupe"),
])
def test_entite_nommee_qualifiee_est_une_filiale(nommee, attendu):
    texte = f"{nommee} finance ses fournisseurs par un programme de reverse factoring avec une banque partenaire. " * 3
    e = Entite(nom_saisi="Saint-Gobain", nom_retenu="Compagnie de Saint-Gobain", domaines=["saint-gobain.com"])
    b = brute(champ=Champ.FINANCEMENT, valeur="reverse factoring", citation="finance ses fournisseurs par un programme de reverse factoring avec une banque partenaire",
              entite_nommee=nommee, url="https://x.example/p", type_source=TypeSource.P3)
    p = page(url="https://x.example/p", texte=texte, titre=nommee)
    assert verif(b, {"https://x.example/p": p}, entite=e).verifs.entite == attendu


def test_nom_legal_complet_n_est_pas_une_filiale():
    e = Entite(nom_saisi="Barilla", nom_retenu="Barilla G. e R. Fratelli S.p.A.", domaines=["barillagroup.com"])
    texte = "BARILLA G. E R. FRATELLI - SOCIETA' PER AZIONI : fiche d'identité de l'entité juridique. " * 4
    b = brute(champ=Champ.IDENTITE, valeur="Barilla", citation="BARILLA G. E R. FRATELLI - SOCIETA' PER AZIONI",
              entite_nommee="BARILLA G. E R. FRATELLI - SOCIETA' PER AZIONI", url="https://lei.example/x", type_source=TypeSource.P3)
    assert verif(b, {"https://lei.example/x": page(url="https://lei.example/x", texte=texte)}, entite=e).verifs.entite == "groupe"


def test_une_citation_qui_reprend_le_titre_de_la_page_n_est_pas_inventee():
    """Faux rejet corrigé le 13 novembre : le titre n'est pas dans le texte principal extrait, mais il fait partie de la page."""
    corps = "Nouveau rôle créé pour piloter les ambitions du groupe en intelligence artificielle. " * 6
    p = page(url="https://presse.example/ia", texte=corps, titre="Annica Hagen has been appointed Chief Artificial Intelligence Officer")
    b = brute(champ=Champ.SIGNAL, valeur="Nomination", citation="Annica Hagen has been appointed Chief Artificial Intelligence Officer",
              url="https://presse.example/ia", type_source=TypeSource.P3, entite_nommee="Nokia")
    t = verif(b, {"https://presse.example/ia": p})
    assert t.verifs.citation_trouvee and t.verifs.score_similarite == 1.0


class LecteurAvecRendu(FauxLecteur):
    """Page lue directement : pauvre. Rendue par JavaScript : complète."""

    def __init__(self, pages, rendues):
        super().__init__(pages)
        self.rendues = rendues
        self.appels = 0

    def lire_rendu(self, url):
        self.appels += 1
        return self.rendues.get(url)


def test_page_pauvre_relue_avec_rendu_javascript():
    """Cas Vattenfall : la page lue directement ne donne que les intitulés ; rendue, elle porte le nom du directeur financier."""
    url = "https://group.vattenfall.com/who-we-are/corporate-governance/group-management"
    entite = Entite(nom_saisi="Vattenfall", nom_retenu="Vattenfall AB", domaines=["vattenfall.com"])
    pauvre = page(url=url, texte="EGM members: President and CEO, Chief Financial Officer, General Counsel.", titre="Group management | Vattenfall")
    rendue = page(url=url, texte="Group management Vattenfall\nKerstin Ahlfont, Chief Financial Officer\nAnna Borg, President and CEO", titre="Group management | Vattenfall")
    rendue.via = "jina"
    b = brute(champ=Champ.DIRECTION_FINANCIERE, valeur="Kerstin Ahlfont, Chief Financial Officer", url=url, entite_nommee="Vattenfall",
              type_source=TypeSource.P1, citation="Kerstin Ahlfont, Chief Financial Officer", citation_langue="en")
    lecteur = LecteurAvecRendu({url: pauvre}, {url: rendue})
    t = verifier(b, societe="Vattenfall", rang=1, entite=entite, lecteur=lecteur, modele="test", version_outil="0", empreinte_prompt="p",
                 aujourdhui=AUJOURDHUI)
    assert lecteur.appels == 1 and t.verifs.lu_via == "jina" and t.verifs.citation_trouvee and t.verifs.mode_verification == "code"
    assert t.niveau == Niveau.CONFIRME  # la citation est celle du modèle, retrouvée telle quelle : le rendu ne plafonne pas


def test_le_rendu_n_est_demande_que_si_la_citation_manque():
    url = "https://news.sap.com/2026/06/nokia"
    lecteur = LecteurAvecRendu({url: page(url=url)}, {})
    verifier(brute(), societe="Nokia", rang=1, entite=NOKIA, lecteur=lecteur, modele="test", version_outil="0", empreinte_prompt="p",
             aujourdhui=AUJOURDHUI)
    assert lecteur.appels == 0


# --- La réparation ne garde que ce qui soutient la valeur ------------------------------------------

def test_un_seul_nom_propre_ne_repare_pas_un_signal():
    """Cas Stadler : « CHF » seul ramenait une phrase sur le nominal des actions. Un signal exige deux noms propres du passage."""
    texte = "Dezember 2025: 100 Millionen Namenaktien mit einem Nominalwert von jeweils CHF 0.20 wurden ausgegeben.\n" * 2
    url = "https://exemple.test/halbjahresbericht-2026.html"
    entite = Entite(nom_saisi="Stadler Rail", nom_retenu="Stadler Rail AG", domaines=["stadlerrail.com"])
    b = brute(champ=Champ.SIGNAL, valeur="Net cash de -424,0 M CHF au 30 juin 2026", url=url, entite_nommee="Stadler Rail",
              type_source=TypeSource.P1, citation="Die Net Cash Position beträgt per 30. Juni 2026 –424.0 Millionen Franken", citation_langue="de")
    t = verif(b, {url: page(url=url, texte=texte + " Stadler Rail", titre="Halbjahresbericht 2026 Stadler Rail")}, entite)
    assert t.verifs.mode_verification == "code" and t.niveau == Niveau.NON_TROUVE


def test_un_dirigeant_se_repare_avec_son_nom_et_un_mot_de_son_poste():
    url = "https://exemple.test/management-board"
    entite = Entite(nom_saisi="voestalpine", nom_retenu="voestalpine AG", domaines=["voestalpine.com"])
    b = brute(champ=Champ.DIRECTION_FINANCIERE, valeur="Gerald Mayer, Chief Financial Officer", url=url, entite_nommee="voestalpine",
              type_source=TypeSource.P1, citation="Mag. Gerald Mayer is responsible for finance at voestalpine", citation_langue="en")
    seul = page(url=url, texte="Gerald Mayer est cité dans la liste des participants à la conférence de voestalpine AG. " * 2, titre="Participants voestalpine")
    assert verif(b, {url: seul}, entite).niveau == Niveau.NON_TROUVE  # le nom sans le poste : rien à garder
    avec_poste = page(url=url, texte="Gerald Mayer is the Chief Financial Officer of voestalpine AG since 2020. " * 2, titre="Management Board voestalpine")
    t = verif(b, {url: avec_poste}, entite)
    assert t.verifs.mode_verification == "citation_remplacee" and "Gerald Mayer" in t.citation


def test_le_balisage_markdown_d_un_lecteur_ne_fait_pas_manquer_une_citation():
    """Cas Vattenfall : le nom et le titre sont sur deux lignes de titre Markdown dans la page rendue."""
    url = "https://exemple.test/group-management"
    entite = Entite(nom_saisi="Vattenfall", nom_retenu="Vattenfall AB", domaines=["vattenfall.com"])
    texte = "![Image 10: Kerstin Ahlfont](https://exemple.test/cdn/kerstin.jpg)\n\n### Kerstin Ahlfont\n\nChief Financial Officer\n\n| Vattenfall | Group |\n|---|---|\n"
    b = brute(champ=Champ.DIRECTION_FINANCIERE, valeur="Kerstin Ahlfont, Chief Financial Officer", url=url, entite_nommee="Vattenfall",
              type_source=TypeSource.P1, citation="Kerstin Ahlfont Chief Financial Officer", citation_langue="en")
    t = verif(b, {url: page(url=url, texte=texte, titre="Group management | Vattenfall")}, entite)
    assert t.verifs.citation_trouvee and t.verifs.mode_verification == "code" and t.verifs.score_similarite >= 0.95


def test_une_adresse_n_est_pas_un_passage_de_remplacement():
    url = "https://exemple.test/p"
    texte = "Voir ![Image: SAP S/4HANA Nokia](https://exemple.test/sap-s4hana-nokia.png) pour le schéma complet du projet.\nNokia a choisi SAP S/4HANA pour son cœur financier."
    b = brute(citation="Nokia selected SAP S/4HANA for its financial core", url=url)
    t = verif(b, {url: page(url=url, texte=texte)})
    assert t.verifs.mode_verification == "citation_remplacee" and "http" not in t.citation and "](" not in t.citation
