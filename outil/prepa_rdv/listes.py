"""Listes fermées, alias, mots-clés multilingues et domaines de référence.

Valeurs de départ [H] : elles se relisent et se corrigent ici, jamais dans une consigne au modèle.
"""
from __future__ import annotations

import re
import unicodedata

from rapidfuzz import fuzz, process

from .schema import Champ

ERP = (
    "SAP S/4HANA", "SAP ECC", "Oracle Fusion", "Oracle E-Business Suite", "Oracle JD Edwards",
    "Microsoft Dynamics 365", "Microsoft Dynamics AX ou NAV", "Infor", "IFS", "Workday", "Sage",
    "QAD", "Epicor", "autre",
)
ACHATS = (
    "SAP Ariba", "Coupa", "Jaggaer", "Ivalua", "Basware", "GEP", "Zycus", "Oracle Procurement",
    "Microsoft Dynamics 365 Supply Chain", "autre",
)
TMS = (
    "Kyriba", "SAP Treasury", "GTreasury", "FIS", "ION", "Coupa Treasury", "Bellin", "Salmon",
    "Allgeier (Trema)", "autre",
)
FINANCEMENT = (
    "Affacturage avec recours", "Affacturage sans recours", "Affacturage (recours non précisé)",
    "Titrisation de créances", "Affacturage inversé (supply chain finance)", "Escompte dynamique",
    "Billets de trésorerie", "Ligne de crédit renouvelable", "Crédit documentaire ou forfaiting", "autre",
)

LISTES: dict[Champ, tuple[str, ...]] = {
    Champ.ERP: ERP,
    Champ.ACHATS: ACHATS,
    Champ.TMS: TMS,
    Champ.FINANCEMENT: FINANCEMENT,
}

