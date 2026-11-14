"""Table de confiance. Le code applique, le modèle ne note jamais sa propre confiance.

Types de preuve : P1 document de la société, P2 tiers qui la nomme (éditeur, intégrateur, association),
P3 presse ou notation, P4 signal indirect (offre d'emploi, conférence), P5 base payante.
Niveaux : confirmé, probable, non trouvé, absence déclarée, contradiction.
"""
from __future__ import annotations

import calendar
import re
from dataclasses import dataclass, field
from datetime import date, datetime

from .listes import norm
from .schema import Champ, CHAMPS_LISTE_FERMEE, Niveau, StatutValeur, TypeSource, Verifs

# Fenêtres de fraîcheur en mois, par type de preuve. Valeurs de départ [H].
FENETRES_MOIS: dict[TypeSource, int] = {
    TypeSource.P1: 24, TypeSource.P2: 36, TypeSource.P3: 24, TypeSource.P4: 12,
}
# Fenêtres par champ : activées seulement si la sonde montre que la plupart des trouvailles utiles
# tombent hors fenêtre (cahier des charges, section 6.4). Valeurs de départ [H].
FENETRES_PAR_CHAMP: dict[Champ, dict[TypeSource, int]] = {
    Champ.DIRECTION_FINANCIERE: {TypeSource.P1: 12, TypeSource.P2: 12, TypeSource.P3: 12, TypeSource.P4: 12},
    **{c: {TypeSource.P1: 60, TypeSource.P2: 60, TypeSource.P3: 24, TypeSource.P4: 12} for c in CHAMPS_LISTE_FERMEE},
}


def fenetre_mois(type_source: TypeSource, champ: Champ, par_champ: bool = False) -> int | None:
    """Nombre de mois de fraîcheur admis, ou None pour P5 (second avis seulement)."""
    if type_source == TypeSource.P5:
        return None
    if par_champ and champ in FENETRES_PAR_CHAMP:
        return FENETRES_PAR_CHAMP[champ].get(type_source)
    return FENETRES_MOIS.get(type_source)


MOIS = {
    "jan": 1, "januar": 1, "janvier": 1, "january": 1, "feb": 2, "februar": 2, "fev": 2, "fevrier": 2, "february": 2, "mar": 3, "mars": 3,
    "marz": 3, "maerz": 3, "march": 3, "apr": 4, "avr": 4, "avril": 4, "april": 4, "may": 5, "mai": 5, "jun": 6, "juin": 6, "juni": 6, "june": 6,
    "jul": 7, "juil": 7, "juillet": 7, "juli": 7, "july": 7, "aug": 8, "aout": 8, "august": 8, "sep": 9, "sept": 9, "septembre": 9,
    "september": 9, "oct": 10, "octobre": 10, "okt": 10, "oktober": 10, "october": 10, "nov": 11, "novembre": 11, "november": 11,
    "dec": 12, "decembre": 12, "dez": 12, "dezember": 12, "december": 12,
}
_MOT_MOIS = r"([A-Za-zéûäöüÉ]{3,10})\.?"


def _mois(nom: str) -> int | None:
    import unicodedata
    cle = unicodedata.normalize("NFKD", nom).encode("ascii", "ignore").decode("ascii").lower()
    return MOIS.get(cle)


def _date_en_lettres(t: str) -> date | None:
    """« March 13, 2019 », « 15 septembre 2026 », « Date: 15 September 2026 », « Mai 2025 » (cette dernière vaut la fin du mois)."""
    for motif, ordre in ((rf"(\d{{1,2}})(?:st|nd|rd|th|er)?\.?\s+{_MOT_MOIS}\s+(\d{{4}})", "jma"), (rf"{_MOT_MOIS}\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(\d{{4}})", "mja"),
                         (rf"{_MOT_MOIS}\s+(\d{{4}})", "ma")):
        m = re.search(motif, t)
        if not m:
            continue
        g = m.groups()
        mois = _mois(g[1] if ordre == "jma" else g[0])
        if mois is None:
            continue
        try:
            if ordre == "jma":
                return date(int(g[2]), mois, int(g[0]))
            if ordre == "mja":
                return date(int(g[2]), mois, int(g[1]))
            return date(int(g[1]), mois, calendar.monthrange(int(g[1]), mois)[1])
        except ValueError:
            continue
    return None


def parse_date(texte: str | None) -> date | None:
    """Date lisible (AAAA, AAAA-MM, AAAA-MM-JJ, JJ/MM/AAAA, JJ.MM.AAAA, ou en lettres : « March 13, 2019 », « 15 septembre 2026 »).

    Une date partielle vaut la fin de sa période : « 2024 » est le 31 décembre 2024. C'est le choix
    le plus indulgent, il se paie d'au plus onze mois d'écart.
    """
    if not texte:
        return None
    t = texte.strip()
    m = re.fullmatch(r"(\d{4})", t)
    if m:
        return date(int(m.group(1)), 12, 31)
    m = re.fullmatch(r"(\d{4})-(\d{1,2})", t)
    if m:
        a, mo = int(m.group(1)), int(m.group(2))
        if 1 <= mo <= 12:
            return date(a, mo, calendar.monthrange(a, mo)[1])
        return None
    m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", t[:10])
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    m = re.fullmatch(r"(\d{1,2})[/.](\d{1,2})[/.](\d{4})", t)
    if m:
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            return None
    return _date_en_lettres(t)


