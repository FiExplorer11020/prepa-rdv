"""Les contrôles du code sur une trouvaille (cahier des charges, section 6.5).

1. La citation figure dans le texte relu de la source (similarité d'au moins 0,95).
2. L'adresse répond, et son domaine donne le type de source : le code le recalcule, le modèle le propose.
3. La source nomme la société ou une filiale, à côté de la citation. Une filiale est signalée comme telle.
4. La date de la source tombe dans la fenêtre de son type (module `confiance`).
5. Deux valeurs qui se contredisent restent affichées ensemble (`confiance.synthese_champ`).
6. Chaque nombre du brief figure dans la fiche (module `brief`).

Le code relit lui-même chaque page citée. Le modèle ne se contrôle pas.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime, timezone
from urllib.parse import urlparse

from rapidfuzz import fuzz

from .confiance import niveau_trouvaille, parse_date
from .lecteur import Lecteur, Page, domaine_racine
from .listes import (ALIAS, DOMAINES_DIFFUSION, DOMAINES_P2, DOMAINES_P3, DOMAINES_P4, DOMAINES_P5, MOTS_CHEMIN_P4, QUALIFICATIFS_FILIALE,
                     norm, normaliser_valeur)
from .resolveur import Entite
from .schema import (CHAMPS_LISTE_FERMEE, MAX_MOTS_CITATION, Champ, Niveau, StatutValeur, Trouvaille, TrouvailleBrute, TypeSource,
                     Verifs)

SEUIL_CITATION = 0.95
TEXTE_PAUVRE = 4000  # en dessous, une page HTML lue sans la citation peut être une coquille JavaScript : on la relit rendue
LIGATURES = {"ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi", "ﬄ": "ffl", "­": ""}


_MD_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_MD_LIEN = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_MD_DEBUT = re.compile(r"(?m)^[ \t]*(?:#{1,6}|[>*+-]|\d+\.)[ \t]+")
_MD_FILET = re.compile(r"(?m)^[ \t|:-]*-{3,}[ \t|:-]*$")


def sans_markdown(texte: str) -> str:
    """Retire le balisage Markdown que laisse un lecteur de pages : images, liens, titres, puces, tableaux, emphases."""
    t = _MD_IMAGE.sub(" ", texte)
    t = _MD_LIEN.sub(r"\1", t)
    t = _MD_FILET.sub(" ", t)
    t = _MD_DEBUT.sub("", t)
    return re.sub(r"[|*`]+", " ", t)


def normaliser_texte(texte: str) -> str:
    """Texte comparable : balisage Markdown, ligatures, césures de fin de ligne, guillemets, espaces et casse neutralisés."""
    t = unicodedata.normalize("NFKC", sans_markdown(texte))
    for a, b in LIGATURES.items():
        t = t.replace(a, b)
    t = re.sub(r"-\s*\n\s*", "", t)  # mot coupé en fin de ligne
    t = t.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    t = t.replace("–", "-").replace("—", "-").replace(" ", " ")
    return re.sub(r"\s+", " ", t).strip().casefold()


def segments_citation(citation: str) -> list[str]:
    """Une citation à trous (« … » ou « [...] ») se vérifie par morceaux d'au moins quatre mots."""
    morceaux = re.split(r"\s*(?:…|\[\s*\.\.\.\s*\]|\.\.\.)\s*", citation)
    segs = [normaliser_texte(m) for m in morceaux if len(m.split()) >= 4]
    return segs or [normaliser_texte(citation)]


def chercher(segment: str, texte: str) -> tuple[float, int | None]:
    """Score de similarité (0 à 1) et position approximative d'un segment dans un texte normalisé."""
    if not segment or not texte:
        return 0.0, None
    pos = texte.find(segment)
    if pos != -1:
        return 1.0, pos
    al = fuzz.partial_ratio_alignment(segment, texte)
    return (al.score / 100.0, al.dest_start) if al else (0.0, None)


