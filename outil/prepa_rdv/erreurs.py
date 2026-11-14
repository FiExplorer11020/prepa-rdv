"""Journal d'erreurs (`erreurs.jsonl`, cahier des charges section 9).

Une ligne par erreur : société, champ, ce que l'outil a écrit, ce que dit la source, cause, contrôle qui l'a vue,
changement apporté, relance faite. Le code relève les erreurs que ses contrôles voient ; le changement et la relance
s'ajoutent après coup, par `corriger`. Une erreur sans changement associé n'est pas comptée comme corrigée.

Causes admises : entité, extrapolation, citation reformulée, citation inventée, date, périmètre, source non primaire,
traduction, autre.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rapidfuzz import fuzz

from .jetons import dossier_sorties
from .lecteur import Lecteur
from .verificateur import normaliser_texte

CAUSES = ("entité", "extrapolation", "citation reformulée", "citation inventée", "date", "périmètre",
          "source non primaire", "traduction", "page lue incomplète", "autre")


def chemin() -> Path:
    return dossier_sorties() / "journal" / "erreurs.jsonl"


def lire() -> list[dict[str, Any]]:
    """Lignes du journal, sans les constats d'identité : un nom légal mal cité n'entre dans aucun champ du brief."""
    p = chemin()
    lignes = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()] if p.exists() else []
    return [e for e in lignes if e.get("champ") != "identite"]


def _extrait(citation: str, texte: str, taille: int = 220) -> tuple[float, str]:
    """Passage de la page le plus proche de la citation, avec sa similarité."""
    n, c = normaliser_texte(texte), normaliser_texte(citation)
    if not n or not c:
        return 0.0, ""
    al = fuzz.partial_ratio_alignment(c, n)
    return al.score / 100.0, n[max(0, al.dest_start - 20):al.dest_start + taille]


CHANGEMENT_REPARATION = ("Le code garde le passage de la page le plus proche, qui porte la valeur et la société, à la place de la citation "
                         "du modèle (verificateur.reparer_citation) ; niveau plafonné à « probable »")


def classer(t: dict[str, Any], lecteur: Lecteur | None) -> dict[str, Any] | None:
    """Erreur vue par les contrôles du code pour une trouvaille rejetée ou réparée, ou None si la trouvaille passe."""
    v = t["verifs"]
    if t["champ"] == "identite":
        return None
    if v.get("mode_verification") == "citation_remplacee":
        avant = v.get("score_avant_reparation") or 0.0
        return {"id_trouvaille": t["id"], "societe": t["societe"], "champ": t["champ"], "ecrit": f"{t['valeur']} : « {v['citation_du_modele']} »",
                "url": t["url"], "source_dit": t["citation"], "similarite": round(avant, 3),
                "cause": "citation reformulée" if avant >= 0.6 else "citation inventée",
                "detecteur": "contrôle 1 : citation dans le texte relu", "changement": CHANGEMENT_REPARATION, "relance": None}
    if t["niveau"] != "non trouvé":
        return None
    if v.get("mode_verification") == "seconde_lecture":
        return None  # deux lectures qui ne s'accordent pas : la trouvaille reste écartée, mais ce n'est pas une erreur établie du modèle
    erreurs = " | ".join(v["erreurs"])
    if any(m in erreurs for m in ("robots.txt", "HTTP 401", "HTTP 403", "HTTP 429")):
        return None  # un refus de lecture n'est pas une erreur du modèle : c'est une limite, traitée par la seconde lecture
    source_dit, score = "", v.get("score_similarite", 0.0)
    if "citation introuvable" in erreurs and lecteur is not None:
        page = lecteur.lire(t["url"])
        if page.ok:
            score, source_dit = _extrait(t["citation"], page.texte)
    if "citation introuvable" in erreurs:
        cause, detecteur = ("citation reformulée" if score >= 0.6 else "citation inventée"), "contrôle 1 : citation dans le texte relu"
    elif "mots (limite" in erreurs:
        cause, detecteur = "citation reformulée", "contrôle 1 : longueur de la citation"
    elif "HTTP 404" in erreurs or "HTTP 410" in erreurs or "réseau" in erreurs:
        cause, detecteur = "autre", "contrôle 2 : adresse qui répond"
    elif v["entite"] == "absente":
        cause, detecteur = "entité", "contrôle 3 : société nommée à côté de la citation"
    else:
        cause, detecteur = "autre", "contrôles du code"
    return {"id_trouvaille": t["id"], "societe": t["societe"], "champ": t["champ"], "ecrit": f"{t['valeur']} : « {t['citation']} »",
            "url": t["url"], "source_dit": source_dit or erreurs, "similarite": round(score, 3), "cause": cause, "detecteur": detecteur,
            "changement": None, "relance": None}


def releve(fiches: list[dict[str, Any]], lecteur: Lecteur | None = None) -> list[dict[str, Any]]:
    """Ajoute au journal les erreurs que les contrôles voient et qui n'y sont pas déjà. Renvoie les nouvelles lignes."""
    connues = {(e["id_trouvaille"], e["ecrit"]) for e in lire()}
    nouvelles = []
    for f in fiches:
        for t in f["trouvailles"]:
            e = classer(t, lecteur)
            if e and (e["id_trouvaille"], e["ecrit"]) not in connues:
                if e["changement"]:  # réparée par le code dans ce même passage : la relance est ce passage lui-même
                    e["relance"] = f"même passage ({f['run_id']}) : trouvaille gardée avec le passage de la page, niveau {t['niveau']}"
                e = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "run_id": f["run_id"], **e}
                nouvelles.append(e)
    if nouvelles:
        chemin().parent.mkdir(parents=True, exist_ok=True)
        with chemin().open("a", encoding="utf-8") as fh:
            for e in nouvelles:
                fh.write(json.dumps(e, ensure_ascii=False) + "\n")
    return nouvelles


def corriger(id_trouvaille: str, changement: str, relance: str, cause: str | None = None, source_dit: str | None = None) -> dict[str, Any]:
    """Ajoute au journal (en ajout seul) la correction d'une erreur : ce qui a changé et la relance faite.

    La cause et ce que dit la source se corrigent ici quand l'analyse de la correction montre que la première cause était fausse
    (cas des deux erreurs de la sonde : la page portait la phrase, c'est la lecture directe qui l'avait perdue).
    """
    if cause is not None and cause not in CAUSES:
        raise ValueError(f"Cause inconnue : {cause}. Causes admises : {', '.join(CAUSES)}")
    derniere = next((e for e in reversed(lire()) if e["id_trouvaille"] == id_trouvaille and e.get("changement") is None), None)
    if derniere is None:
        raise KeyError(f"Aucune erreur ouverte pour {id_trouvaille}")
    ligne = {**derniere, "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "changement": changement, "relance": relance}
    if cause is not None:
        ligne["cause"] = cause
    if source_dit is not None:
        ligne["source_dit"] = source_dit
    with chemin().open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(ligne, ensure_ascii=False) + "\n")
    return ligne


def comptes() -> dict[str, int]:
    """Erreurs distinctes et erreurs corrigées (avec changement et relance)."""
    par_cle: dict[tuple, dict] = {}
    for e in lire():
        k = (e["id_trouvaille"], e["ecrit"])
        if k not in par_cle or e.get("changement"):
            par_cle[k] = e
    return {"erreurs": len(par_cle), "corrigees": sum(1 for e in par_cle.values() if e.get("changement") and e.get("relance"))}