# Variantes courantes → valeur de la liste. Clés déjà normalisées par `norm`.
ALIAS: dict[Champ, dict[str, str]] = {
    Champ.ERP: {
        "s 4hana": "SAP S/4HANA", "sap s 4hana": "SAP S/4HANA", "s4hana": "SAP S/4HANA",
        "s 4 hana": "SAP S/4HANA", "sap s 4 hana": "SAP S/4HANA",  # « SAP S/4 HANA », avec une espace
        "rise with sap": "SAP S/4HANA", "sap rise": "SAP S/4HANA", "sap hana": "SAP S/4HANA",
        "sap ecc": "SAP ECC", "sap erp": "SAP ECC", "sap r 3": "SAP ECC", "sap ecc 6": "SAP ECC",
        "oracle fusion": "Oracle Fusion", "oracle cloud erp": "Oracle Fusion", "oracle fusion cloud erp": "Oracle Fusion",
        "oracle ebs": "Oracle E-Business Suite", "oracle e business suite": "Oracle E-Business Suite",
        "jd edwards": "Oracle JD Edwards", "jde": "Oracle JD Edwards",
        "dynamics 365": "Microsoft Dynamics 365", "microsoft dynamics 365": "Microsoft Dynamics 365",
        "dynamics ax": "Microsoft Dynamics AX ou NAV", "dynamics nav": "Microsoft Dynamics AX ou NAV",
        "workday": "Workday", "infor": "Infor", "ifs": "IFS", "sage": "Sage", "qad": "QAD", "epicor": "Epicor",
    },
    Champ.ACHATS: {
        "ariba": "SAP Ariba", "sap ariba": "SAP Ariba", "sap business network": "SAP Ariba",
        "coupa": "Coupa", "coupa procurement": "Coupa", "jaggaer": "Jaggaer", "ivalua": "Ivalua",
        "basware": "Basware", "gep": "GEP", "gep smart": "GEP", "zycus": "Zycus",
        "oracle procurement": "Oracle Procurement", "oracle procurement cloud": "Oracle Procurement",
        "dynamics 365 supply chain": "Microsoft Dynamics 365 Supply Chain",
    },
    Champ.TMS: {
        "kyriba": "Kyriba", "sap treasury": "SAP Treasury", "sap trm": "SAP Treasury",
        "sap cash management": "SAP Treasury", "sap treasury and risk management": "SAP Treasury",
        "gtreasury": "GTreasury", "fis quantum": "FIS", "fis integrity": "FIS", "fis treasury": "FIS", "fis": "FIS",
        "reval": "ION", "ion reval": "ION", "ion treasury": "ION", "wallstreet suite": "ION", "ion": "ION",
        "coupa treasury": "Coupa Treasury", "bellin": "Bellin", "salmon software": "Salmon", "salmon": "Salmon",
        "trema": "Allgeier (Trema)", "allgeier": "Allgeier (Trema)",
    },
    Champ.FINANCEMENT: {
        "factoring": "Affacturage (recours non précisé)", "affacturage": "Affacturage (recours non précisé)",
        "factoring with recourse": "Affacturage avec recours", "recourse factoring": "Affacturage avec recours",
        "affacturage avec recours": "Affacturage avec recours",
        "non recourse factoring": "Affacturage sans recours", "factoring without recourse": "Affacturage sans recours",
        "affacturage sans recours": "Affacturage sans recours",
        "receivables securitisation": "Titrisation de créances", "receivables securitization": "Titrisation de créances",
        "securitisation": "Titrisation de créances", "securitization": "Titrisation de créances",
        "titrisation": "Titrisation de créances", "abs": "Titrisation de créances", "abcp": "Titrisation de créances",
        "asset backed commercial paper": "Titrisation de créances",
        "reverse factoring": "Affacturage inversé (supply chain finance)",
        "supply chain finance": "Affacturage inversé (supply chain finance)",
        "supply chain financing": "Affacturage inversé (supply chain finance)",
        "supplier finance": "Affacturage inversé (supply chain finance)",
        "supplier financing": "Affacturage inversé (supply chain finance)",
        "affacturage inverse": "Affacturage inversé (supply chain finance)",
        "dynamic discounting": "Escompte dynamique", "escompte dynamique": "Escompte dynamique",
        "commercial paper": "Billets de trésorerie", "neu cp": "Billets de trésorerie", "ecp": "Billets de trésorerie",
        "uscp": "Billets de trésorerie", "billets de tresorerie": "Billets de trésorerie",
        "revolving credit facility": "Ligne de crédit renouvelable", "rcf": "Ligne de crédit renouvelable",
        "documentary credit": "Crédit documentaire ou forfaiting", "letter of credit": "Crédit documentaire ou forfaiting",
        "forfaiting": "Crédit documentaire ou forfaiting",
    },
}

# Mots-clés par champ, en anglais, allemand, français, suédois, finnois et italien. Servent à
# découper les rapports en fenêtres de texte (chemin B) avant de les montrer au modèle.
MOTS_CLES: dict[Champ, tuple[str, ...]] = {
    Champ.ERP: (
        "SAP", "S/4HANA", "ERP", "Oracle", "Dynamics 365", "Workday", "enterprise resource planning",
        "Unternehmenssoftware", "progiciel de gestion", "affärssystem", "toiminnanohjausjärjestelmä", "gestionale",
    ),
    Champ.ACHATS: (
        "Ariba", "Coupa", "Jaggaer", "Ivalua", "Basware", "procurement platform", "e-procurement", "source-to-pay",
        "purchase-to-pay", "Beschaffungsplattform", "plateforme d'achats", "inköp",
    ),
    Champ.TMS: (
        "treasury management system", "Kyriba", "Reval", "GTreasury", "SAP Treasury", "cash management",
        "Treasury-Management-System", "Treasury Management", "trésorerie centralisée", "in-house bank", "cash pooling",
    ),
    Champ.FINANCEMENT: (
        "factoring", "reverse factoring", "supply chain finance", "supplier finance", "supplier finance arrangements",
        "dynamic discounting", "securitisation", "securitization", "receivables", "commercial paper", "affacturage",
        "titrisation", "créances", "Forderungsverkauf", "Factoring", "Verbriefung", "Lieferantenfinanzierung",
        "kundfordringar", "myyntisaamiset", "cessione dei crediti", "ABCP", "NEU CP",
    ),
    Champ.DIRECTION_FINANCIERE: (
        "Chief Financial Officer", "CFO", "Group Treasurer", "Head of Treasury", "directeur financier",
        "directrice financière", "Finanzvorstand", "Finanzchef", "Leiter Treasury", "ekonomichef", "talousjohtaja",
        "direttore finanziario",
    ),
}