def verifier_citation(citation: str, page: Page) -> tuple[float, int | None, int | None]:
    """Meilleur score, position dans le texte normalisé de la page, numéro de page pour un PDF."""
    segs = segments_citation(citation)
    if page.pages:  # PDF : page par page, pour garder le numéro
        meilleur = (0.0, None, None)
        normees = [normaliser_texte(p) for p in page.pages]
        for numero, texte in enumerate(normees, start=1):
            scores = [chercher(s, texte) for s in segs]
            score = min(s for s, _ in scores)
            if score > meilleur[0]:
                meilleur = (score, scores[0][1], numero)
            if score >= 1.0:
                break
        return meilleur
    # Le titre fait partie de la page : une citation qui reprend le titre n'est pas une invention. Il précède le texte principal.
    texte = normaliser_texte(f"{page.titre}\n{page.texte}" if page.titre and normaliser_texte(page.titre) not in normaliser_texte(page.texte)
                             else page.texte)
    scores = [chercher(s, texte) for s in segs]
    return min(s for s, _ in scores), scores[0][1], None


# --- Réparation d'une citation que le modèle a reformulée, traduite ou mal attribuée --------------
# Le modèle recopie parfois de mémoire : il traduit une citation lue en anglais comme si la page était italienne, ou il prête à une
# page la phrase d'une autre. Si la page est lisible et porte bien la valeur (le produit, la personne), le code garde le passage de
# la page le plus proche de ce que le modèle voulait citer. Ce passage est recopié par le code : il est exact par construction.
# Le niveau est plafonné à « probable », car le lien entre le passage et l'affirmation n'est plus celui que le modèle a écrit.

SEUIL_REPARATION = 0.5
MAX_FENETRES = 4000
MOTS_GENERIQUES = {"system", "systems", "management", "platform", "solution", "solutions", "treasury", "finance", "financial", "cloud",
                   "software", "group", "global", "enterprise", "resource", "planning"}
_PHRASE = re.compile(r"(?<=[.!?])\s+")


def _fenetres(page: Page) -> list[str]:
    """Passages candidats : phrases de la page (titre compris) de 25 mots au plus ; une phrase plus longue est découpée en fenêtres."""
    blocs = [re.sub(r"\s+", " ", p) for p in page.pages] if page.pages else sans_markdown(page.texte).split("\n")  # PDF : les retours coupent les phrases
    if page.titre:
        blocs = [page.titre, *blocs]
    fenetres: list[str] = []
    for bloc in blocs:
        for phrase in _PHRASE.split(bloc):
            mots = phrase.split()
            if len(mots) < 4 or "http" in phrase or "](" in phrase:
                continue  # trop court, ou une adresse : ce n'est pas une phrase de la page
            if len(mots) <= MAX_MOTS_CITATION:
                fenetres.append(" ".join(mots))
                continue
            departs = list(range(0, len(mots) - MAX_MOTS_CITATION + 1, 12))
            if departs[-1] + MAX_MOTS_CITATION < len(mots):
                departs.append(len(mots) - MAX_MOTS_CITATION)
            fenetres += [" ".join(mots[d:d + MAX_MOTS_CITATION]) for d in departs]
        if len(fenetres) > MAX_FENETRES:
            break
    return fenetres


MOTS_ROLE_DIRIGEANT = ("chief financial officer", "financial officer", "cfo", "finance", "financial", "treasur", "tresor", "cash", "finanz",
                       "directeur financier", "directrice financiere", "ekonomi", "talous", "direttore finanziario")


