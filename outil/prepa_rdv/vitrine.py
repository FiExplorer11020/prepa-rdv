"""La vitrine : un site statique tiré des fiches et des livrables (D5, D24).

Le site ne dit que ce que disent déjà les PDF et les tableurs : les briefs, les trouvailles retenues avec leur citation,
les verdicts de l'audit et les deux textes. Il s'écrit après les livrables, hors des trois heures du cas. Pas de clé, pas
de script, pas de mesure d'audience, et chaque page porte `noindex`.

Couleurs émail et cobalt, le cobalt sur une seule chose par page : le téléchargement principal. Titres en Fraunces, texte
en Figtree. Ce sont des instances statiques (Fraunces à la taille optique 144 et SOFT 100, Figtree en 400, 500 et 600),
servies par le site lui-même, sous licence SIL Open Font License 1.1 dont le texte les accompagne.
"""
from __future__ import annotations

import html
import json
import re
import shutil
import statistics
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from pypdf import PdfReader

from . import audit, bilan as bilan_mod, brief, gabarit, horloge, textes
from .run import charger_fiches, slug
from .schema import LIBELLES_CHAMP, Niveau
from .tableur import CHAMPS_CARTO, LEGENDE, valeur_cellule

POLICES = Path(__file__).parent / "polices"
TELECHARGEMENTS = ("briefs.pdf", "cartographie.xlsx", "trouvailles.xlsx", "ton-outil.pdf", "a-200-societes.pdf")
TEXTES = (("ton-outil", "Comment il fonctionne"), ("a-200-societes", "À 200 sociétés"))
BANDEAU = "Scénario fictif. Cas pratique de novembre 2026, fait sur des informations publiques."
NOINDEX = '<meta name="robots" content="noindex">'
# L'en-tête vaut pour les fichiers que la balise ne couvre pas : PDF, tableurs, polices.
VERCEL = {"headers": [{"source": "/(.*)", "headers": [{"key": "X-Robots-Tag", "value": "noindex"}]}]}

CLASSES = {Niveau.CONFIRME: "n-confirme", Niveau.PROBABLE: "n-probable", Niveau.NON_TROUVE: "n-non-trouve",
           Niveau.ABSENCE_DECLAREE: "n-absence", Niveau.CONTRADICTION: "n-contradiction"}
# Les niveaux accordés à « cellule » : 25 confirmées, 1 non trouvée.
FEMININ = {Niveau.CONFIRME: ("confirmée", "confirmées"), Niveau.PROBABLE: ("probable", "probables"),
           Niveau.NON_TROUVE: ("non trouvée", "non trouvées"), Niveau.ABSENCE_DECLAREE: ("absence déclarée", "absences déclarées"),
           Niveau.CONTRADICTION: ("contradiction", "contradictions")}
ORDRE_BARRE = (Niveau.CONFIRME, Niveau.PROBABLE, Niveau.ABSENCE_DECLAREE, Niveau.CONTRADICTION, Niveau.NON_TROUVE)
RANG = {Niveau.CONFIRME.value: 0, Niveau.ABSENCE_DECLAREE.value: 1, Niveau.CONTRADICTION.value: 2, Niveau.PROBABLE.value: 3}

_e = html.escape


def _pastille(niveau: str) -> str:
    n = Niveau(niveau)
    return f'<span class="pastille {CLASSES[n]}">{_e(n.value)}</span>'


def _accord(n: int, niveau: Niveau) -> str:
    return f"{n} {FEMININ[niveau][0 if n == 1 else 1]}"


def _taille(p: Path) -> str:
    ko = p.stat().st_size / 1024
    return f"{textes._n(ko / 1024, 1)} Mo" if ko >= 1024 else f"{textes._n(ko)} Ko"


def _refs(texte: str) -> str:
    """Le texte échappé, ses renvois [n] devenus des liens vers la liste des sources de la page."""
    return re.sub(r"\[(\d+)\]", r'<a class="renvoi" href="#source-\1">[\1]</a>', _e(texte))


def _page(titre: str, description: str, corps: str, racine: str = "", actif: str = "", lien_outil: str = "",
          textes_presents: tuple[tuple[str, str], ...] = TEXTES) -> str:
    nav = [("index.html#societes", "Les sociétés", "accueil")] + [(f"{nom}.html", libelle, nom) for nom, libelle in textes_presents]
    liens = "".join(f'<a href="{racine}{h}"' + (' aria-current="page"' if k == actif else "") + f">{_e(t)}</a>" for h, t, k in nav)
    if lien_outil:
        liens += f'<a href="{_e(lien_outil)}">Le code</a>'
    pied = _e(gabarit.PIED) + (f' <a href="{_e(lien_outil)}">Le code, les journaux et la méthode</a>.' if lien_outil else "")
    return ('<!doctype html>\n<html lang="fr">\n<head>\n<meta charset="utf-8">\n'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">\n{NOINDEX}\n'
            f'<meta name="description" content="{_e(description)}">\n<title>{_e(titre)}</title>\n'
            f'<link rel="stylesheet" href="{racine}style.css">\n</head>\n<body>\n'
            f'<div class="bandeau"><div class="cadre">{_e(BANDEAU)}</div></div>\n'
            f'<header class="entete"><div class="cadre"><a class="marque" href="{racine}index.html">{_e(gabarit.MARQUE)}</a>'
            f'<nav class="nav" aria-label="Pages du site">{liens}</nav></div></header>\n'
            f'<main class="cadre">\n{corps}\n</main>\n'
            f'<footer class="pied"><div class="cadre">{pied}</div></footer>\n</body>\n</html>\n')


