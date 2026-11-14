"""Les deux tableurs : `cartographie.xlsx` (une ligne par société) et `trouvailles.xlsx` (une ligne par trouvaille).

Aucune cellule n'est corrigée à la main : le contrôle d'empreinte compare le fichier livré à la sortie de l'outil.
"""
from __future__ import annotations

import hashlib
import random
from pathlib import Path
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from . import affichage
from .schema import CHAMPS_BRIEF, LIBELLES_CHAMP, Champ, Niveau

CHAMPS_CARTO = (*CHAMPS_BRIEF, Champ.SIGNAL)
LEGENDE = [
    ("confirmé", "Citation vérifiée dans une source de la société (24 mois) ou d'un tiers qui la nomme (36 mois), société nommée."),
    ("probable", "Citation vérifiée, mais source hors fenêtre, sans date, de presse, d'offre d'emploi, ou société nommée à distance."),
    ("non trouvé", "Aucune citation vérifiée après le plan de requêtes complet. Ce n'est pas une absence prouvée."),
    ("absence déclarée", "Un document de la société dit qu'elle n'a pas le produit."),
    ("contradiction", "Deux valeurs incompatibles au même niveau : les deux sont affichées."),
]
EN_TETE = PatternFill("solid", fgColor="1F2937")
BLANC = Font(bold=True, color="FFFFFF")


def valeur_cellule(v: dict, t: dict | None, entite: dict) -> str:
    """La valeur telle que la cellule la montre : le nom, puis ce qu'il faut savoir pour ne pas dire plus que la page (D21)."""
    base = v["valeur"] if v["valeur"] != "autre" else (v["precision"] or "autre")
    return base + (" (absence déclarée)" if v.get("statut") == "absence_declaree" else "") + affichage.marques(t, entite)


def _valeurs(synthese: dict, par_id: dict | None = None, entite: dict | None = None) -> tuple[str, str, str]:
    """Valeur, niveau et identifiants de trouvailles d'un champ, pour la ligne de la société."""
    vs = synthese["valeurs"]
    if not vs:
        return "", synthese["niveau"], ""
    par_id, entite = par_id or {}, entite or {}
    texte = " ; ".join(valeur_cellule(v, par_id.get(v["ids"][0]) if v["ids"] else None, entite) for v in vs[:3])
    return texte, synthese["niveau"], ",".join(v["ids"][0] for v in vs[:3] if v["ids"])


def _style(ws, largeurs: list[int]) -> None:
    for i, l in enumerate(largeurs, start=1):
        ws.column_dimensions[get_column_letter(i)].width = l
    for c in ws[1]:
        c.fill, c.font = EN_TETE, BLANC
        c.alignment = Alignment(wrap_text=True, vertical="center")
    ws.freeze_panes = "B2"
    ws.auto_filter.ref = ws.dimensions


def _lien(ws, cellule, url: str | None) -> None:
    if url:
        cellule.value, cellule.hyperlink, cellule.font = url, url, Font(color="1D4ED8", underline="single")


def echantillon_audit(fiches: list[dict], n: int = 36, graine: int = 2026, exclure: set[str] | None = None) -> list[dict[str, Any]]:
    """Cellules tirées au sort (graine fixe) parmi les valeurs trouvées : société, champ, valeur, citation, lien."""
    cellules = [c for c in cellules_audit(fiches) if c["id"] not in (exclure or set())]
    return random.Random(graine).sample(cellules, min(n, len(cellules)))


def cellules_audit(fiches: list[dict]) -> list[dict[str, Any]]:
    """Toutes les cellules qu'un audit peut tirer : la première valeur de chaque champ de la cartographie, avec sa trouvaille."""
    cellules = []
    for f in fiches:
        par_id = {t["id"]: t for t in f["trouvailles"]}
        for champ in CHAMPS_CARTO:
            for v in f["synthese"][champ.value]["valeurs"][:1]:
                t = par_id.get(v["ids"][0]) if v["ids"] else None
                if t:
                    cellules.append({"societe": f["societe"], "champ": LIBELLES_CHAMP[champ], "valeur": valeur_cellule(v, t, f.get("entite") or {}),
                                     "niveau": v["niveau"], "citation": t["citation"], "url": t["url"], "id": t["id"]})
    cellules.sort(key=lambda c: (c["societe"], c["champ"]))
    return cellules