def _exigences(brute: TrouvailleBrute, entite: Entite) -> list[tuple[list[str], int]]:
    """Ce que le passage de remplacement doit contenir : des groupes de mots, avec le nombre minimum de chaque groupe.

    Une valeur qui ne se laisse pas lier à des mots sûrs ne se répare pas : mieux vaut « non trouvé » qu'un passage qui n'y est pour rien.
    """
    champ = brute.champ
    if champ in CHAMPS_LISTE_FERMEE:
        valeur, precision = normaliser_valeur(champ, brute.valeur, brute.precision)
        if valeur != "autre":
            return [(sorted({norm(valeur)} | {a for a, cible in ALIAS.get(champ, {}).items() if cible == valeur}), 1)]
        return [([m for m in norm(precision or brute.valeur).split() if len(m) >= 4 and m not in MOTS_GENERIQUES], 1)]
    if champ == Champ.DIRECTION_FINANCIERE:
        morceaux = re.split(r"[,(]", brute.valeur, maxsplit=1)
        nom = morceaux[0].split()
        role = [m for m in norm(morceaux[1] if len(morceaux) > 1 else "").split() if len(m) >= 4 and m not in MOTS_GENERIQUES]
        # le nom de famille, et un mot du poste annoncé (ou, à défaut, un mot de poste de finance) dans la même phrase
        return [([norm(nom[-1])] if nom and len(norm(nom[-1])) >= 3 else [], 1), (role or [norm(m) for m in MOTS_ROLE_DIRIGEANT], 1)]
    if champ == Champ.SIGNAL:
        propres = [(m.start(), m.group()) for m in re.finditer(r"[A-ZÀ-Ý][A-Za-zÀ-ÿ'’\-]{2,}", brute.valeur)]
        societe = {m for n in noms_societe(entite) for m in norm(n).split()}
        mots = [norm(m) for pos, m in propres if pos > 0 and norm(m) not in societe and norm(m) not in MOTS_GENERIQUES]
        mots = list(dict.fromkeys(m for m in mots if m))
        return [(mots, 2)] if len(mots) >= 2 else []  # un seul nom propre ne suffit pas à lier un passage à un signal
    return []


def _porte_la_valeur(exigences: list[tuple[list[str], int]], texte: str) -> bool:
    """Chaque groupe d'exigences a son minimum de mots dans le texte, en mots entiers.

    Le texte se lit de deux façons : apostrophes retirées (« L'Oréal » donne « loreal ») et apostrophes en espace (« Kyriba's »
    donne « kyriba s »), pour qu'un possessif ne cache pas le produit.
    """
    variantes = (norm(texte), norm(re.sub(r"['’ʼ`´]", " ", texte)))
    present = lambda m: any(re.search(rf"(?<![a-z0-9]){re.escape(m)}(?![a-z0-9])", n) for n in variantes)  # noqa: E731
    return all(sum(1 for m in mots if present(m)) >= minimum for mots, minimum in exigences)


def reparer_citation(brute: TrouvailleBrute, page: Page, entite: Entite) -> tuple[str, float] | None:
    """Passage de la page à garder à la place de la citation du modèle, avec sa proximité, ou None."""
    exigences = _exigences(brute, entite)
    if not exigences or any(not mots for mots, _ in exigences) or not page.ok:
        return None
    cible = norm(brute.citation)
    meilleur: tuple[str, float] | None = None
    for fenetre in _fenetres(page):
        if not _porte_la_valeur(exigences, fenetre):
            continue
        score = fuzz.token_set_ratio(cible, norm(fenetre)) / 100.0
        if meilleur is None or score > meilleur[1] or (score == meilleur[1] and len(fenetre) < len(meilleur[0])):
            meilleur = (fenetre, score)
    return meilleur if meilleur and meilleur[1] >= SEUIL_REPARATION else None


# --- Accord de deux lectures à l'aveugle ---------------------------------------------------------
# Le second lecteur recopie au plus 15 mots, le premier jusqu'à 25 : la citation du premier ne tient souvent pas dans le passage du
# second. Les deux lectures s'accordent aussi quand le passage du second se retrouve mot pour mot dans la citation du premier : ces
# mots-là ont été lus deux fois, sans que le second connaisse la citation. Ils sont six au moins et portent la valeur (le produit,
# la personne, les noms propres du signal). Plus court, l'accord se réduit au nom du produit et à une date, que deux lecteurs
# peuvent écrire sans avoir lu la page.

MIN_MOTS_ACCORD = 6


def accord_des_lectures(brute: TrouvailleBrute, passage: str, entite: Entite) -> str | None:
    """Le passage du second lecteur s'il se retrouve dans la citation du premier et porte la valeur ; sinon None."""
    passage = " ".join(passage.split())
    if not MIN_MOTS_ACCORD <= len(passage.split()) <= MAX_MOTS_CITATION:
        return None
    if chercher(normaliser_texte(passage), normaliser_texte(brute.citation))[0] < SEUIL_CITATION:
        return None
    exigences = _exigences(brute, entite)
    if not exigences or any(not mots for mots, _ in exigences):
        return None
    return passage if _porte_la_valeur(exigences, passage) else None


