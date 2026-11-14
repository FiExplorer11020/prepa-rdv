"""Accès au modèle.

`ClaudeCLI` appelle Claude Code en mode non interactif (`claude -p`) : il marche avec un abonnement, sans
clé de la Console. Chaque appel est écrit au registre des jetons, modèle par modèle (Claude Code utilise
aussi un petit modèle pour résumer les pages lues).

Le coût en dollars est estimé au tarif de liste, et on garde à côté celui que Claude Code déclare. Avec un
abonnement, aucun des deux n'est une facture.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import Any

from .jetons import Registre, cout_estime


class ErreurModele(RuntimeError):
    """L'appel au modèle a échoué. Les jetons éventuellement consommés sont déjà au registre."""

    def __init__(self, message: str, brut: Any = None):
        super().__init__(message)
        self.brut = brut


@dataclass
class Reponse:
    modele: str
    texte: str
    donnees: Any
    usage: dict[str, Any]
    cout_declare_usd: float | None
    duree_ms: int
    tours: int | None
    session: str | None
    brut: dict[str, Any] = field(repr=False, default_factory=dict)


def _extraire_json(texte: str) -> Any:
    """JSON d'une réponse en texte, avec ou sans bloc de code."""
    t = texte.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", t, re.S)
    if m:
        t = m.group(1).strip()
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        debut, fin = t.find("{"), t.rfind("}")
        if debut != -1 and fin > debut:
            return json.loads(t[debut:fin + 1])
        raise


