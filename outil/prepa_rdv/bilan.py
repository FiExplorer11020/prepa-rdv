"""Bilan d'un lot de fiches : niveaux obtenus, motifs de rejet, part hors fenêtre, jetons.

Sert à lire la sonde (cahier des charges, section 6.4 : faut-il des fenêtres par champ ? la lecture par le code
bute-t-elle sur trop de sites ?) et à nourrir le journal d'erreurs.
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Any

MOTIFS = (
    ("robots", r"robots\.txt"),
    ("refus HTTP", r"HTTP (401|403|429)"),
    ("page introuvable", r"HTTP (404|410)|réseau"),
    ("citation introuvable", r"citation introuvable"),
    ("citation trop longue", r"citation de \d+ mots"),
    ("page vide", r"page vide"),
)


def motif(erreurs: list[str], entite: str) -> str:
    texte = " | ".join(erreurs)
    for nom, motif_re in MOTIFS:
        if re.search(motif_re, texte):
            return nom
    return "société non nommée" if entite == "absente" else "autre"


def bilan_societe(f: dict[str, Any]) -> dict[str, Any]:
    t = f["trouvailles"]
    niveaux = Counter(x["niveau"] for x in t)
    rejets = Counter(motif(x["verifs"]["erreurs"], x["verifs"]["entite"]) for x in t if x["niveau"] == "non trouvé")
    gardees = [x for x in t if x["niveau"] != "non trouvé"]
    v = lambda x: x["verifs"]  # noqa: E731
    return {
        "societe": f["societe"], "trouvailles": len(t), "niveaux": dict(niveaux), "rejets": dict(rejets),
        "gardees": len(gardees),
        "hors_fenetre": sum(1 for x in gardees if v(x).get("dans_fenetre") is False),
        "sans_date": sum(1 for x in gardees if v(x).get("sans_date")),
        "type_corrige": sum(1 for x in t if v(x).get("type_corrige")),
        "pages_vivantes": sum(1 for x in t if v(x).get("page_vivante")),
        "pages_lues": len({x["url"] for x in t if v(x).get("adresse_ok") and v(x).get("mode_verification", "code") != "seconde_lecture"}),
        "pages_refusees": len({x["url"] for x in t if not v(x).get("adresse_ok") or v(x).get("refus_du_code")}),
        # Citations du modèle sur les pages que le code a pu lire (hors constats d'identité et hors seconde lecture)
        "lisibles": sum(1 for x in t if v(x).get("adresse_ok") and v(x).get("mode_verification", "code") != "seconde_lecture" and x["champ"] != "identite"),
        "mot_pour_mot": sum(1 for x in t if v(x).get("adresse_ok") and v(x).get("mode_verification", "code") == "code" and v(x).get("citation_trouvee")
                            and x["champ"] != "identite"),
        "relues": sum(1 for x in t if v(x).get("mode_verification") == "seconde_lecture"),
        "relues_confirmees": sum(1 for x in t if v(x).get("mode_verification") == "seconde_lecture" and x["niveau"] != "non trouvé"),
        "reparees": sum(1 for x in t if v(x).get("mode_verification") == "citation_remplacee"),
        "lues_rendues": len({x["url"] for x in t if v(x).get("lu_via") == "jina"}),
        "jetons": f.get("jetons", {}), "duree_s": f.get("duree_s"),
    }


def bilan_lot(fiches: list[dict[str, Any]]) -> dict[str, Any]:
    par = [bilan_societe(f) for f in fiches]
    gardees = sum(b["gardees"] for b in par)
    return {
        "societes": par,
        "total": {
            "trouvailles": sum(b["trouvailles"] for b in par), "gardees": gardees,
            "hors_fenetre": sum(b["hors_fenetre"] for b in par), "sans_date": sum(b["sans_date"] for b in par),
            "part_hors_fenetre_ou_sans_date": round((sum(b["hors_fenetre"] + b["sans_date"] for b in par) / gardees), 2) if gardees else None,
            "rejets": dict(sum((Counter(b["rejets"]) for b in par), Counter())),
            "pages_lues": sum(b["pages_lues"] for b in par), "pages_refusees": sum(b["pages_refusees"] for b in par),
            "lisibles": sum(b["lisibles"] for b in par), "mot_pour_mot": sum(b["mot_pour_mot"] for b in par),
            "relues": sum(b["relues"] for b in par), "relues_confirmees": sum(b["relues_confirmees"] for b in par),
            "reparees": sum(b["reparees"] for b in par), "lues_rendues": sum(b["lues_rendues"] for b in par),
            "traites": sum((b["jetons"] or {}).get("traites", 0) for b in par),
            "cout_estime_usd": round(sum((b["jetons"] or {}).get("cout_estime_usd", 0.0) for b in par), 2),
        },
    }


def formater(b: dict[str, Any]) -> str:
    lignes = ["| Société | Trouvailles | Confirmé | Probable | Absence | Rejetées | Hors fenêtre | Sans date | Pages lues | Refusées | Jetons traités | Coût estimé ($) | Durée (s) |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for s in b["societes"]:
        n = s["niveaux"]
        j = s["jetons"] or {}
        lignes.append(f"| {s['societe']} | {s['trouvailles']} | {n.get('confirmé', 0)} | {n.get('probable', 0)} | {n.get('absence déclarée', 0)} | "
                      f"{n.get('non trouvé', 0)} | {s['hors_fenetre']} | {s['sans_date']} | {s['pages_lues']} | {s['pages_refusees']} | "
                      f"{j.get('traites', 0):,} | {j.get('cout_estime_usd', 0):.2f} | {s['duree_s']} |".replace(",", " "))
    t = b["total"]
    lignes += ["", f"Total : {t['trouvailles']} trouvailles, {t['gardees']} gardées, {t['hors_fenetre']} hors fenêtre, {t['sans_date']} sans date "
               f"(part hors fenêtre ou sans date : {t['part_hors_fenetre_ou_sans_date']}). "
               f"Pages lues par le code : {t['pages_lues']}, refusées ou illisibles pour lui : {t['pages_refusees']} "
               f"(dont {t['relues']} lignes relues par un second agent, {t['relues_confirmees']} concordantes). "
               f"Citations réparées par le code : {t['reparees']}. Pages relues rendues par JavaScript : {t['lues_rendues']}. "
               f"Motifs de rejet : {t['rejets'] or 'aucun'}."]
    return "\n".join(lignes)