def _bouton(href: str, libelle: str, detail: str = "", accent: bool = False) -> str:
    poids = f' <span class="poids">{_e(detail)}</span>' if detail else ""
    return f'<a class="bouton{" accent" if accent else ""}" href="{_e(href)}">{_e(libelle)}{poids}</a>'


def _accueil(fiches: list[dict], telechargements: Path, jugements: dict[str, dict[str, dict]], lien_outil: str,
             textes_presents: tuple[tuple[str, str], ...] = TEXTES) -> str:
    n = len(fiches)
    t = bilan_mod.bilan_lot(fiches)["total"]
    js = [f.get("jetons") or {} for f in fiches]
    duree = statistics.mean([x.get("duree_s") or 0 for x in js] or [0]) / 60
    cout = statistics.mean([x.get("cout_estime_usd") or 0 for x in js] or [0])
    actif = horloge.temps_actif() / 60
    cellules = Counter(Niveau(f["synthese"][c.value]["niveau"]) for f in fiches for c in CHAMPS_CARTO)
    total = sum(cellules.values())

    actions = []
    if (telechargements / "briefs.pdf").exists():
        actions.append(_bouton("telechargements/briefs.pdf", f"Les {n} briefs", f"PDF, {_taille(telechargements / 'briefs.pdf')}", accent=True))
    if (telechargements / "cartographie.xlsx").exists():
        actions.append(_bouton("telechargements/cartographie.xlsx", "La cartographie", "tableur"))
    tete = (f'<section class="ouverture"><p class="leg">Cas pratique, novembre 2026</p>'
            f'<h1>Préparer un <span class="insecable">rendez-vous</span> avec une direction financière</h1>'
            f'<p class="chapo">Pour une grande entreprise, l\'outil cherche sur sources publiques son ERP, sa plateforme d\'achats, '
            f"son TMS et ses financements court terme. Chaque information porte la citation retrouvée sur sa page, l'adresse de la "
            f"page, sa date et un niveau de confiance que le code fixe d'après une table.</p>"
            f"<p>Le cas demande de préparer {n} rendez-vous en trois heures de construction au plus, avec un outil qui fait le "
            f"travail. Ce site reprend ce que contiennent les briefs et les tableurs.</p>"
            f'<div class="actions">{"".join(actions)}</div></section>')

    chiffres = [(f"{n}", "", "sociétés, un brief d'une page chacune.", "Les fiches"),
                (f"{t['gardees']}", f"sur {t['trouvailles']}", "trouvailles passent les contrôles du code, avec leur citation.", "trouvailles.xlsx")]
    premier, relance, second = (jugements.get(x) or {} for x in audit.TIRAGES)
    if premier:
        r1, rc = audit.resume(premier.values()), audit.resume({**premier, **relance}.values())
        avant = f" ({r1['juste']} avant deux règles d'affichage)" if relance else ""
        apres = ""
        if second:
            r2 = audit.resume(second.values())
            apres = f" Second tirage, {r2['cellules']} cellules neuves : {r2['juste']} sur {r2['verifiables']}."
        chiffres.append((f"{rc['juste']}", f"sur {rc['verifiables']}",
                         f"cellules jugées justes par un audit à l'aveugle, sur les vérifiables{avant}.{apres}", "Feuilles « Audit » de la cartographie"))
    chiffres.append((f"{textes._n(cout, 2)} $", "", "par société en moyenne, estimés au tarif de liste de l'API. L'accès passe par un "
                     "abonnement : ce coût n'est pas facturé.", "Registre des jetons"))
    chiffres.append((textes._n(duree, 1), "min", "d'agent par société, en moyenne.", "Registre des jetons"))
    if actif:
        chiffres.append((textes._n(actif), "min", f"de construction active, pour un plafond de {horloge.PLAFOND_MINUTES}.", "Journal de l'horloge"))
    tuiles = "".join(f'<div class="chiffre"><p class="n">{_e(a)}' + (f" <small>{_e(b)}</small>" if b else "")
                     + f'</p><p class="l">{_e(c)}</p><p class="src">{_e(d)}</p></div>' for a, b, c, d in chiffres)
    mesures = f'<section><h2>Ce que les journaux mesurent</h2><div class="chiffres">{tuiles}</div></section>'

    segments = [(niv, cellules[niv]) for niv in ORDRE_BARRE if cellules[niv]]
    aria = ", ".join(_accord(k, niv) for niv, k in segments)
    barre = "".join(f'<span class="{CLASSES[niv]}" style="flex-grow:{k}" title="{_e(_accord(k, niv))}"></span>' for niv, k in segments)
    legende = "".join(
        f"<div><dt>{_pastille(niv)}<span class=\"compte\">{_e(_accord(cellules[Niveau(niv)], Niveau(niv)) if cellules[Niveau(niv)] else 'aucune cellule')}</span></dt>"
        f"<dd>{_e(definition)}</dd></div>" for niv, definition in LEGENDE)
    niveaux = (f'<section id="niveaux"><h2>Les {total} cellules de la cartographie, par niveau</h2>'
               f'<p>Six champs par société : direction financière, ERP, achats, TMS, financements court terme et signal récent. '
               f"Le code fixe le niveau de chaque cellule d'après la table ci-dessous.</p>"
               f'<div class="barre" role="img" aria-label="{_e(aria)}">{barre}</div><dl class="niveaux">{legende}</dl></section>')

    etapes = "".join(f'<li class="etape"><div class="tete"><span class="n">{i}</span><span class="etiquette">{_e(qui)}</span></div>'
                     f"<b>{_e(nom)}</b><p>{_e(sortie)}</p></li>" for i, (nom, qui, sortie) in enumerate(textes.ETAPES, start=1))
    modele = [str(i) for i, (_, qui, _) in enumerate(textes.ETAPES, start=1) if qui == "Modèle"]
    chaine = (f'<section><h2>La chaîne, en six étapes</h2><p>Le modèle tient les étapes {", ".join(modele[:-1])} et {modele[-1]}, '
              f"le code les autres.</p><ol class=\"etapes\">{etapes}</ol></section>")

    lignes = []
    for i, f in enumerate(fiches, start=1):
        compte = Counter(Niveau(f["synthese"][c.value]["niveau"]) for c in CHAMPS_CARTO)
        resume = " · ".join(_accord(compte[niv], niv) for niv in ORDRE_BARRE if compte[niv])
        e = f.get("entite") or {}
        meta = " · ".join(x for x in (e.get("pays"), e.get("statut")) if x)
        lignes.append(f'<li><a href="societes/{slug(f["societe"])}.html"><span class="n">{i}</span>'
                      f'<span class="t"><span class="nom">{_e(f["societe"])}</span><span class="meta">{_e(meta)}</span></span>'
                      f'<span class="niv">{_e(resume)}</span></a></li>')
    societes = (f'<section id="societes"><h2>Les {n} sociétés</h2><p>Dans l\'ordre des briefs. Chaque page reprend le brief et ses '
                f'sources, puis les trouvailles retenues avec leur citation.</p><ol class="sommaire">{"".join(lignes)}</ol></section>')

    presents = {nom for nom, _ in textes_presents}
    cartes = [f'<a class="carte" href="{nom}.html"><span class="titre">{_e(titre)}</span><span class="l">{_e(texte)}</span></a>'
              for nom, titre, texte in (
                         ("ton-outil", "Ton outil : comment il fonctionne et où il s'est trompé",
                          "Les outils et les sources, le temps et le coût de chaque société, le prompt principal, les erreurs relevées."),
                         ("a-200-societes", "Et à 200 sociétés ?", f"Ce qui casse et ce qui change pour passer de {n} à 200 sociétés."))
              if nom in presents]
    deux = (f'<section><h2>{"Les deux textes" if len(cartes) > 1 else "Le texte"}</h2><div class="cartes">{"".join(cartes)}</div></section>'
            if cartes else "")
    return _page(gabarit.MARQUE, f"{n} briefs de rendez-vous préparés sur informations publiques, citées et datées.",
                 tete + mesures + niveaux + chaine + societes + deux, actif="accueil", lien_outil=lien_outil,
                 textes_presents=textes_presents)