def _racines_societe(domaines_societe: list[str]) -> tuple[set[str], set[str]]:
    """Domaines racines de la société, et leurs radicaux : « saint-gobain.com » donne le radical « saint-gobain »."""
    racines = {domaine_racine(d) for d in domaines_societe if d}
    return racines, {r.split(".")[0] for r in racines}


def classer_source(url: str, domaines_societe: list[str], propose: TypeSource, texte: str | None = None) -> TypeSource:
    """Type de source d'après le domaine, le chemin et, pour un diffuseur de communiqués, l'émetteur.

    Le code décide quand il reconnaît le domaine. Pour un domaine inconnu, le modèle peut seulement descendre
    (P4 offre d'emploi ou conférence, P5 base de données) : il ne peut jamais monter vers P1 ou P2.
    """
    parsed = urlparse(url)
    hote = (parsed.hostname or "").lower()
    racine = domaine_racine(hote)
    chemin = parsed.path.lower()
    racines, radicaux = _racines_societe(domaines_societe)
    # Un site régional de la société (saint-gobain.com.cn, saint-gobain.fr) est un site de la société.
    de_la_societe = racine in racines or racine.split(".")[0] in radicaux
    sous_domaine_emploi = hote.startswith(("jobs.", "careers.", "karriere.", "emploi."))
    if racine in DOMAINES_P4 or sous_domaine_emploi or (de_la_societe and any(m in chemin for m in MOTS_CHEMIN_P4)):
        return TypeSource.P4
    if racine in DOMAINES_P5:
        return TypeSource.P5
    if de_la_societe:
        return TypeSource.P1
    if racine in DOMAINES_DIFFUSION and texte:
        # Un communiqué est de l'émetteur : on lit les adresses de contact de la page.
        domaines_courriel = {domaine_racine(d) for d in re.findall(r"@([A-Za-z0-9.-]+\.[A-Za-z]{2,})", texte)}
        if domaines_courriel & racines:
            return TypeSource.P1
        if domaines_courriel & {domaine_racine(d) for d in DOMAINES_P2}:
            return TypeSource.P2
        return TypeSource.P3
    if racine in DOMAINES_P2:
        return TypeSource.P2
    if racine in DOMAINES_P3:
        return TypeSource.P3
    return TypeSource.P4 if propose == TypeSource.P4 else TypeSource.P3  # domaine inconnu : presse ou tiers, au plus « probable »


DEBUT_JURIDIQUE = {"compagnie", "de", "les", "laboratoires", "la", "le"}
FIN_JURIDIQUE = {"se", "sa", "ag", "ab", "oyj", "plc", "spa", "kgaa", "co", "&", "group", "groupe", "g", "r", "e", "fratelli"}


def forme_courte(nom: str) -> str:
    """« Compagnie de Saint-Gobain » donne « Saint-Gobain », « Nokia Oyj » donne « Nokia »."""
    mots = nom.replace(",", " ").split()
    while mots and mots[0].lower() in DEBUT_JURIDIQUE:
        mots.pop(0)
    while mots and mots[-1].lower().replace(".", "") in FIN_JURIDIQUE:
        mots.pop()
    return " ".join(mots)


MOTS_DOCUMENT_DATE = ("news", "press", "release", "communique", "media", "report", "rapport", "annual", "results", "presentation",
                      "pdf", "article", "blog", "story", "case-stud", "customer")


def est_page_vivante(url: str, type_code: TypeSource, type_contenu: str) -> bool:
    """Page de la société qui n'a pas de date propre : contact, équipe, relations investisseurs.

    Une telle page vaut à la date de lecture. Un communiqué, un rapport ou un article garde sa date de publication.
    On la reconnaît à son adresse : ni année, ni mot de document daté, et pas un PDF.
    """
    if type_code != TypeSource.P1 or "pdf" in type_contenu:
        return False
    chemin = urlparse(url).path.lower()
    return not re.search(r"(?<!\d)(19|20)\d{2}(?!\d)", chemin) and not any(m in chemin for m in MOTS_DOCUMENT_DATE)


def noms_societe(entite: Entite) -> list[str]:
    noms = [entite.nom_saisi, entite.nom_retenu or "", *entite.alias]
    noms += [forme_courte(n) for n in noms]
    return sorted({n for n in noms if len(n) >= 3}, key=len, reverse=True)