def mois_entre(ancienne: date, recente: date) -> int:
    """Nombre de mois entiers écoulés."""
    mois = (recente.year - ancienne.year) * 12 + (recente.month - ancienne.month)
    if recente.day < ancienne.day:
        mois -= 1
    return max(mois, 0)


def niveau_trouvaille(
    verifs: Verifs,
    type_source: TypeSource,
    statut: StatutValeur,
    champ: Champ,
    date_lecture: datetime | date,
    aujourdhui: date | None = None,
    par_champ: bool = False,
) -> Niveau:
    """Niveau d'une trouvaille isolée. Complète `verifs` (date retenue, âge, fenêtre)."""
    aujourdhui = aujourdhui or date.today()
    lecture = date_lecture.date() if isinstance(date_lecture, datetime) else date_lecture

    # 1. Rejet : une preuve qui ne passe pas les contrôles n'existe pas.
    if not (verifs.citation_trouvee and verifs.citation_longueur_ok and verifs.adresse_ok):
        return Niveau.NON_TROUVE
    if verifs.entite == "absente":
        return Niveau.NON_TROUVE

    # 2. Date : celle de la page, sinon celle que le modèle a relevée. Sans date, une page de la
    # société prend la date de lecture ; tout autre type est plafonné à « probable ».
    d = parse_date(verifs.date_page) or parse_date(verifs.date_retenue)
    verifs.sans_date = d is None
    if d is None and type_source == TypeSource.P1:
        d = lecture
        verifs.sans_date = False
    verifs.date_retenue = d.isoformat() if d else None

    fenetre = fenetre_mois(type_source, champ, par_champ)
    if d is not None:
        verifs.age_mois = mois_entre(d, aujourdhui)
        verifs.dans_fenetre = (verifs.age_mois <= fenetre) if fenetre is not None else None
    else:
        verifs.age_mois = None
        verifs.dans_fenetre = None

    # 3. Niveau.
    if type_source in (TypeSource.P1, TypeSource.P2):
        if verifs.dans_fenetre and verifs.entite == "groupe":
            return Niveau.ABSENCE_DECLAREE if statut == StatutValeur.ABSENCE_DECLAREE else Niveau.CONFIRME
        return Niveau.PROBABLE
    # P3, P4, P5 : au mieux « probable ».
    return Niveau.PROBABLE


# --- Synthèse d'un champ -------------------------------------------------------------------

_RANG = {
    Niveau.CONFIRME: 3, Niveau.ABSENCE_DECLAREE: 3, Niveau.PROBABLE: 2,
    Niveau.CONTRADICTION: 1, Niveau.NON_TROUVE: 0,
}


@dataclass
class ValeurRetenue:
    """Une valeur distincte d'un champ, avec le meilleur niveau qui la soutient."""

    valeur: str
    precision: str | None
    statut: StatutValeur
    niveau: Niveau
    ids: list[str] = field(default_factory=list)
    role: str = ""  # direction financière seulement : directeur, tresorerie ou adjoint


_ADJOINT = re.compile(r"\b(deputy|adjoint|adjointe|stellvertretende?r?|assistant|former|ancien|ancienne|ex)\b|\bvice[ -](chief|cfo|directeur|directrice)\b")
_TRESORERIE = re.compile(r"\b(treasurer|tresorier|tresoriere|treasury|tresorerie|schatzmeister|cash management|cash manager|liquidity|liquiditat)\b")
_DIRECTEUR = re.compile(r"\b(cfo|chief financial officer|directeur financier|directrice financiere|directeur administratif et financier|daf|finance director"
                        r"|financial director|finanzvorstand|finanzchef|finanzdirektor|ekonomichef|talousjohtaja|direttore finanziario|direttrice finanziaria"
                        r"|membre du directoire .{0,40}financ|member of the board .{0,40}financ|responsable des finances)\b")
_DESIGNE = re.compile(r"\b(designe|designee|designate|designated|incoming|successor|successeur|nachfolger|nominated|nomme)\b")
_ORDRE_ROLE = {"directeur": 0, "designe": 1, "tresorerie": 2, "adjoint": 3, "autre": 4, "": 0}


def role_dirigeant(t) -> str:
    """Rôle d'une personne nommée : directeur financier, directeur désigné, responsable de la trésorerie, adjoint, ou autre poste.

    Un adjoint en charge de la trésorerie compte comme responsable de la trésorerie. Deux personnes de rôles différents ne se
    contredisent pas : le directeur financier, son successeur désigné et le trésorier sont des postes distincts. Quand la valeur n'est
    que le nom, le poste se lit dans la citation.
    """
    titre = norm(t.valeur) if ("," in t.valeur or "(" in t.valeur) else norm(f"{t.valeur} {t.citation}")
    if _DESIGNE.search(titre) and not _TRESORERIE.search(titre):
        return "designe"  # le directeur financier désigné succède au sortant : deux postes dans le temps, pas une contradiction
    if _TRESORERIE.search(titre) and not _ADJOINT.search(titre):
        return "tresorerie"
    if _ADJOINT.search(titre):
        return "tresorerie" if _TRESORERIE.search(norm(f"{t.valeur} {t.citation}")) else "adjoint"
    return "directeur" if _DIRECTEUR.search(titre) else "autre"