def _trouvaille(t: dict, entite: dict, jugement: dict | None) -> str:
    v = t["verifs"]
    valeur = valeur_cellule({"valeur": t["valeur"], "precision": t["precision"], "statut": t["statut_valeur"]}, t, entite)
    domaine = v.get("domaine") or (urlparse(t["url"]).hostname or t["url"])
    quand = (v.get("date_retenue") or "")[:4] or "date non lue"
    mode = " · seconde lecture" if v.get("mode_verification") == "seconde_lecture" else ""
    langue = f' lang="{_e(t["citation_langue"])}"' if t.get("citation_langue") else ""
    traduction = f'<p class="traduction">Traduction : {_e(t["traduction_fr"])}</p>' if t.get("traduction_fr") else ""
    verdict = ""
    if jugement:
        ecart = f", {jugement['ecart']}" if jugement.get("ecart") else ""
        raison = f" {jugement['raison']}" if jugement.get("raison") else ""
        verdict = f'<p class="audit"><b>Audit à l\'aveugle : {_e(jugement["verdict"] + ecart)}.</b>{_e(raison)}</p>'
    return (f'<li class="trouvaille"><div class="haut"><span class="valeur">{_e(valeur)}</span>{_pastille(t["niveau"])}</div>'
            f'<p class="src"><a href="{_e(t["url"])}">{_e(domaine.removeprefix("www."))}</a>, {_e(quand)}{mode}</p>'
            f"<details><summary>Citation</summary><blockquote{langue}>{_e(t['citation'])}</blockquote>{traduction}</details>{verdict}</li>")


