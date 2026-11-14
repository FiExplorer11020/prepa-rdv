"""Accès au modèle par des sous-agents de Claude Code, quand la session interactive est le seul accès disponible.

Le circuit, par société :
1. `ecrire_demande` écrit `demande.md` : consignes, demande, schéma et chemin de la réponse.
2. La session de Claude Code lance un sous-agent par société. Il cherche et lit le web, puis écrit `agent-sortie.json`.
3. `recevoir` valide la réponse contre le schéma fermé, l'écrit au cache de l'outil (`agent.json`) et enregistre
   l'agent dans `agents-outil.jsonl`, pour que ses jetons se comptent par société et une seule fois.
4. Le code reprend : relecture des pages, vérification, niveau de confiance, fiche, brief.

Le modèle ne reçoit rien d'autre que ce que l'outil lui écrit, et l'outil ne lit de lui que le fichier de réponse.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

from . import agent
from .jetons import dossier_sorties
from .modele import ErreurModele, _extraire_json
from .resolveur import Entite
from .schema import SortieModele

FICHIER_DEMANDE = "demande.md"
FICHIER_SORTIE = "agent-sortie.json"
CORRESPONDANCE = "agents-outil.jsonl"


class AttenteAgent(RuntimeError):
    """La société attend la réponse d'un sous-agent. Ce n'est pas une erreur : c'est une étape à faire."""

    def __init__(self, societe: str, demande: Path):
        super().__init__(f"{societe} : en attente d'un sous-agent, demande dans {demande}")
        self.societe, self.demande = societe, demande


def chemin_correspondance() -> Path:
    return dossier_sorties() / "journal" / CORRESPONDANCE


def ecrire_demande(dossier: Path, entite: Entite) -> Path:
    """Écrit la demande d'une société et renvoie son chemin. Le schéma et les consignes viennent de `agent.preparer`."""
    d = agent.preparer(entite)
    sortie = (dossier / FICHIER_SORTIE).resolve()
    texte = f"""# Demande pour {entite.nom_saisi}

Tu es l'agent de recherche d'un outil de préparation de rendez-vous. Fais le travail décrit ci-dessous et écris le résultat
dans un fichier. Moyens autorisés : WebSearch, WebFetch et Write (pour le seul fichier de réponse). N'utilise ni le skill
agent-reach, ni Firecrawl, ni LinkedIn, ni aucun serveur MCP. Ne modifie aucun autre fichier.

## Consignes

{d.systeme}

## Demande

{d.prompt}

## Réponse attendue

Écris dans le fichier `{sortie}` un seul objet JSON, sans texte autour, conforme à ce schéma. Tous les champs de chaque
trouvaille sont obligatoires : mets null quand il n'y a pas de valeur. Réponds ensuite par le seul mot OK.

```json
{json.dumps(d.schema, ensure_ascii=False, indent=1)}
```
"""
    chemin = dossier / FICHIER_DEMANDE
    chemin.write_text(texte, encoding="utf-8")
    (dossier / "demande.json").write_text(json.dumps({"societe": entite.nom_saisi, "empreinte_prompt": d.empreinte_prompt,
                                                      "plan": d.plan, "sortie": str(sortie)}, ensure_ascii=False, indent=1), encoding="utf-8")
    return chemin


def lire_sortie(dossier: Path) -> SortieModele:
    """Réponse du sous-agent, validée contre le schéma fermé. Lève ErreurModele avec la raison si elle ne passe pas."""
    chemin = dossier / FICHIER_SORTIE
    if not chemin.exists():
        raise ErreurModele(f"Pas de réponse : {chemin} n'existe pas")
    try:
        brut = _extraire_json(chemin.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ErreurModele(f"Réponse sans JSON valide : {e}") from e
    try:
        return SortieModele.model_validate(brut)
    except ValidationError as e:
        raise ErreurModele(f"Réponse hors schéma : {str(e)[:600]}") from e


def recevoir(dossier: Path, entite: Entite, agent_id: str | None = None, phase: str = "run", modele: str = "claude-sonnet-5-5 (sous-agent)") -> SortieModele:
    """Valide la réponse, l'écrit au cache de l'outil et enregistre l'agent pour le comptage des jetons."""
    sortie = lire_sortie(dossier)
    d = agent.preparer(entite)
    (dossier / "agent.json").write_text(json.dumps({
        "empreinte_prompt": d.empreinte_prompt, "modele": modele, "plan": d.plan, "prompt": d.prompt,
        "sortie": sortie.model_dump(mode="json"), "sessions": [agent_id] if agent_id else [], "acces": "sous-agent"},
        ensure_ascii=False, indent=1), encoding="utf-8")
    if agent_id:
        enregistrer_agent(agent_id, entite.nom_saisi, phase)
    return sortie


def enregistrer_agent(agent_id: str, societe: str, phase: str, role: str = "agent") -> None:
    """Un sous-agent de l'outil : ses jetons s'attribuent à la société et à la phase, et ne comptent pas comme développement."""
    p = chemin_correspondance()
    p.parent.mkdir(parents=True, exist_ok=True)
    if agent_id in correspondance():
        return
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "agent_id": agent_id,
                            "societe": societe, "phase": phase, "role": role}, ensure_ascii=False) + "\n")


def correspondance() -> dict[str, dict]:
    p = chemin_correspondance()
    if not p.exists():
        return {}
    lignes = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
    return {l["agent_id"]: l for l in lignes}
