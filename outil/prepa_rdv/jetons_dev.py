"""Jetons des sessions de développement de Claude Code, lus dans leurs transcriptions.

Chaque session écrit `<id>.jsonl` dans `~/.claude/projects/<dossier>/`, et ses sous-agents dans
`<id>/subagents/agent-*.jsonl`. Un appel d'API y occupe plusieurs lignes (une par bloc de contenu), avec
le même identifiant de message : on garde une ligne par message. Les jetons réels sont dans
`usage.iterations` (la somme des itérations) ; les totaux de tête valent zéro tant que la réponse n'est
pas finie.

Les jetons de lecture du cache dominent : Claude Code relit tout le contexte à chaque appel. Le rapport
les montre à part des jetons écrits (entrée fraîche, écriture du cache, sortie).
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any

from .jetons import cout_estime

CLES = ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")


def _usage_effectif(usage: dict[str, Any]) -> dict[str, int]:
    itérations = usage.get("iterations") or []
    sources = itérations if itérations else [usage]
    out = {k: sum(int(s.get(k) or 0) for s in sources) for k in CLES}
    c5 = c1 = 0
    for s in sources:
        cc = s.get("cache_creation") or {}
        c5 += int(cc.get("ephemeral_5m_input_tokens") or 0)
        c1 += int(cc.get("ephemeral_1h_input_tokens") or 0)
    if c5 + c1 == 0:
        c5 = out["cache_creation_input_tokens"]  # sans détail, tout compte au tarif de 5 minutes
    out["cache_5m"], out["cache_1h"] = c5, c1
    out["recherches_web"] = int((usage.get("server_tool_use") or {}).get("web_search_requests") or 0)
    return out


def lire_appels(chemin: Path) -> list[dict[str, Any]]:
    """Un dict par appel d'API de la transcription, dédoublonné par identifiant de message."""
    par_id: dict[str, dict[str, Any]] = {}
    with chemin.open(encoding="utf-8") as f:
        for brut in f:
            brut = brut.strip()
            if not brut:
                continue
            try:
                r = json.loads(brut)
            except json.JSONDecodeError:
                continue
            if r.get("type") != "assistant":
                continue
            m = r.get("message") or {}
            usage = m.get("usage")
            if not isinstance(usage, dict) or m.get("model") in (None, "<synthetic>"):
                continue
            u = _usage_effectif(usage)
            cle = m.get("id") or r.get("uuid")
            actuel = par_id.get(cle)
            if actuel is None or sum(u[k] for k in CLES) >= sum(actuel[k] for k in CLES):
                par_id[cle] = {**u, "modele": m.get("model"), "ts": r.get("timestamp")}
    return list(par_id.values())


def transcription_agent(agent_id: str, racine: Path | None = None) -> Path | None:
    """Transcription d'un sous-agent, quelle que soit la session qui l'a lancé."""
    racine = racine or Path.home() / ".claude" / "projects"
    return next(iter(racine.glob(f"*/*/subagents/agent-{agent_id}.jsonl")), None)


def totaux_agents(ids: list[str], racine: Path | None = None) -> dict[str, Any]:
    """Jetons et coût estimé d'un ou plusieurs sous-agents, pour la fiche d'une société."""
    t = {"entree": 0, "cache_ecrit": 0, "cache_lu": 0, "sortie": 0, "recherches_web": 0, "appels": 0, "cout_estime_usd": 0.0, "duree_s": 0.0}
    for i in ids:
        chemin = transcription_agent(i, racine)
        if chemin is None:
            continue
        appels = lire_appels(chemin)
        if appels:  # durée de l'agent : du premier au dernier appel de sa transcription
            debut = min(datetime.fromisoformat(a["ts"].replace("Z", "+00:00")) for a in appels)
            fin = max(datetime.fromisoformat(a["ts"].replace("Z", "+00:00")) for a in appels)
            t["duree_s"] += (fin - debut).total_seconds()
        for a in appels:
            t["appels"] += 1
            t["entree"] += a["input_tokens"]
            t["sortie"] += a["output_tokens"]
            t["cache_lu"] += a["cache_read_input_tokens"]
            t["cache_ecrit"] += a["cache_creation_input_tokens"]
            t["recherches_web"] += a["recherches_web"]
            t["cout_estime_usd"] += cout_estime(a["modele"], a["input_tokens"], a["output_tokens"], a["cache_read_input_tokens"],
                                                a["cache_5m"], a["cache_1h"], a["recherches_web"]) or 0.0
    t["cout_estime_usd"] = round(t["cout_estime_usd"], 4)
    t["traites"] = t["entree"] + t["cache_ecrit"] + t["cache_lu"] + t["sortie"]
    return t