@dataclass
class SyntheseChamp:
    champ: Champ
    niveau: Niveau
    valeurs: list[ValeurRetenue] = field(default_factory=list)
    contradiction: bool = False
    note: str = ""


def _cle_valeur(t) -> tuple[str, str]:
    """Clé de regroupement : le produit pour une liste fermée, la personne pour la direction financière."""
    if t.champ == Champ.DIRECTION_FINANCIERE:
        nom = t.valeur.split(",")[0].split("(")[0]
        return ("personne", f"{role_dirigeant(t)}:{norm(nom)}")
    if t.valeur_normalisee == "autre":
        return ("autre", norm(t.precision or t.valeur))
    return ("liste", norm(t.valeur_normalisee))


def synthese_champ(champ: Champ, trouvailles: list) -> SyntheseChamp:
    """Niveau d'un champ à partir de ses trouvailles déjà évaluées.

    - Une valeur distincte par produit (ou par personne pour la direction financière).
    - Contradiction : deux personnes différentes au même niveau pour le même poste, ou présence
      et absence déclarée du même produit au même niveau. Les deux restent affichées.
    - Plusieurs produits différents ne se contredisent pas : une pile en compte souvent plusieurs.
    """
    acceptees = [t for t in trouvailles if t.champ == champ and t.niveau != Niveau.NON_TROUVE]
    if not acceptees:
        return SyntheseChamp(champ, Niveau.NON_TROUVE)

    groupes: dict[tuple[str, str], list] = {}
    for t in acceptees:
        groupes.setdefault(_cle_valeur(t), []).append(t)

    # P5, base de données commerciale : second avis seulement. Une valeur que seules des bases nomment ne fait pas le champ ; elle
    # reste dans le tableur des trouvailles. Le constat d'identité, lu dans les registres, n'est pas concerné.
    if champ != Champ.IDENTITE:
        type_lu = lambda t: (t.verifs.type_source_code if t.verifs and t.verifs.type_source_code else t.type_source)  # noqa: E731
        groupes = {cle: membres for cle, membres in groupes.items() if any(type_lu(t) != TypeSource.P5 for t in membres)}
        if not groupes:
            return SyntheseChamp(champ, Niveau.NON_TROUVE,
                                 note="Seule une base de données commerciale nomme une valeur : second avis seulement.")

    valeurs: list[ValeurRetenue] = []
    contradiction = False
    for cle, membres in groupes.items():
        presents = [t for t in membres if t.statut_valeur == StatutValeur.PRESENT]
        absents = [t for t in membres if t.statut_valeur == StatutValeur.ABSENCE_DECLAREE]
        meilleurs = {}
        for statut, liste in ((StatutValeur.PRESENT, presents), (StatutValeur.ABSENCE_DECLAREE, absents)):
            if liste:
                meilleurs[statut] = max(liste, key=lambda t: _RANG[t.niveau])
        if len(meilleurs) == 2:
            rp, ra = _RANG[meilleurs[StatutValeur.PRESENT].niveau], _RANG[meilleurs[StatutValeur.ABSENCE_DECLAREE].niveau]
            if rp == ra:
                contradiction = True
        for statut, t in meilleurs.items():
            valeurs.append(ValeurRetenue(
                valeur=t.valeur_normalisee if cle[0] != "personne" else t.valeur,
                precision=t.precision, statut=statut, niveau=t.niveau,
                ids=[m.id for m in membres if m.statut_valeur == statut],
                role=role_dirigeant(t) if cle[0] == "personne" else "",
            ))

    if champ == Champ.DIRECTION_FINANCIERE:
        # Une contradiction ne vaut qu'entre deux personnes données pour le directeur financier au même niveau. Plusieurs personnes
        # peuvent tenir la trésorerie ou d'autres postes de la finance : elles s'affichent toutes, sans contradiction.
        personnes = [v for v in valeurs if v.statut == StatutValeur.PRESENT and v.role == "directeur"]
        if len(personnes) > 1:
            haut = max(_RANG[v.niveau] for v in personnes)
            if sum(1 for v in personnes if _RANG[v.niveau] == haut) > 1:
                contradiction = True

    valeurs.sort(key=lambda v: (-_RANG[v.niveau], _ORDRE_ROLE.get(v.role, 0)))
    if contradiction:
        return SyntheseChamp(champ, Niveau.CONTRADICTION, valeurs, True,
                             "Deux valeurs incompatibles au même niveau : les deux restent affichées.")
    haut = valeurs[0].niveau
    return SyntheseChamp(champ, haut, valeurs)
