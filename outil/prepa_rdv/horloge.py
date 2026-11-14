"""Horloge de la construction : le cas plafonne l'effort à trois heures.

Le fichier `sorties/journal/horloge.jsonl` reçoit des événements datés : `debut`, `pause`, `reprise`, `fin`.
Le temps actif est la somme des intervalles entre un `debut` ou une `reprise` et la `pause` ou la `fin`
qui suit. Une attente de l'extérieur (connexion à faire, relecture par une personne) se déclare en `pause`.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .jetons import dossier_sorties


def chemin() -> Path:
    return dossier_sorties() / "journal" / "horloge.jsonl"


def marquer(evenement: str, note: str = "", ts: datetime | None = None) -> dict:
    ligne = {"ts": (ts or datetime.now(timezone.utc)).isoformat(timespec="seconds"), "evenement": evenement, "note": note}
    p = chemin()
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(ligne, ensure_ascii=False) + "\n")
    return ligne


def lire() -> list[dict]:
    p = chemin()
    if not p.exists():
        return []
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def debut_construction() -> datetime | None:
    for e in lire():
        if e["evenement"] == "debut":
            return datetime.fromisoformat(e["ts"])
    return None


def temps_actif(maintenant: datetime | None = None) -> float:
    """Secondes de construction active, pauses déduites."""
    maintenant = maintenant or datetime.now(timezone.utc)
    total, ouvert = 0.0, None
    for e in lire():
        t = datetime.fromisoformat(e["ts"])
        if e["evenement"] in ("debut", "reprise") and ouvert is None:
            ouvert = t
        elif e["evenement"] in ("pause", "fin") and ouvert is not None:
            total += (t - ouvert).total_seconds()
            ouvert = None
    if ouvert is not None:
        total += (maintenant - ouvert).total_seconds()
    return total