TEINTES_VERDICT = {"juste": "DCFCE7", "partiel": "FEF3C7", "faux": "FEE2E2", "invérifiable": "E5E7EB"}


def ecrire_audit(au, cellules: list[dict], verdicts: dict[str, dict] | None, auditeur: str = "", relance: dict[str, dict] | None = None) -> None:
    """Feuille « Audit » : les cellules tirées au sort et, une fois l'audit reçu, le verdict de l'agent auditeur."""
    if not verdicts:
        au.append(["Société", "Champ", "Valeur", "Niveau", "Citation", "Lien", "Juste ou faux (à remplir)", "Identifiant"])
        for a in cellules:
            au.append([a["societe"], a["champ"], a["valeur"], a["niveau"], a["citation"], None, "", a["id"]])
            _lien(au, au.cell(row=au.max_row, column=6), a["url"])
        _style(au, [18, 22, 28, 12, 70, 40, 18, 22])
        return
    relance = relance or {}
    en_tete = ["Société", "Champ", "Valeur", "Niveau", "Citation", "Lien", "Verdict de l'auditeur", "Écart", "Raison de l'auditeur",
               "Passage relu par l'auditeur", "Identifiant"]
    if relance:
        en_tete[-1:-1] = ["Après correction : valeur rejugée", "Après correction : verdict", "Après correction : raison"]
    au.append(en_tete)
    compte = {v: 0 for v in TEINTES_VERDICT}
    for a in cellules:
        j = verdicts.get(a["id"]) or {}
        ligne = [a["societe"], a["champ"], a["valeur"], a["niveau"], a["citation"], None, j.get("verdict", ""), j.get("ecart"),
                 j.get("raison"), j.get("passage"), a["id"]]
        if relance:
            rj = relance.get(a["id"]) or {}
            ligne[-1:-1] = [rj.get("valeur"), rj.get("verdict"), rj.get("raison")]
        au.append(ligne)
        r = au.max_row
        _lien(au, au.cell(row=r, column=6), a["url"])
        for c in au[r]:
            c.alignment = Alignment(wrap_text=True, vertical="top")
        if j.get("verdict") in TEINTES_VERDICT:
            compte[j["verdict"]] += 1
            au.cell(row=r, column=7).fill = PatternFill("solid", fgColor=TEINTES_VERDICT[j["verdict"]])
        if relance and (relance.get(a["id"]) or {}).get("verdict") in TEINTES_VERDICT:
            au.cell(row=r, column=13).fill = PatternFill("solid", fgColor=TEINTES_VERDICT[relance[a["id"]]["verdict"]])
    _style(au, [18, 22, 28, 12, 60, 40, 14, 20, 50, 40] + ([36, 14, 50] if relance else []) + [22])
    qui = f"un sous-agent auditeur ({auditeur})" if auditeur else "un sous-agent auditeur"
    au.cell(row=au.max_row + 2, column=1, value=(
        f"Verdicts écrits par {qui}, qui n'a pas produit ces cellules et ne connaissait pas leur niveau. Il a ouvert chaque lien "
        "et dit si la page soutient la valeur. C'est un modèle qui en juge un autre, pas une relecture par une personne."))
    au.cell(row=au.max_row + 1, column=1, value="Justes : {juste} ; partielles : {partiel} ; fausses : {faux} ; invérifiables : {invérifiable}."
            .format(**compte))