def _compte_trouvailles(gardees: int, ecartees: int) -> str:
    """La phrase qui ouvre les trouvailles d'une société : celles des six champs de la cartographie, pas celles de l'identité."""
    total = gardees + ecartees
    if not total:
        return "Aucune trouvaille pour les six champs de la cartographie."
    if not gardees:
        debut = "La seule trouvaille des six champs ne passe pas" if total == 1 else f"Aucune des {total} trouvailles des six champs ne passe"
        return (f"{debut} les contrôles du code. {'Elle reste' if total == 1 else 'Elles restent'} dans le tableur des trouvailles, "
                f"avec le motif.")
    phrase = (f"Sur les {total} trouvailles des six champs, {gardees} {'passent' if gardees > 1 else 'passe'} les contrôles du code."
              if total > 1 else "La seule trouvaille des six champs passe les contrôles du code.")
    phrase += (" Chacune garde" if gardees > 1 else " Elle garde") + (" la citation retrouvée sur sa page, et le verdict de l'audit "
                                                                    "quand la cellule a été tirée.")
    if ecartees == 1:
        phrase += " L'autre, écartée, reste dans le tableur des trouvailles avec son motif."
    elif ecartees:
        phrase += f" Les {ecartees} autres, écartées, restent dans le tableur des trouvailles avec leur motif."
    return phrase


def _page_societe(f: dict, numero: int, fiches: list[dict], telechargements: Path, page_pdf: bool,
                  jugements: dict[str, dict], lien_outil: str, textes_presents: tuple[tuple[str, str], ...] = TEXTES) -> str:
    c = brief.composer(f)
    entite = f.get("entite") or {}
    actions = []
    if (telechargements / "briefs.pdf").exists():
        actions.append(_bouton(f"../telechargements/briefs.pdf{f'#page={numero}' if page_pdf else ''}", "Le brief en PDF", accent=True))
    for nom, libelle in (("cartographie.xlsx", "La cartographie"), ("trouvailles.xlsx", "Toutes les trouvailles")):
        if (telechargements / nom).exists():
            actions.append(_bouton(f"../telechargements/{nom}", libelle, "tableur"))
    tete = (f'<section class="ouverture"><p class="leg"><a href="../index.html#societes">Les {len(fiches)} sociétés</a> · '
            f'brief {numero} sur {len(fiches)}</p><h1>{_e(c["societe"])}</h1><p class="meta">{_e(c["entete"])}</p>'
            f'<div class="actions">{"".join(actions)}</div></section>')

    lignes = "".join(f'<tr><td class="champ">{_e(x["champ"])}</td><td class="valeur">{_refs(x["valeur"])}</td>'
                     f'<td class="niveau">{_pastille(x["niveau"])}</td></tr>' for x in c["lignes"])
    sait = (f"<section><h2>Ce qu'on sait</h2><table class=\"brief\"><thead><tr><th>Champ</th><th>Valeur et source</th>"
            f'<th class="niveau">Niveau</th></tr></thead><tbody>{lignes}</tbody></table>'
            f'<p class="leg">Les niveaux sont définis sur la <a href="../index.html#niveaux">page d\'accueil</a>.</p></section>')
    angle = "".join(f"<p>{_e(p)}</p>" for p in c["angle"])
    questions = "".join(f"<li>{_e(q)}</li>" for q in c["questions"])
    contact = f'<p class="contact">{_e(c["contact"])}</p>' if c["contact"] else ""
    rdv = (f'<section><h2>L\'angle pour CA|ES <span class="etiquette">hypothèse</span></h2>{angle}'
           f'<h2 class="suite">Questions pour le rendez-vous</h2><ol class="questions">{questions}</ol>{contact}</section>')
    sources = "".join(f'<li id="source-{s["n"]}" value="{s["n"]}"><a href="{_e(s["url"])}">{_e(s["domaine"])}</a>, {_e(s["annee"])}'
                      f'<span class="adresse">{_e(s["url"])}</span></li>' for s in c["sources"])
    liste = (f'<section id="sources"><h2>Les sources du brief</h2><ol class="sources">{sources}</ol></section>' if sources else
             '<section id="sources"><h2>Les sources du brief</h2><p>Aucune source retenue.</p></section>')

    champs = {ch.value for ch in CHAMPS_CARTO}
    gardees = [t for t in f["trouvailles"] if t["champ"] in champs and t["niveau"] != Niveau.NON_TROUVE.value]
    ecartees = sum(1 for t in f["trouvailles"] if t["champ"] in champs and t["niveau"] == Niveau.NON_TROUVE.value)
    blocs = []
    for ch in CHAMPS_CARTO:
        ts = [t for t in gardees if t["champ"] == ch.value]
        ts.sort(key=lambda t: t["verifs"].get("date_retenue") or "", reverse=True)
        ts.sort(key=lambda t: RANG.get(t["niveau"], 9))
        if ts:
            items = "".join(_trouvaille(t, entite, jugements.get(t["id"])) for t in ts)
            blocs.append(f'<h3>{_e(LIBELLES_CHAMP[ch])}</h3><ul class="trouvailles">{items}</ul>')
    trouvailles = (f"<section><h2>Les trouvailles retenues</h2><p>{_compte_trouvailles(len(gardees), ecartees)}</p>"
                   f"{''.join(blocs)}</section>")

    i = numero - 1
    voisines = []
    if i > 0:
        voisines.append(f'<a href="{slug(fiches[i - 1]["societe"])}.html">← {_e(fiches[i - 1]["societe"])}</a>')
    if i < len(fiches) - 1:
        voisines.append(f'<a class="apres" href="{slug(fiches[i + 1]["societe"])}.html">{_e(fiches[i + 1]["societe"])} →</a>')
    nav = f'<nav class="voisines" aria-label="Sociétés voisines">{"".join(voisines)}</nav>'
    return _page(f"{c['societe']} · {gabarit.MARQUE}",
                 f"Brief de rendez-vous pour {c['societe']} : direction financière, ERP, achats, TMS et financements court terme, avec leurs sources.",
                 tete + sait + rdv + liste + trouvailles + nav, racine="../", lien_outil=lien_outil, textes_presents=textes_presents)