def importer(
    dossier_projet: Path,
    debut_construction: datetime | None = None,
    depuis: date = date(2026, 11, 13),
    exclure: tuple[str, ...] = (),
    correspondance: dict[str, dict] | None = None,
) -> list[dict[str, Any]]:
    """Lignes agrégées par session, agent, phase et modèle.

    La portée « cas » prend les sessions dont le premier appel date de `depuis` ou après ; les autres
    sont « hors-cas » (ici : une session antérieure, sans lien avec l'outil). La phase est « planification »
    avant `debut_construction`, « construction » après.
    """
    fichiers: list[tuple[str, str, Path]] = []
    for p in sorted(dossier_projet.glob("*.jsonl")):
        fichiers.append((p.stem, "principal", p))
        for sa in sorted((dossier_projet / p.stem / "subagents").glob("agent-*.jsonl")):
            fichiers.append((p.stem, sa.stem.replace("agent-", "sous-agent-"), sa))

    lignes: list[dict[str, Any]] = []
    for session, agent, chemin in fichiers:
        if session in exclure:
            continue
        appels = lire_appels(chemin)
        if not appels:
            continue
        premier = min(a["ts"] for a in appels)
        portee = "cas" if datetime.fromisoformat(premier.replace("Z", "+00:00")).date() >= depuis else "hors-cas"
        acc: dict[tuple, dict[str, Any]] = defaultdict(lambda: {
            "appels": 0, "entree": 0, "cache_ecrit": 0, "cache_lu": 0, "sortie": 0, "recherches_web": 0,
            "cache_5m": 0, "cache_1h": 0, "cout_estime_usd": 0.0, "premier": None, "dernier": None,
        })
        for a in appels:
            t = datetime.fromisoformat(a["ts"].replace("Z", "+00:00"))
            if portee == "hors-cas":
                phase = "hors-cas"
            elif debut_construction is not None and t >= debut_construction:
                phase = "construction"
            else:
                phase = "planification"
            x = acc[(phase, a["modele"])]
            x["appels"] += 1
            x["entree"] += a["input_tokens"]
            x["sortie"] += a["output_tokens"]
            x["cache_lu"] += a["cache_read_input_tokens"]
            x["cache_ecrit"] += a["cache_creation_input_tokens"]
            x["cache_5m"] += a["cache_5m"]
            x["cache_1h"] += a["cache_1h"]
            x["recherches_web"] += a["recherches_web"]
            x["cout_estime_usd"] += cout_estime(
                a["modele"], a["input_tokens"], a["output_tokens"], a["cache_read_input_tokens"],
                a["cache_5m"], a["cache_1h"], a["recherches_web"]) or 0.0
            x["premier"] = a["ts"] if x["premier"] is None else min(x["premier"], a["ts"])
            x["dernier"] = a["ts"] if x["dernier"] is None else max(x["dernier"], a["ts"])
        mappe = (correspondance or {}).get(agent.replace("sous-agent-", "")) if agent.startswith("sous-agent-") else None
        for (phase, modele), x in acc.items():
            ligne = {
                "source": "dev", "portee": portee, "phase": phase, "session": session, "agent": agent,
                "modele": modele, **{k: (round(v, 4) if isinstance(v, float) else v) for k, v in x.items()},
            }
            if mappe:  # agent de l'outil : il compte pour la société et la phase, pas pour le développement
                ligne.update(source="outil", societe=mappe["societe"], phase=mappe["phase"], backend="sous-agent", portee="cas")
            lignes.append(ligne)
    return lignes