def ecrire_cartographie(fiches: list[dict], chemin: Path, lien_outil: str = "", audit: list[dict] | None = None,
                        verdicts: dict[str, dict] | None = None, auditeur: str = "", relance: dict[str, dict] | None = None,
                        second: dict[str, dict] | None = None) -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "Cartographie"
    en_tete = ["Société", "Pays", "Statut", "ISIN", "LEI", "Site"]
    for c in CHAMPS_CARTO:
        en_tete += [f"{LIBELLES_CHAMP[c]} : valeur", f"{LIBELLES_CHAMP[c]} : source", f"{LIBELLES_CHAMP[c]} : niveau"]
    en_tete += ["Date de la fiche", "Jetons traités", "Coût estimé ($)", "Durée (s)", "Version"]
    ws.append(en_tete)
    for f in fiches:
        e, par_id = f["entite"], {t["id"]: t for t in f["trouvailles"]}
        ligne = [f["societe"], e.get("pays"), e.get("statut"), ", ".join(e.get("isin") or []), e.get("lei"), e.get("site")]
        urls, toutes = [], []
        for c in CHAMPS_CARTO:
            valeur, niveau, ids = _valeurs(f["synthese"][c.value], par_id, e)
            sources = list(dict.fromkeys(par_id[i]["url"] for i in ids.split(",") if i in par_id))
            urls.append(sources[0] if sources else None)
            toutes.append("\n".join(sources))
            ligne += [valeur, "\n".join(sources), niveau]
        j = f.get("jetons") or {}
        ligne += [f["date_fiche"], j.get("traites"), j.get("cout_estime_usd"), round(j.get("duree_s") or f.get("duree_s") or 0), f["version_outil"]]
        ws.append(ligne)
        r = ws.max_row
        for k, url in enumerate(urls):
            cellule = ws.cell(row=r, column=7 + k * 3 + 1)
            _lien(ws, cellule, url)
            cellule.value = toutes[k] or None  # toutes les sources distinctes, la première est le lien
        for c in ws[r]:
            c.alignment = Alignment(wrap_text=True, vertical="top")
    _style(ws, [18, 12, 14, 16, 22, 28] + [30, 36, 12] * len(CHAMPS_CARTO) + [12, 14, 12, 10, 10])
    if lien_outil:
        ws.cell(row=ws.max_row + 2, column=1, value="Outil").font = Font(bold=True)
        _lien(ws, ws.cell(row=ws.max_row, column=2), lien_outil)

    lg = wb.create_sheet("Légende")
    lg.append(["Niveau", "Définition"])
    for n, d in LEGENDE:
        lg.append([n, d])
    _style(lg, [20, 110])
    lg.freeze_panes = "A2"

    ecrire_audit(wb.create_sheet("Audit"), audit if audit is not None else echantillon_audit(fiches), verdicts, auditeur, relance)
    if second:
        niveaux = {c["id"]: c["niveau"] for c in cellules_audit(fiches)}
        ws2 = wb.create_sheet("Audit, second tirage")
        ecrire_audit(ws2, [{**j, "niveau": niveaux.get(i, "")} for i, j in second.items()], second, auditeur)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    wb.save(chemin)
    return chemin


COLONNES_TROUVAILLES = ["id", "societe", "champ", "valeur", "valeur_normalisee", "precision", "statut_valeur", "niveau", "citation",
                        "citation_langue", "traduction_fr", "url", "entite_nommee", "type_source_modele", "type_source_code",
                        "date_source_modele", "date_page", "date_retenue", "age_mois", "dans_fenetre", "citation_trouvee",
                        "score_similarite", "adresse_ok", "statut_http", "entite", "erreurs", "date_lecture", "empreinte_source",
                        "modele", "version_outil", "empreinte_prompt", "mode_verification", "citation_du_modele", "score_avant_reparation"]


def ecrire_trouvailles(fiches: list[dict], chemin: Path) -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "Trouvailles"
    ws.append(COLONNES_TROUVAILLES)
    for f in fiches:
        for t in f["trouvailles"]:
            v = t["verifs"]
            ws.append([t["id"], t["societe"], t["champ"], t["valeur"], t["valeur_normalisee"], t["precision"], t["statut_valeur"],
                       t["niveau"], t["citation"], t["citation_langue"], t["traduction_fr"], None, t["entite_nommee"], t["type_source"],
                       v["type_source_code"], t["date_source"], v["date_page"], v["date_retenue"], v["age_mois"], v["dans_fenetre"],
                       v["citation_trouvee"], v["score_similarite"], v["adresse_ok"], v["statut_http"], v["entite"],
                       " | ".join(v["erreurs"]), t["date_lecture"], t["empreinte_source"], t["modele"], t["version_outil"], t["empreinte_prompt"],
                       v.get("mode_verification", "code"), v.get("citation_du_modele"), v.get("score_avant_reparation")])
            _lien(ws, ws.cell(row=ws.max_row, column=12), t["url"])
    _style(ws, [22, 16, 18, 24, 24, 20, 14, 12, 70, 8, 40, 40, 20, 8, 8, 14, 12, 12, 8, 8, 8, 8, 8, 8, 10, 40, 26, 20, 18, 8, 14, 16, 50, 10])
    chemin.parent.mkdir(parents=True, exist_ok=True)
    wb.save(chemin)
    return chemin


def empreinte_fichier(chemin: Path) -> str:
    return hashlib.sha256(chemin.read_bytes()).hexdigest()
