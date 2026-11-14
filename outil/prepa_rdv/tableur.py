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


def _valeurs(synthese: dict) -> tuple[str, str, str]:
    """Valeur, niveau et identifiants de trouvailles d'un champ, pour la ligne de la société."""
    vs = synthese["valeurs"]
    if not vs:
        return "", synthese["niveau"], ""
    texte = " ; ".join((v["valeur"] if v["valeur"] != "autre" else (v["precision"] or "autre"))
                       + (" (absence déclarée)" if v["statut"] == "absence_declaree" else "") for v in vs[:3])
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


def echantillon_audit(fiches: list[dict], n: int = 36, graine: int = 2026) -> list[dict[str, Any]]:
    """Cellules tirées au sort (graine fixe) parmi les valeurs trouvées : société, champ, valeur, citation, lien."""
    cellules = []
    for f in fiches:
        par_id = {t["id"]: t for t in f["trouvailles"]}
        for champ in CHAMPS_CARTO:
            for v in f["synthese"][champ.value]["valeurs"][:1]:
                t = par_id.get(v["ids"][0]) if v["ids"] else None
                if t:
                    cellules.append({"societe": f["societe"], "champ": LIBELLES_CHAMP[champ], "valeur": v["valeur"] if v["valeur"] != "autre" else (v["precision"] or "autre"),
                                     "niveau": v["niveau"], "citation": t["citation"], "url": t["url"], "id": t["id"]})
    cellules.sort(key=lambda c: (c["societe"], c["champ"]))
    return random.Random(graine).sample(cellules, min(n, len(cellules)))


def ecrire_cartographie(fiches: list[dict], chemin: Path, lien_outil: str = "", audit: list[dict] | None = None) -> Path:
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
            valeur, niveau, ids = _valeurs(f["synthese"][c.value])
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

    au = wb.create_sheet("Audit")
    au.append(["Société", "Champ", "Valeur", "Niveau", "Citation", "Lien", "Juste ou faux (à remplir)", "Identifiant"])
    for a in (audit if audit is not None else echantillon_audit(fiches)):
        au.append([a["societe"], a["champ"], a["valeur"], a["niveau"], a["citation"], None, "", a["id"]])
        _lien(au, au.cell(row=au.max_row, column=6), a["url"])
    _style(au, [18, 22, 28, 12, 70, 40, 18, 22])
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