# Domaines d'éditeurs, d'intégrateurs, de cabinets et d'associations : type P2.
DOMAINES_P2 = frozenset({
    "sap.com", "kyriba.com", "coupa.com", "ariba.com", "jaggaer.com", "ivalua.com", "basware.com", "gep.com",
    "zycus.com", "oracle.com", "microsoft.com", "workday.com", "infor.com", "ifs.com", "sage.com", "qad.com",
    "epicor.com", "gtreasury.com", "fisglobal.com", "ion.group", "iongroup.com", "bellin.com", "allgeier.com",
    "mulesoft.com", "salesforce.com", "accenture.com", "capgemini.com", "deloitte.com", "pwc.com", "kpmg.com",
    "ey.com", "cognizant.com", "tcs.com", "infosys.com", "wipro.com", "hcltech.com", "afte.com", "eact.eu",
    "silicon-saxony.de",
})
# Offres d'emploi et interventions : type P4.
DOMAINES_P4 = frozenset({
    "indeed.com", "glassdoor.com", "welcometothejungle.com", "lever.co", "greenhouse.io", "workable.com",
    "smartrecruiters.com", "linkedin.com", "youtube.com", "youtu.be", "vimeo.com", "slideshare.net", "monster.com",
    "stepstone.de", "xing.com", "jobteaser.com", "connexion-emploi.com", "jobijoba.com", "indeed.fr", "talent.com", "apec.fr",
    "kununu.com", "lesrencontreseconomiques.fr",
})
# Bases de données commerciales (technologies, entreprises) : type P5, second avis seulement.
DOMAINES_P5 = frozenset({
    "appsruntheworld.com", "slintel.com", "6sense.com", "zoominfo.com", "builtwith.com", "enlyft.com", "theirstack.com",
    "g2.com", "crunchbase.com", "pitchbook.com", "dnb.com", "lei.bloomberg.com", "bloomberg.com", "opencorporates.com",
})
# Diffuseurs d'information réglementée et de communiqués : le type dépend de l'émetteur, lu dans les adresses de contact.
DOMAINES_DIFFUSION = frozenset({
    "businesswire.com", "prnewswire.com", "globenewswire.com", "finanzwire.com", "eqs-news.com", "actusnews.com",
    "newsweb.oslobors.no", "cision.com", "mynewsdesk.com", "news.cision.com", "investegate.co.uk", "euronext.com",
})
# Mots qui, collés au nom du groupe, désignent une filiale ou une entité du groupe (« Saint-Gobain China »).
QUALIFICATIFS_FILIALE = frozenset({
    "china", "chine", "france", "germany", "deutschland", "italia", "italy", "uk", "usa", "america", "americas", "asia", "europe",
    "india", "brasil", "brazil", "espana", "spain", "nordic", "japan", "korea", "canada", "mexico", "poland", "polska",
    "solutions", "networks", "services", "industries", "logistics", "division", "branch", "subsidiary", "filiale", "gmbh", "ltd",
    "limited", "llc", "inc", "bv", "nv",
})
MOTS_CHEMIN_P4 = ("career", "careers", "job", "jobs", "karriere", "stellenangebot", "emploi", "recrut", "vacanc", "rekry")
# Presse et agences de notation : type P3 (c'est aussi le type par défaut d'un domaine inconnu).
DOMAINES_P3 = frozenset({
    "reuters.com", "bloomberg.com", "ft.com", "lesechos.fr", "handelsblatt.com", "moodys.com", "spglobal.com",
    "fitchratings.com", "scope.com", "erp.today", "computerweekly.com", "cfo.com", "treasury-management.com",
})