def _page_texte(nom: str, md: str, telechargements: Path, lien_outil: str,
                textes_presents: tuple[tuple[str, str], ...] = TEXTES) -> str:
    corps = textes.md_corps(md).replace("<table>", '<div class="defile"><table>').replace("</table>", "</table></div>")
    # Une adresse écrite en clair dans le texte devient un lien ; celles déjà dans une balise ne bougent pas.
    corps = re.sub(r"(?<![=\"'>/])(https://[^\s<>\"']*[^\s<>\"'.,;:!?)])", r'<a href="\1">\1</a>', corps)
    titre = next((re.sub(r"\*\*|`", "", ligne[2:]).strip() for ligne in md.split("\n") if ligne.startswith("# ")), nom)
    pdf = telechargements / f"{nom}.pdf"
    if pdf.exists() and "</h1>" in corps:
        bouton = f'<div class="actions">{_bouton(f"telechargements/{nom}.pdf", "Le texte en PDF", f"PDF, {_taille(pdf)}", accent=True)}</div>'
        corps = corps.replace("</h1>", "</h1>" + bouton, 1)
    return _page(f"{titre} · {gabarit.MARQUE}", titre, f'<article class="texte">{corps}</article>', actif=nom, lien_outil=lien_outil,
                 textes_presents=textes_presents)


def verifier(dest: Path) -> list[str]:
    """Contrôles du site écrit : `noindex` sur chaque page, aucun script, chaque lien interne mène à un fichier, chaque ancre existe."""
    racine = dest.resolve()
    pages = sorted(racine.rglob("*.html"))
    ids = {p: set(re.findall(r'\bid="([^"]+)"', p.read_text(encoding="utf-8"))) for p in pages}
    problemes = []
    for p in pages:
        texte, rel = p.read_text(encoding="utf-8"), p.relative_to(racine)
        if NOINDEX not in texte:
            problemes.append(f"{rel} : pas de noindex")
        if re.search(r"<script\b", texte, re.IGNORECASE):
            problemes.append(f"{rel} : script")
        for lien in (html.unescape(x) for x in re.findall(r'(?:href|src)="([^"]*)"', texte)):
            if re.match(r"^(?:https?:|mailto:)", lien):
                continue
            chemin, _, ancre = lien.partition("#")
            cible = (p.parent / chemin).resolve() if chemin else p
            if not cible.is_file() or racine not in cible.parents:
                problemes.append(f"{rel} : lien cassé {lien}")
            elif ancre and cible.suffix == ".html" and ancre not in ids.get(cible, set()):
                problemes.append(f"{rel} : ancre absente {lien}")
    for nom in ("vercel.json", "style.css"):
        if not (racine / nom).is_file():
            problemes.append(f"{nom} absent")
    return problemes


def construire(dest: Path, sorties: Path, lien_outil: str = "", ordre: list[str] | None = None) -> dict[str, Any]:
    """Écrit le site dans `dest` depuis les fiches et les livrables de `sorties`, puis le contrôle.

    `dest` est vidé d'abord. Un dossier qui n'est ni vide ni une vitrine précédente est refusé."""
    fiches = charger_fiches(sorties, ordre)
    if ordre:
        fiches.sort(key=lambda f: ordre.index(f["societe"]))
    if not fiches:
        raise ValueError(f"aucune fiche dans {sorties / 'societes'}")
    if dest.exists() and any(dest.iterdir()):
        if not ((dest / "vercel.json").is_file() and (dest / "style.css").is_file()):
            raise ValueError(f"{dest} n'est pas vide et ne ressemble pas à une vitrine précédente : rien n'est effacé")
        shutil.rmtree(dest)
    (dest / "societes").mkdir(parents=True)
    shutil.copytree(POLICES, dest / "polices")
    (dest / "style.css").write_text(CSS, encoding="utf-8")
    (dest / "vercel.json").write_text(json.dumps(VERCEL, indent=1) + "\n", encoding="utf-8")
    telechargements = dest / "telechargements"
    telechargements.mkdir()
    for nom in TELECHARGEMENTS:
        if (sorties / "livrables" / nom).is_file():
            shutil.copy2(sorties / "livrables" / nom, telechargements / nom)
    # Le lien « page N » ne vaut que si le PDF a bien une page par brief, dans l'ordre des fiches.
    pdf = telechargements / "briefs.pdf"
    page_pdf = pdf.is_file() and len(PdfReader(str(pdf)).pages) == len(fiches)

    jugements = {x: audit.verdicts(sorties, x) for x in audit.TIRAGES}
    par_cellule = {k: v for x in audit.TIRAGES for k, v in jugements[x].items()}  # la relance remplace le premier jugement
    # Un texte absent des livrables n'a ni page, ni entrée au menu, ni carte à l'accueil.
    presents = tuple((nom, libelle) for nom, libelle in TEXTES if (sorties / "livrables" / f"{nom}.md").is_file())
    (dest / "index.html").write_text(_accueil(fiches, telechargements, jugements, lien_outil, presents), encoding="utf-8")
    for numero, f in enumerate(fiches, start=1):
        (dest / "societes" / f"{slug(f['societe'])}.html").write_text(
            _page_societe(f, numero, fiches, telechargements, page_pdf, par_cellule, lien_outil, presents), encoding="utf-8")
    for nom, _ in presents:
        md = (sorties / "livrables" / f"{nom}.md").read_text(encoding="utf-8")
        (dest / f"{nom}.html").write_text(_page_texte(nom, md, telechargements, lien_outil, presents), encoding="utf-8")
    pages = sorted(dest.rglob("*.html"))
    return {"dossier": str(dest), "pages": len(pages), "fichiers": sum(1 for p in dest.rglob("*") if p.is_file()),
            "page_par_brief": page_pdf, "problemes": verifier(dest)}