def controler_entite(brute: TrouvailleBrute, page: Page, entite: Entite, position: int | None, numero: int | None = None) -> str:
    """groupe : la société est nommée dans la citation, le titre ou à moins de 800 caractères de la citation.
    filiale : une autre entité est nommée, ou la société n'apparaît qu'à distance. absente : rien de tout cela."""
    texte = normaliser_texte(page.texte)
    noms = [normaliser_texte(n) for n in noms_societe(entite)]
    # La position vaut dans le texte où la citation a été trouvée : la page du PDF, ou la page web entière.
    ref = normaliser_texte(page.pages[numero - 1]) if numero and page.pages and numero <= len(page.pages) else texte
    voisinage = ref[max(0, (position or 0) - 800):(position or 0) + len(brute.citation) + 800] if position is not None else ""
    proche = " ".join([normaliser_texte(brute.citation), normaliser_texte(page.titre or ""), normaliser_texte(page.url_finale or page.url), voisinage])
    mot = lambda n, t: re.search(rf"(?<![a-z0-9]){re.escape(n)}(?![a-z0-9])", t) is not None  # noqa: E731
    nommee_courte = normaliser_texte(forme_courte(brute.entite_nommee))
    noms_courts = {normaliser_texte(forme_courte(n)) for n in noms_societe(entite)}
    qualifie = nommee_courte not in noms_courts and any(mot(n, nommee_courte) for n in noms_courts) \
        and bool(set(re.findall(r"[a-z0-9]+", norm(nommee_courte))) & QUALIFICATIFS_FILIALE)
    if qualifie and mot(nommee_courte, proche):
        return "filiale"  # « Saint-Gobain China » n'est pas « Saint-Gobain » : la citation vaut pour l'entité nommée
    if any(mot(n, proche) for n in noms):
        return "groupe"
    nommee = normaliser_texte(brute.entite_nommee)
    if nommee and mot(nommee, proche):
        return "filiale"  # une entité est nommée à côté de la citation, mais ce n'est pas le groupe lui-même
    if any(mot(n, texte) for n in noms):
        return "filiale"
    return "absente"


