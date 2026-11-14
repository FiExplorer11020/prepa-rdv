"""Registre des jetons du projet.

Chaque appel au modèle de l'outil (essais, sonde, run, audit, démo) ajoute une ligne à
`sorties/journal/jetons.jsonl`. Le registre est en ajout seul : on n'y corrige rien.
Les sessions de développement de Claude Code se comptent à part (`jetons_dev.py`) et se
rejoignent dans le rapport. Le coût en dollars est estimé au tarif de liste : avec un
abonnement ou une clé non facturée, c'est un ordre de grandeur, pas une facture.
"""
from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

# Tarif de liste, en dollars par million de jetons, relevé le 13 novembre 2026.
# entree, sortie, lecture du cache. L'écriture du cache coûte 1,25 fois l'entrée (5 minutes)
# ou 2 fois l'entrée (1 heure).
PRIX: dict[str, dict[str, Any]] = {
    "claude-haiku-5-5": {"entree": 0.10, "sortie": 0.50, "cache_lu": 0.01,
                         "seuil_long": 100_000, "long": {"entree": 0.50, "sortie": 2.50, "cache_lu": 0.05}},
    "claude-sonnet-5-5": {"entree": 2.0, "sortie": 10.0, "cache_lu": 0.10},
    "claude-opus-5-5": {"entree": 4.0, "sortie": 20.0, "cache_lu": 0.20},
    "claude-fable-5-2": {"entree": 8.0, "sortie": 40.0, "cache_lu": 0.20},
}
PRIX_RECHERCHE_WEB = 10.0 / 1000  # dollars par recherche
COEF_ECRITURE_5M = 1.25
COEF_ECRITURE_1H = 2.0


def prix_modele(modele: str | None) -> dict[str, Any] | None:
    """Ligne de prix d'un modèle, reconnue par son préfixe (les identifiants portent une date)."""
    if not modele:
        return None
    for cle in sorted(PRIX, key=len, reverse=True):
        if modele.startswith(cle):
            return PRIX[cle]
    return None


def cout_estime(
    modele: str | None,
    entree: int = 0,
    sortie: int = 0,
    cache_lu: int = 0,
    cache_ecrit_5m: int = 0,
    cache_ecrit_1h: int = 0,
    recherches_web: int = 0,
) -> float | None:
    """Coût estimé au tarif de liste, en dollars. None si le modèle n'est pas dans la grille."""
    p = prix_modele(modele)
    if p is None:
        return None
    grille = p
    if "seuil_long" in p and (entree + cache_lu + cache_ecrit_5m + cache_ecrit_1h) > p["seuil_long"]:
        grille = {**p, **p["long"]}
    m = 1_000_000
    cout = (
        entree * grille["entree"] / m
        + sortie * grille["sortie"] / m
        + cache_lu * grille["cache_lu"] / m
        + cache_ecrit_5m * grille["entree"] * COEF_ECRITURE_5M / m
        + cache_ecrit_1h * grille["entree"] * COEF_ECRITURE_1H / m
        + recherches_web * PRIX_RECHERCHE_WEB
    )
    return round(cout, 6)


def dossier_sorties() -> Path:
    return Path(os.environ.get("PREPA_RDV_SORTIES", "sorties"))


class Registre:
    """Journal des appels au modèle, un objet JSON par ligne."""

    def __init__(self, chemin: Path | None = None):
        self.chemin = Path(chemin) if chemin else dossier_sorties() / "journal" / "jetons.jsonl"

    def ajouter(self, **champs: Any) -> dict[str, Any]:
        ligne = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), **champs}
        self.chemin.parent.mkdir(parents=True, exist_ok=True)
        with self.chemin.open("a", encoding="utf-8") as f:
            f.write(json.dumps(ligne, ensure_ascii=False) + "\n")
        return ligne

    def lignes(self) -> list[dict[str, Any]]:
        if not self.chemin.exists():
            return []
        out = []
        for brut in self.chemin.read_text(encoding="utf-8").splitlines():
            brut = brut.strip()
            if brut:
                out.append(json.loads(brut))
        return out


COLONNES_JETONS = ("entree", "cache_ecrit", "cache_lu", "sortie", "recherches_web", "appels")


def totaux(lignes: Iterable[dict[str, Any]], par: tuple[str, ...] = ()) -> list[dict[str, Any]]:
    """Somme des jetons et du coût estimé, groupée par les clés demandées."""
    acc: dict[tuple, dict[str, Any]] = defaultdict(lambda: {c: 0 for c in COLONNES_JETONS} | {"cout_estime_usd": 0.0, "duree_ms": 0})
    for ligne in lignes:
        cle = tuple(ligne.get(k) for k in par)
        a = acc[cle]
        a["appels"] += ligne.get("appels", 1)
        for c in ("entree", "cache_ecrit", "cache_lu", "sortie", "recherches_web", "duree_ms"):
            a[c] += int(ligne.get(c) or 0)
        a["cout_estime_usd"] += float(ligne.get("cout_estime_usd") or 0.0)
    return [{**dict(zip(par, cle)), **valeurs, "cout_estime_usd": round(valeurs["cout_estime_usd"], 4)}
            for cle, valeurs in sorted(acc.items(), key=lambda kv: tuple(str(x) for x in kv[0]))]


def jetons_traites(ligne: dict[str, Any]) -> int:
    """Tous les jetons lus ou écrits par le modèle pour cette ligne (entrée fraîche, cache, sortie)."""
    return sum(int(ligne.get(c) or 0) for c in ("entree", "cache_ecrit", "cache_lu", "sortie"))