def norm(texte: str) -> str:
    """Minuscules, sans accents, ponctuation réduite à des espaces."""
    t = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode("ascii").lower()
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def normaliser_valeur(champ: Champ, valeur: str, precision: str | None = None) -> tuple[str, str | None]:
    """Valeur de la liste fermée pour un champ, et précision à garder si c'est « autre ».

    Le code décide, pas le modèle : alias d'abord, rapprochement flou ensuite, « autre » sinon.
    """
    liste = LISTES.get(champ)
    if liste is None:
        return valeur.strip(), precision
    cle = norm(valeur)
    for entree in liste:
        if norm(entree) == cle:
            return entree, precision
    alias = ALIAS.get(champ, {})
    if cle in alias:
        return alias[cle], precision
    # Alias contenu dans le texte (« SAP S/4HANA Cloud sur Azure ») : le plus long gagne.
    contenus = [a for a in alias if re.search(rf"(?<![a-z0-9]){re.escape(a)}(?![a-z0-9])", cle)]
    if contenus:
        return alias[max(contenus, key=len)], precision or valeur.strip()
    candidats = [norm(x) for x in liste if x != "autre"]
    meilleur = process.extractOne(cle, candidats, scorer=fuzz.token_set_ratio, score_cutoff=90)
    if meilleur:
        retenu = [x for x in liste if x != "autre"][meilleur[2]]
        return retenu, precision
    return "autre", precision or valeur.strip()


# --- Noms courts pour le brief ------------------------------------------------------------------
# Le modèle écrit parfois un commentaire à la place du nom d'un produit ou d'une personne (« Aprovall : plateforme KYS de collecte… »).
# Le brief n'affiche que le nom ; le commentaire reste dans les tableurs.

# Un point finit une phrase, sauf après une initiale (« Christian P. Illek ») ou un titre (« Dr. », « Prof. »).
FIN_DE_PHRASE = r"(?<!\b[A-Z])(?<!Dr)(?<!Prof)(?<!Mr)(?<!Mrs)(?<!Ms)(?<!Mme)(?<!Mlle)(?<!St)(?<!Jr)(?<!Sr)\.\s"


def _sans_parentheses_longues(texte: str, mots_max: int) -> str:
    """Retire les parenthèses de plus de `mots_max` mots, et une parenthèse restée ouverte avec ce qui la suit."""
    texte = re.sub(r"\s*\([^()]*\)", lambda m: m.group(0) if len(m.group(0).split()) <= mots_max else "", texte)
    return re.split(r"\s*\(", texte, maxsplit=1)[0] if texte.count("(") > texte.count(")") else texte


def nom_court(texte: str, mots_max: int = 7) -> str:
    """Nom d'un produit : la partie avant la première explication (point, deux-points, point-virgule, virgule)."""
    texte = _sans_parentheses_longues(" ".join(texte.split()), 4)
    tete = re.split(rf"{FIN_DE_PHRASE}|\s:\s|\s;\s|\s[—-]\s|,\s", texte, maxsplit=1)[0].strip()
    mots = (tete or texte).split()
    court = " ".join(mots[:mots_max])
    court = _sans_parentheses_longues(court, 99) if court.count("(") > court.count(")") else court
    mots = court.split()
    while len(mots) > 1 and mots[-1].lower() in MOTS_VIDES_FIN:  # une coupe ne finit pas sur « de », « des », « et »
        mots.pop()
    return " ".join(mots)


MOTS_VIDES_FIN = {"de", "du", "des", "la", "le", "les", "et", "ou", "à", "au", "aux", "en", "par", "pour", "sur", "avec", "comme", "d'", "l'", "un", "une",
                  "of", "the", "and", "for", "with", "von", "der", "die", "das", "und"}


def personne_courte(texte: str, mots_max: int = 16) -> str:
    """Un dirigeant pour le brief : le nom et le titre, sans la remarque entre parenthèses ni la suite après le point-virgule."""
    texte = _sans_parentheses_longues(" ".join(texte.split()), 3)
    texte = re.split(rf"{FIN_DE_PHRASE}|\s;\s", texte, maxsplit=1)[0]
    return " ".join(texte.split()[:mots_max])