def verifier(
    brute: TrouvailleBrute,
    *,
    societe: str,
    rang: int,
    entite: Entite,
    lecteur: Lecteur,
    modele: str,
    version_outil: str,
    empreinte_prompt: str,
    aujourdhui: date | None = None,
    par_champ: bool = False,
    lecture: Page | None = None,
    mode: str = "code",
) -> Trouvaille:
    """Relit la page, applique les contrôles et calcule le niveau de confiance.

    `lecture` fournit une page déjà lue par un autre moyen (seconde lecture). Le niveau est alors plafonné à « probable » :
    « confirmé » est réservé aux citations que le code a relues lui-même.
    """
    aujourdhui = aujourdhui or date.today()
    maintenant = datetime.now(timezone.utc)
    v = Verifs(mode_verification=mode)
    v.citation_mots = len(brute.citation.split())
    v.citation_longueur_ok = 0 < v.citation_mots <= MAX_MOTS_CITATION
    if not v.citation_longueur_ok:
        v.erreurs.append(f"citation de {v.citation_mots} mots (limite {MAX_MOTS_CITATION})")

    page = lecture if lecture is not None else lecteur.lire(brute.url)
    v.statut_http = page.statut
    v.domaine = page.domaine or (urlparse(brute.url).hostname or "")
    v.adresse_ok = page.ok
    if not page.ok:
        v.erreurs.append(page.erreur or "page vide")

    type_code = classer_source(page.url_finale or brute.url, entite.domaines, brute.type_source, page.texte if page.ok else None)
    v.type_source_code, v.type_corrige = type_code, type_code != brute.type_source

    position = None
    if page.ok:
        score, position, numero = verifier_citation(brute.citation, page)
        if score < SEUIL_CITATION and mode == "code" and lecture is None and len(page.texte) < TEXTE_PAUVRE and page.via == "direct":
            # Page lisible mais pauvre : le contenu est peut-être construit par JavaScript. On relit la page rendue.
            rendu = getattr(lecteur, "lire_rendu", lambda _url: None)(brute.url)
            if rendu is not None:
                score_r, position_r, numero_r = verifier_citation(brute.citation, rendu)
                if score_r > score:
                    page, score, position, numero = rendu, score_r, position_r, numero_r
        v.lu_via = page.via
        v.score_similarite, v.page_numero = round(score, 3), numero
        v.citation_trouvee = score >= SEUIL_CITATION
        if not v.citation_trouvee and mode == "code" and lecture is None and brute.statut_valeur == StatutValeur.PRESENT:
            repare = reparer_citation(brute, page, entite)
            if repare is not None:
                score2, position2, numero2 = verifier_citation(repare[0], page)
                if score2 >= SEUIL_CITATION:
                    v.mode_verification, v.citation_du_modele, v.score_avant_reparation = "citation_remplacee", brute.citation, round(score, 3)
                    v.erreurs = [e for e in v.erreurs if not e.startswith("citation de ")]
                    v.erreurs.append(f"citation du modèle absente de la page (similarité {score:.2f}) : passage de la page gardé à sa place")
                    brute = brute.model_copy(update={"citation": repare[0], "traduction_fr": None, "citation_langue": "non déterminée"})
                    v.citation_mots, v.citation_longueur_ok = len(brute.citation.split()), True
                    score, position, numero = score2, position2, numero2
                    v.score_similarite, v.page_numero, v.citation_trouvee = round(score, 3), numero, True
        if not v.citation_trouvee and mode == "seconde_lecture" and lecture is not None and brute.statut_valeur == StatutValeur.PRESENT:
            # Le passage relu à l'aveugle (première ligne de la page reconstituée) se retrouve dans la citation du premier agent :
            # on garde les mots lus deux fois, et la citation du premier reste dans la fiche.
            accord = accord_des_lectures(brute, page.texte.split("\n", 1)[0], entite)
            if accord is not None:
                v.citation_du_modele, v.score_avant_reparation = brute.citation, round(score, 3)
                v.erreurs = [e for e in v.erreurs if not e.startswith("citation de ")]
                v.erreurs.append(f"citation du premier agent plus longue que le passage relu (similarité {score:.2f}) : "
                                 "les mots lus deux fois sont gardés à sa place")
                brute = brute.model_copy(update={"citation": accord, "traduction_fr": None, "citation_langue": "non déterminée"})
                v.citation_mots, v.citation_longueur_ok = len(accord.split()), True
                score, position, numero = verifier_citation(accord, page)
                v.score_similarite, v.page_numero, v.citation_trouvee = round(score, 3), numero, True
        if not v.citation_trouvee:
            v.erreurs.append(f"citation introuvable dans la page (similarité {score:.2f})")
        v.entite = controler_entite(brute, page, entite, position, numero)
        d = page.date_page
        lue = parse_date(d)
        if lue is None or abs((aujourdhui - lue).days) <= 2:
            d = None  # date illisible, ou page qui affiche la date du jour : elle ne date rien
        v.date_page = d
        v.page_vivante = est_page_vivante(page.url_finale or brute.url, type_code, page.type_contenu)
    v.date_retenue = brute.date_source
    if v.page_vivante:
        v.date_page = v.date_retenue = None  # elle vaut à la date de lecture (module `confiance`)

    valeur_norm, precision = normaliser_valeur(brute.champ, brute.valeur, brute.precision)
    niveau = niveau_trouvaille(v, type_code, brute.statut_valeur, brute.champ, maintenant, aujourdhui, par_champ)
    if v.mode_verification != "code" and niveau in (Niveau.CONFIRME, Niveau.ABSENCE_DECLAREE):
        niveau = Niveau.PROBABLE
    return Trouvaille(
        **brute.model_dump(exclude={"precision"}), precision=precision,
        id=f"{re.sub(r'[^a-z0-9]+', '-', norm(societe)).strip('-')}-{brute.champ.value}-{rang}",
        societe=societe, valeur_normalisee=valeur_norm, date_lecture=maintenant, empreinte_source=page.empreinte,
        modele=modele, version_outil=version_outil, empreinte_prompt=empreinte_prompt, verifs=v, niveau=niveau,
    )