class ClaudeCLI:
    """Claude Code en mode non interactif."""

    nom = "claude-cli"

    def __init__(
        self,
        modele: str = "claude-sonnet-5-5",
        outils: tuple[str, ...] = (),
        delai_s: int = 900,
        budget_usd: float | None = None,
        registre: Registre | None = None,
        binaire: str | None = None,
    ):
        self.modele = modele
        self.outils = outils
        self.delai_s = delai_s
        self.budget_usd = budget_usd
        self.registre = registre or Registre()
        self.binaire = binaire or shutil.which("claude") or os.path.expanduser("~/.local/bin/claude")

    # -- environnement et commande -------------------------------------------------------------

    @staticmethod
    def _env() -> dict[str, str]:
        """Environnement minimal : ni les réglages de la session qui nous lance, ni une clé d'API."""
        garder = ("HOME", "PATH", "USER", "LANG", "LC_ALL", "TMPDIR", "SHELL")
        env = {k: os.environ[k] for k in garder if k in os.environ}
        env.setdefault("LANG", "fr_FR.UTF-8")
        return env

    def _commande(self, schema: dict | None, systeme: str | None, outils: tuple[str, ...]) -> list[str]:
        cmd = [self.binaire, "-p", "--output-format", "json", "--model", self.modele, "--no-session-persistence",
               "--tools", ",".join(outils)]
        if outils:
            cmd += ["--allowedTools", ",".join(outils)]
        if systeme:
            cmd += ["--append-system-prompt", systeme]
        if schema:
            cmd += ["--json-schema", json.dumps(schema, ensure_ascii=False)]
        if self.budget_usd:
            cmd += ["--max-budget-usd", str(self.budget_usd)]
        return cmd

    # -- appel ---------------------------------------------------------------------------------

    def appeler(
        self,
        prompt: str,
        *,
        schema: dict | None = None,
        systeme: str | None = None,
        outils: tuple[str, ...] | None = None,
        phase: str = "run",
        societe: str | None = None,
        note: str = "",
    ) -> Reponse:
        outils = self.outils if outils is None else outils
        cmd = self._commande(schema, systeme, outils)
        with tempfile.TemporaryDirectory(prefix="prepa-rdv-") as neutre:  # hors de tout dossier portant un CLAUDE.md
            try:
                p = subprocess.run(cmd, input=prompt, text=True, capture_output=True, timeout=self.delai_s,
                                   env=self._env(), cwd=neutre)
            except subprocess.TimeoutExpired as e:
                self.registre.ajouter(source="outil", backend=self.nom, phase=phase, societe=societe, modele=self.modele,
                                      statut="delai_depasse", note=note)
                raise ErreurModele(f"Délai de {self.delai_s} s dépassé") from e

        brut = None
        try:
            brut = json.loads(p.stdout)
            if isinstance(brut, list):
                brut = next((x for x in brut if isinstance(x, dict) and x.get("type") == "result"), {})
        except json.JSONDecodeError:
            pass
        if not isinstance(brut, dict):
            self.registre.ajouter(source="outil", backend=self.nom, phase=phase, societe=societe, modele=self.modele,
                                  statut="illisible", note=(p.stderr or p.stdout)[:300])
            raise ErreurModele(f"Sortie illisible (code {p.returncode}) : {(p.stderr or p.stdout)[:300]}")

        self._journaliser(brut, phase, societe, note)
        if p.returncode != 0 or brut.get("is_error"):
            raise ErreurModele(f"Échec ({brut.get('subtype')}) : {str(brut.get('result'))[:300]}", brut)

        texte = brut.get("result") or ""
        donnees = brut.get("structured_output")
        if donnees is None and schema is not None:
            try:
                donnees = _extraire_json(texte)
            except json.JSONDecodeError as e:
                raise ErreurModele(f"Réponse sans JSON valide : {texte[:300]}", brut) from e
        return Reponse(
            modele=self.modele, texte=texte, donnees=donnees, usage=brut.get("usage") or {},
            cout_declare_usd=brut.get("total_cost_usd"), duree_ms=int(brut.get("duration_ms") or 0),
            tours=brut.get("num_turns"), session=brut.get("session_id"), brut=brut,
        )

    def _journaliser(self, brut: dict, phase: str, societe: str | None, note: str) -> None:
        """Une ligne de registre par modèle utilisé pendant l'appel."""
        par_modele = brut.get("modelUsage") or {}
        if not par_modele:  # repli : l'usage global, attribué au modèle demandé
            u = brut.get("usage") or {}
            par_modele = {self.modele: {
                "inputTokens": u.get("input_tokens", 0), "outputTokens": u.get("output_tokens", 0),
                "cacheReadInputTokens": u.get("cache_read_input_tokens", 0),
                "cacheCreationInputTokens": u.get("cache_creation_input_tokens", 0),
                "webSearchRequests": (u.get("server_tool_use") or {}).get("web_search_requests", 0),
                "costUSD": brut.get("total_cost_usd")}}
        premiere = True
        for modele, u in par_modele.items():
            entree, sortie = int(u.get("inputTokens") or 0), int(u.get("outputTokens") or 0)
            lu, ecrit = int(u.get("cacheReadInputTokens") or 0), int(u.get("cacheCreationInputTokens") or 0)
            recherches = int(u.get("webSearchRequests") or 0)
            self.registre.ajouter(
                source="outil", backend=self.nom, phase=phase, societe=societe, modele=modele, appels=1 if premiere else 0,
                entree=entree, sortie=sortie, cache_lu=lu, cache_ecrit=ecrit, recherches_web=recherches,
                duree_ms=int(brut.get("duration_ms") or 0) if premiere else 0,
                tours=brut.get("num_turns") if premiere else None,
                cout_estime_usd=cout_estime(modele, entree, sortie, lu, ecrit, 0, recherches),
                cout_declare_usd=u.get("costUSD"), session=brut.get("session_id"), statut="ok" if not brut.get("is_error") else "erreur",
                note=note,
            )
            premiere = False

    def verifier_acces(self) -> Reponse:
        """Appel à vide : sans outil, une réponse d'un mot. Sert à la porte G0 et à mesurer le poids de base."""
        return self.appeler("Réponds par le seul mot OK.", outils=(), phase="essai", note="appel à vide")