CSS = """/* La vitrine : couleurs émail et cobalt, titres en Fraunces, texte en Figtree. Le cobalt porte une seule chose par page. */
@font-face { font-family: "Fraunces"; font-weight: 400; font-display: swap; src: url("polices/Fraunces144ptSuperSoft-Regular.ttf") format("truetype"); }
@font-face { font-family: "Figtree"; font-weight: 400; font-display: swap; src: url("polices/Figtree-Regular.ttf") format("truetype"); }
@font-face { font-family: "Figtree"; font-weight: 500; font-display: swap; src: url("polices/Figtree-Medium.ttf") format("truetype"); }
@font-face { font-family: "Figtree"; font-weight: 600; font-display: swap; src: url("polices/Figtree-SemiBold.ttf") format("truetype"); }

:root {
  color-scheme: light dark;
  --fond: #F4F0E6; --surface: #ECE6D8; --surface-2: #F4F0E6;
  --texte: #17181C; --texte-2: #5B5A55; --filet: #D9D2C1; --trait-2: #C9C1AE; --contour: #847F75;
  --accent: #1C3D8C; --sur-accent: #F7F3EA; --alerte: #963020;
  --r-carte: 28px; --r-petit: 14px;
  --titre: Fraunces, Georgia, serif; --corps: Figtree, system-ui, -apple-system, "Segoe UI", sans-serif;
  --mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
@media (prefers-color-scheme: dark) {
  :root {
    --fond: #0E1220; --surface: #161B2C; --surface-2: #1F2538;
    --texte: #EDE7DA; --texte-2: #A8A294; --filet: #2B3247; --trait-2: #3B4360; --contour: #6B7493;
    --accent: #9DB3F0; --sur-accent: #0E1220; --alerte: #E3A08E;
  }
}

* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body { margin: 0; background: var(--fond); color: var(--texte); font: 400 17px/1.55 var(--corps);
  font-feature-settings: "kern" 1; -webkit-font-smoothing: antialiased; overflow-wrap: break-word; }
.cadre { max-width: 70rem; margin: 0 auto; padding: 0 2rem; }
h1, h2, h3, .marque, .titre, .chiffre .n, .etape .n, .sommaire .n {
  font-family: var(--titre); font-weight: 400; font-variation-settings: "opsz" 144, "SOFT" 100; letter-spacing: -0.012em; }
h1 { font-size: clamp(2.1rem, 5vw, 3.3rem); line-height: 1.08; margin: .3rem 0 0; max-width: 20em; text-wrap: balance; }
.insecable { white-space: nowrap; }
h2 { font-size: clamp(1.5rem, 3vw, 1.95rem); line-height: 1.18; margin: 0 0 .9rem; text-wrap: balance; }
h2.suite { margin-top: 2.2rem; }
h3 { font-size: 1.3rem; line-height: 1.25; margin: 1.9rem 0 .4rem; }
p { margin: 0 0 .9rem; max-width: 44em; }
a { color: inherit; text-decoration: underline; text-decoration-color: var(--contour); text-decoration-thickness: 1px; text-underline-offset: .18em; }
a:hover { text-decoration-color: var(--texte); }
:focus-visible { outline: 2px solid var(--texte); outline-offset: 3px; border-radius: 4px; }
.leg, .meta { font-weight: 500; color: var(--texte-2); font-size: .9rem; line-height: 1.45; }

.bandeau { background: var(--surface); border-bottom: 1px solid var(--filet); color: var(--texte-2); font-weight: 500; font-size: .85rem; }
.bandeau .cadre { padding-top: .5rem; padding-bottom: .5rem; }
.entete .cadre { display: flex; flex-wrap: wrap; align-items: baseline; justify-content: space-between; gap: .5rem 2rem;
  padding-top: 1.3rem; padding-bottom: 1.3rem; }
.marque { font-size: 1.5rem; text-decoration: none; }
.nav { display: flex; flex-wrap: wrap; gap: .3rem 1.4rem; font-weight: 500; font-size: .95rem; }
.nav a { color: var(--texte-2); text-decoration: none; }
.nav a:hover, .nav a[aria-current] { color: var(--texte); text-decoration: underline; text-decoration-color: var(--texte); }

main section { padding: 2.6rem 0; border-top: 1px solid var(--filet); }
main section.ouverture { border-top: 0; padding-top: 1.4rem; }
.chapo { font-size: 1.22rem; line-height: 1.5; max-width: 36em; margin-top: 1.2rem; }
.ouverture .meta { margin-top: .6rem; }
.actions { display: flex; flex-wrap: wrap; gap: .6rem; margin-top: 1.5rem; }
.bouton { display: inline-flex; align-items: center; gap: .55em; min-height: 2.75rem; padding: .5rem 1.05rem; border-radius: var(--r-petit);
  border: 1.5px solid var(--texte); color: var(--texte); text-decoration: none; font-weight: 600; font-size: .95rem; line-height: 1.2; }
.bouton:hover { background: var(--surface); }
.bouton .poids { font-weight: 500; color: var(--texte-2); }
.bouton.accent { background: var(--accent); border-color: var(--accent); color: var(--sur-accent); }
.bouton.accent .poids { color: inherit; opacity: .82; }
.bouton.accent:hover { background: var(--accent); text-decoration: underline; }

.chiffres { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 1rem; }
.chiffre { background: var(--surface); border-radius: var(--r-carte); padding: 1.3rem 1.4rem 1.2rem; display: flex; flex-direction: column; }
.chiffre p { margin: 0; }
.chiffre .n { font-size: 2.75rem; line-height: 1; letter-spacing: -.02em; font-variant-numeric: lining-nums; }
.chiffre .n small { font-family: var(--corps); font-size: .36em; letter-spacing: 0; margin-left: .2em; }
.chiffre .l { margin-top: .55rem; line-height: 1.42; }
.chiffre .src { margin-top: auto; padding-top: .8rem; font-weight: 500; font-size: .8rem; color: var(--texte-2); }

.barre { display: flex; height: 2.4rem; border-radius: var(--r-petit); overflow: hidden; margin: 1.2rem 0 1.4rem; gap: 2px; }
.barre span { display: block; min-width: 4px; }
.barre .n-confirme { background: var(--texte); }
.barre .n-probable { background: var(--contour); }
.barre .n-absence { background: var(--texte-2); }
.barre .n-contradiction { background: var(--alerte); }
.barre .n-non-trouve { background: var(--trait-2); }
.niveaux { margin: 0; display: grid; grid-template-columns: repeat(auto-fit, minmax(15rem, 1fr)); gap: 1rem 1.6rem; }
.niveaux dt { display: flex; flex-wrap: wrap; align-items: center; gap: .5rem; }
.niveaux .compte { font-weight: 600; font-size: .92rem; }
.niveaux dd { margin: .4rem 0 0; font-size: .92rem; line-height: 1.45; color: var(--texte-2); }

.pastille { display: inline-flex; align-items: center; gap: .45em; height: 1.75em; padding: 0 .75em 0 .62em; border: 1.5px solid currentColor;
  border-radius: 99em; font-weight: 500; font-size: .84rem; line-height: 1; white-space: nowrap; }
.pastille::before { content: ""; width: .5em; height: .5em; border-radius: 50%; background: currentColor; }
.n-confirme { color: var(--texte); }
.n-probable { color: var(--texte); }
.pastille.n-probable::before { background: transparent; box-shadow: inset 0 0 0 1.5px currentColor; }
.n-absence { color: var(--texte-2); }
.n-contradiction { color: var(--alerte); }
.pastille.n-non-trouve { color: var(--texte-2); border-color: var(--trait-2); }
.pastille.n-non-trouve::before { display: none; }
.etiquette { display: inline-flex; align-items: center; height: 1.7em; padding: 0 .62em; border-radius: .38em; background: var(--surface);
  color: var(--texte); font-family: var(--corps); font-size: .82rem; font-weight: 500; letter-spacing: 0; line-height: 1;
  white-space: nowrap; vertical-align: middle; }
h2 .etiquette { margin-left: .5rem; position: relative; top: -.15em; }

.etapes { list-style: none; margin: 1.2rem 0 0; padding: 0; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: .9rem; }
.etape { background: var(--surface); border-radius: var(--r-carte); padding: 1.2rem 1.3rem 1.25rem; }
.etape .tete { display: flex; justify-content: space-between; align-items: center; margin-bottom: .6rem; }
.etape .n { font-size: 2rem; line-height: 1; }
.etape .etiquette { background: var(--surface-2); }
.etape b { display: block; font-weight: 600; margin-bottom: .25rem; }
.etape p { margin: 0; font-size: .95rem; line-height: 1.45; }

.sommaire { list-style: none; margin: 1.2rem 0 0; padding: 0; border-bottom: 1px solid var(--filet); }
.sommaire li { border-top: 1px solid var(--filet); }
.sommaire a { display: grid; grid-template-columns: 2.6rem minmax(0, 1fr) auto; column-gap: 1rem; align-items: baseline; padding: .95rem 0;
  text-decoration: none; }
.sommaire a:hover .nom { text-decoration: underline; text-decoration-color: var(--texte); text-underline-offset: .18em; }
.sommaire .n { font-size: 1.55rem; line-height: 1; color: var(--texte-2); font-variant-numeric: lining-nums; }
.sommaire .nom { display: block; font-weight: 600; font-size: 1.08rem; }
.sommaire .meta { display: block; font-size: .88rem; margin-top: .1rem; }
.sommaire .niv { font-size: .88rem; color: var(--texte-2); font-weight: 500; text-align: right; }

.cartes { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1rem; }
.carte { display: block; background: var(--surface); border-radius: var(--r-carte); padding: 1.4rem 1.5rem; text-decoration: none; }
.carte .titre { display: block; font-size: 1.4rem; line-height: 1.22; }
.carte .l { display: block; margin-top: .6rem; color: var(--texte-2); line-height: 1.45; }
.carte:hover .titre { text-decoration: underline; text-decoration-color: var(--texte); text-underline-offset: .18em; }

table { width: 100%; border-collapse: collapse; font-size: .95rem; }
th { text-align: left; font-weight: 500; color: var(--texte-2); font-size: .84rem; line-height: 1.3; padding: 0 1rem .6rem 0;
  border-bottom: 1.5px solid var(--texte); vertical-align: bottom; }
td { padding: .75rem 1rem .75rem 0; border-bottom: 1px solid var(--filet); vertical-align: top; line-height: 1.45; }
th:last-child, td:last-child { padding-right: 0; }
.brief td.champ { font-weight: 600; width: 13rem; }
.brief .niveau { text-align: right; width: 9rem; }
.renvoi { color: var(--texte-2); text-decoration: none; font-variant-numeric: tabular-nums; white-space: nowrap; }
.renvoi:hover { color: var(--texte); text-decoration: underline; }
.defile { overflow-x: auto; -webkit-overflow-scrolling: touch; margin: .8rem 0 1.2rem; }
.defile table { font-size: .86rem; min-width: 34rem; }
.defile td, .defile th { padding-top: .5rem; padding-bottom: .5rem; }

.questions { padding-left: 1.4rem; margin: 0; max-width: 44em; }
.questions li { margin: 0 0 .6rem; padding-left: .2rem; }
.contact { margin-top: 1.2rem; color: var(--texte-2); }
.sources { padding-left: 1.6rem; margin: 0; }
.sources li { margin: 0 0 .55rem; padding-left: .2rem; }
.sources li:target { background: var(--surface); border-radius: 6px; }
.sources .adresse { display: block; font-size: .8rem; color: var(--texte-2); overflow-wrap: anywhere; }

.trouvailles { list-style: none; margin: 0; padding: 0; border-bottom: 1px solid var(--filet); }
.trouvaille { border-top: 1px solid var(--filet); padding: .9rem 0; }
.trouvaille .haut { display: flex; justify-content: space-between; align-items: flex-start; gap: .8rem 1.2rem; }
.trouvaille .valeur { font-weight: 600; }
.trouvaille .src { margin: .25rem 0 0; font-size: .9rem; color: var(--texte-2); overflow-wrap: anywhere; }
details { margin-top: .55rem; }
summary { cursor: pointer; font-weight: 500; font-size: .9rem; color: var(--texte-2); width: max-content; }
summary:hover { color: var(--texte); }
blockquote { margin: .5rem 0 0; padding: .75rem 1rem; background: var(--surface); border-radius: var(--r-petit); font-size: .95rem; max-width: 46em; }
.traduction { margin: .45rem 0 0; font-size: .9rem; color: var(--texte-2); }
.audit { margin: .6rem 0 0; font-size: .9rem; line-height: 1.45; }
.audit b { font-weight: 600; }

.voisines { display: flex; justify-content: space-between; gap: 1rem; padding: 1.6rem 0 .4rem; border-top: 1px solid var(--filet); font-weight: 500; }
.voisines .apres { margin-left: auto; text-align: right; }

.texte { padding: 1.4rem 0 1rem; }
.texte h2 { margin: 2.6rem 0 .8rem; }
.texte ul, .texte ol { padding-left: 1.3rem; max-width: 46em; margin: 0 0 1rem; }
.texte li { margin: 0 0 .55rem; }
.texte pre { background: var(--surface); border-radius: var(--r-petit); padding: 1rem 1.2rem; font: .8rem/1.55 var(--mono);
  white-space: pre-wrap; overflow-wrap: anywhere; max-width: 100%; }
.texte code { font: .86em var(--mono); background: var(--surface); padding: .05em .3em; border-radius: .3em; overflow-wrap: anywhere; }
.texte .actions { margin: 1.2rem 0 1.6rem; }

.pied { border-top: 1px solid var(--filet); margin-top: 2.4rem; padding: 1.6rem 0 2.6rem; font-size: .88rem; color: var(--texte-2); }

@media (max-width: 860px) {
  .chiffres, .etapes { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .cartes { grid-template-columns: 1fr; }
}
@media (max-width: 640px) {
  body { font-size: 16px; }
  .chapo { font-size: 1.1rem; }
  .cadre { padding: 0 16px; }
  main section { padding: 2rem 0; }
  .chiffres, .etapes { grid-template-columns: 1fr; }
  .sommaire a { grid-template-columns: 2rem minmax(0, 1fr); }
  .sommaire .niv { grid-column: 2; text-align: left; margin-top: .35rem; }
  table.brief, .brief tbody, .brief tr, .brief td { display: block; width: auto; }
  .brief thead { display: none; }
  .brief tr { border-top: 1px solid var(--filet); padding: .7rem 0; }
  .brief td { border: 0; padding: 0; }
  .brief td.champ { width: auto; font-size: .9rem; color: var(--texte-2); font-weight: 500; }
  .brief td.valeur { margin: .15rem 0 .45rem; }
  .brief td.niveau { text-align: left; width: auto; }
  .brief { border-bottom: 1px solid var(--filet); }
  .trouvaille .haut { flex-direction: column; }
}
"""
