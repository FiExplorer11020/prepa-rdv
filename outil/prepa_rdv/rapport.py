"""Rapport des jetons de tout le projet : développement avec Claude Code, essais et runs de l'outil."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import horloge, sous_agents
from .jetons import PRIX, Registre, dossier_sorties, jetons_traites, totaux
from .jetons_dev import importer


def dossier_projet_claude() -> Path:
    """Dossier des transcriptions de Claude Code pour le répertoire de travail courant."""
    slug = str(Path.cwd().resolve()).replace("/", "-").replace(".", "-").replace("_", "-")
    return Path.home() / ".claude" / "projects" / slug


def lignes_projet(dossier_transcriptions: Path | None = None) -> list[dict[str, Any]]:
    """Lignes du registre de l'outil et des sessions de développement, dans un même format."""
    lignes = [{**l, "source": "outil", "portee": "cas"} for l in Registre().lignes()]
    if dossier_transcriptions is not None and dossier_transcriptions.exists():
        lignes += importer(dossier_transcriptions, horloge.debut_construction(), correspondance=sous_agents.correspondance())
    return lignes


def _n(valeur: int | float, decimales: int = 0) -> str:
    """Nombre à la française : espace insécable entre les milliers, virgule décimale."""
    texte = f"{valeur:,.{decimales}f}".replace(",", " ")
    return texte.replace(".", ",")


def _ligne(lib: str, t: dict[str, Any]) -> str:
    traites = t["entree"] + t["cache_ecrit"] + t["cache_lu"] + t["sortie"]
    return (f"| {lib} | {_n(t['appels'])} | {_n(t['entree'])} | {_n(t['cache_ecrit'])} | {_n(t['cache_lu'])} | "
            f"{_n(t['sortie'])} | {_n(traites)} | {_n(t['cout_estime_usd'], 2)} |")


NOMS_MODELES = {"claude-haiku-5-5": "Haiku 5.5", "claude-sonnet-5-5": "Sonnet 5.5", "claude-opus-5-5": "Opus 5.5",
                "claude-fable-5-2": "Fable 5.2"}


def _tarifs(lignes: list[dict[str, Any]]) -> str:
    """Le tarif de chaque modèle présent dans les lignes, dans l'ordre de la table des prix."""
    presents = {str(l.get("modele") or "") for l in lignes}
    phrases = [f"{nom} à {_n(PRIX[cle]['entree'], 2).rstrip('0').rstrip(',')} $ en entrée, "
               f"{_n(PRIX[cle]['sortie'], 2).rstrip('0').rstrip(',')} $ en sortie et {_n(PRIX[cle]['cache_lu'], 2)} $ en lecture du cache"
               for cle, nom in NOMS_MODELES.items() if any(m.startswith(cle) for m in presents)]
    return " ; ".join(phrases) or "aucun appel compté"


def formater(lignes: list[dict[str, Any]]) -> str:
    cas = [l for l in lignes if l.get("portee", "cas") == "cas"]
    hors = [l for l in lignes if l.get("portee") == "hors-cas"]
    en_tete = ("| | Appels | Entrée fraîche | Cache écrit | Cache lu | Sortie | Total traité | Coût estimé ($) |\n"
               "|---|---|---|---|---|---|---|---|")
    out = ["## Jetons du projet (cas pratique)", "", en_tete]
    for t in totaux(cas, ("source", "phase")):
        out.append(_ligne(f"{t['source']} / {t['phase']}", t))
    tot = totaux(cas, ())
    if tot:
        out.append(_ligne("**Total du cas**", tot[0]))
    out += ["", f"Coût estimé au tarif de liste du modèle de chaque appel, par million de jetons : {_tarifs(cas)}. Ce n'est pas une "
            "facture : l'accès passe par un abonnement ou par un compte non facturé. "
            "Les jetons lus dans le cache dominent le total, car Claude Code relit tout son contexte à chaque appel."]
    if hors:
        h = totaux(hors, ())[0]
        out += ["", f"Hors du cas (une session antérieure du même dossier, sans lien avec l'outil) : {_n(jetons_traites(h))} jetons traités, "
                f"{_n(h['cout_estime_usd'], 2)} $ estimés."]
    par_societe = totaux([l for l in cas if l.get("source") == "outil" and l.get("societe")], ("societe",))
    if par_societe:
        out += ["", "### Par société (appels de l'outil)", "", en_tete.replace("| |", "| Société |", 1)]
        for t in par_societe:
            out.append(_ligne(str(t["societe"]), t))
    actif = horloge.temps_actif()
    if actif:
        out += ["", f"Temps de construction actif : {actif / 60:.0f} minutes (plafond du cas : 180)."]
    return "\n".join(out)


def ecrire_instantane(lignes: list[dict[str, Any]]) -> Path:
    """Copie datée des lignes de développement, pour que le rapport survive aux transcriptions."""
    chemin = dossier_sorties() / "journal" / "jetons-dev.json"
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(json.dumps([l for l in lignes if l.get("source") == "dev"], ensure_ascii=False, indent=1), encoding="utf-8")
    return chemin
