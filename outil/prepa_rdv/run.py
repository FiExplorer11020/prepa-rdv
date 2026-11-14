"""Le pipeline d'une société, en six étapes : résoudre, chercher et lire, extraire, vérifier, noter, écrire.

Le code résout l'entité, relit les pages citées, vérifie et note. Le modèle cherche, lit et remplit un schéma fermé.
Chaque étape écrit au journal de la société. Une relance ne refait que ce qui a changé : l'entité, la sortie
du modèle et les pages lues sont gardées au cache, la vérification se rejoue chaque fois.
"""
from __future__ import annotations

import json
import re
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import __version__, agent, brief, contacts, fiche as fiche_mod, jetons_dev, relecture, sous_agents
from .jetons import Registre, dossier_sorties, jetons_traites, totaux
from .lecteur import Lecteur
from .listes import norm
from .modele import ClaudeCLI, ErreurModele
from .resolveur import Entite, Resolveur
from .schema import SortieModele, TrouvailleBrute
from .verificateur import verifier


def slug(nom: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", norm(nom)).strip("-")


@dataclass
class Contexte:
    sorties: Path
    lecteur: Lecteur
    resolveur: Resolveur
    modele: ClaudeCLI | None  # None : accès par sous-agents de la session (module `sous_agents`)
    registre: Registre
    run_id: str
    par_champ: bool = False
    phase: str = "run"
    sans_contacts: bool = False  # interrupteur du module contacts (cahier des charges, section 10)

    @classmethod
    def par_defaut(cls, modele: str = "claude-sonnet-5-5", phase: str = "run", par_champ: bool = False,
                   sans_contacts: bool = False, acces: str = "claude-cli") -> "Contexte":
        sorties = dossier_sorties()
        registre = Registre()
        return cls(sorties=sorties, lecteur=Lecteur(sorties / "cache" / "lectures"), resolveur=Resolveur(),
                   modele=ClaudeCLI(modele=modele, registre=registre) if acces == "claude-cli" else None, registre=registre,
                   run_id=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"), par_champ=par_champ, phase=phase,
                   sans_contacts=sans_contacts)


class Journal:
    """Une ligne par étape et par société : `journal.jsonl`."""

    def __init__(self, chemin: Path, run_id: str, societe: str):
        self.chemin, self.run_id, self.societe = chemin, run_id, societe
        chemin.parent.mkdir(parents=True, exist_ok=True)

    def ecrire(self, etape: str, debut: float, statut: str = "ok", erreur: str | None = None, **extra: Any) -> None:
        fin = time.time()
        ligne = {"run_id": self.run_id, "societe": self.societe, "etape": etape,
                 "debut": datetime.fromtimestamp(debut, timezone.utc).isoformat(timespec="seconds"),
                 "fin": datetime.fromtimestamp(fin, timezone.utc).isoformat(timespec="seconds"),
                 "duree_s": round(fin - debut, 2), "statut": statut, "erreur": erreur, **extra}
        with self.chemin.open("a", encoding="utf-8") as f:
            f.write(json.dumps(ligne, ensure_ascii=False) + "\n")


def _jetons_societe(ctx: Contexte, societe: str, depuis_iso: str) -> dict[str, Any]:
    lignes = [l for l in ctx.registre.lignes()
              if l.get("societe") == societe and l.get("phase") == ctx.phase and l.get("ts", "") >= depuis_iso]
    t = totaux(lignes, ())
    if not t:
        return {"traites": 0, "cout_estime_usd": 0.0, "appels": 0}
    t = t[0]
    return {"traites": jetons_traites(t), "entree": t["entree"], "cache_ecrit": t["cache_ecrit"], "cache_lu": t["cache_lu"],
            "sortie": t["sortie"], "recherches_web": t["recherches_web"], "appels": t["appels"], "cout_estime_usd": t["cout_estime_usd"]}


def traiter(nom: str, ctx: Contexte, forcer: bool = False) -> dict[str, Any]:
    """Pipeline complet d'une société. Renvoie la fiche."""
    debut_total = time.time()
    depuis = datetime.now(timezone.utc).isoformat(timespec="seconds")
    dossier = ctx.sorties / "societes" / slug(nom)
    dossier.mkdir(parents=True, exist_ok=True)
    journal = Journal(dossier / "journal.jsonl", ctx.run_id, nom)

    # 1. Résoudre l'entité
    t0 = time.time()
    chemin_entite = dossier / "entite.json"
    if chemin_entite.exists() and not forcer:
        entite = Entite(**json.loads(chemin_entite.read_text(encoding="utf-8")))
        journal.ecrire("resoudre", t0, "cache")
    else:
        entite = ctx.resolveur.resoudre(nom)
        chemin_entite.write_text(json.dumps(asdict(entite), ensure_ascii=False, indent=1), encoding="utf-8")
        journal.ecrire("resoudre", t0, source=entite.source, a_confirmer=entite.a_confirmer)

    # 2 et 3. Chercher, lire, extraire : un appel agent, gardé au cache
    t0 = time.time()
    chemin_agent = dossier / "agent.json"
    prompt_hash = agent.empreinte_prompt()
    if chemin_agent.exists() and not forcer and json.loads(chemin_agent.read_text(encoding="utf-8")).get("empreinte_prompt") == prompt_hash:
        brut = json.loads(chemin_agent.read_text(encoding="utf-8"))
        sortie = SortieModele.model_validate(brut["sortie"])
        plan = brut["plan"]
        modele_utilise = brut.get("modele", "inconnu")
        ids_agents = [s for s in brut.get("sessions", []) if s] if brut.get("acces") == "sous-agent" else []
        journal.ecrire("agent", t0, "cache", acces=brut.get("acces", "claude-cli"))
    elif ctx.modele is None:
        # Accès par sous-agents : l'outil écrit la demande, la session de Claude Code lance l'agent, `recevoir` reprend.
        demande = sous_agents.ecrire_demande(dossier, entite)
        journal.ecrire("agent", t0, "attente", demande=str(demande))
        raise sous_agents.AttenteAgent(nom, demande)
    else:
        try:
            res = agent.lancer(entite, ctx.modele, ctx.phase)
        except ErreurModele as e:
            journal.ecrire("agent", t0, "echec", str(e)[:400], modele=ctx.modele.modele)
            raise
        sortie, plan = res.sortie, res.plan
        modele_utilise, ids_agents = ctx.modele.modele, []
        chemin_agent.write_text(json.dumps({"empreinte_prompt": prompt_hash, "modele": modele_utilise, "plan": plan,
                                            "prompt": res.prompt, "sortie": sortie.model_dump(mode="json"),
                                            "sessions": [r.session for r in res.reponses]}, ensure_ascii=False, indent=1), encoding="utf-8")
        journal.ecrire("agent", t0, modele=modele_utilise, tours=sum((r.tours or 0) for r in res.reponses),
                       trouvailles=len(sortie.trouvailles), **_jetons_societe(ctx, nom, depuis))

    # 4 et 5. Vérifier et noter
    t0 = time.time()
    trouvailles = []
    for rang, b in enumerate(sortie.trouvailles, start=1):
        trouvailles.append(verifier(b, societe=nom, rang=rang, entite=entite, lecteur=ctx.lecteur, modele=modele_utilise,
                                    version_outil=__version__, empreinte_prompt=prompt_hash, par_champ=ctx.par_champ))
    # Seconde lecture à l'aveugle des pages que le code n'a pas pu lire (robots.txt, 401, 403, 429), si elle est faite.
    refus = relecture.a_relire(trouvailles)
    info_relecture: dict[str, Any] = {"a_relire": len(refus), "faites": 0, "en_attente": 0, "demande": None}
    if refus:
        if (dossier / relecture.FICHIER_SORTIE).exists():
            try:
                par_id = {l.id: l for l in relecture.lire_sortie(dossier).lectures}
            except ErreurModele as e:
                par_id = {}
                info_relecture["erreur"] = str(e)[:300]
            for t in refus:
                lecture = par_id.get(t.id)
                if lecture is None:
                    continue
                i = trouvailles.index(t)
                brute = TrouvailleBrute(**t.model_dump(include=set(TrouvailleBrute.model_fields)))
                trouvailles[i] = verifier(brute, societe=nom, rang=i + 1, entite=entite, lecteur=ctx.lecteur, modele=modele_utilise,
                                          version_outil=__version__, empreinte_prompt=prompt_hash, par_champ=ctx.par_champ,
                                          lecture=relecture.page_relue(t.url, lecture), mode="seconde_lecture")
                trouvailles[i].verifs.refus_du_code = " | ".join(t.verifs.erreurs)
                info_relecture["faites"] += 1
        restantes = [t for t in relecture.a_relire(trouvailles)]
        info_relecture["en_attente"] = len(restantes)
        if restantes:
            info_relecture["demande"] = str(relecture.ecrire_demande(dossier, nom, restantes))
    journal.ecrire("verifier", t0, trouvailles=len(trouvailles), rejetees=sum(1 for t in trouvailles if t.niveau.value == "non trouvé"),
                   relecture=info_relecture)

    # 6. Écrire la fiche et le brief
    t0 = time.time()
    jetons = jetons_dev.totaux_agents(ids_agents) if ids_agents else _jetons_societe(ctx, nom, depuis)
    fiche = fiche_mod.construire(
        entite, trouvailles, run_id=ctx.run_id, version_outil=__version__, empreinte_prompt=prompt_hash, modele=modele_utilise,
        plan_requetes=plan, remarques=sortie.remarques, champs_sans_resultat=[c.value for c in sortie.champs_sans_resultat],
        jetons=jetons, duree_s=time.time() - debut_total)
    fiche["relecture"] = info_relecture
    fiche["contact"] = contacts.construire(fiche, entite, getattr(ctx.lecteur, "cache", None), ctx.sans_contacts)
    (dossier / "fiche.json").write_text(json.dumps(fiche, ensure_ascii=False, indent=1), encoding="utf-8")
    contenu = brief.composer(fiche)
    problemes = brief.verifier_brief(contenu, fiche)
    (dossier / "brief.html").write_text(brief.html_document([contenu]), encoding="utf-8")
    journal.ecrire("ecrire", t0, problemes_brief=problemes)
    return fiche


def lot(noms: list[str], ctx: Contexte, paralleles: int = 2, forcer: bool = False) -> tuple[list[dict], dict[str, str]]:
    """Plusieurs sociétés, `paralleles` à la fois. Une société en échec ne bloque pas les autres.

    Une société qui attend un sous-agent n'est pas un échec : elle apparaît dans les « attentes » de `lot_detail`.
    """
    fiches, echecs, _ = lot_detail(noms, ctx, paralleles, forcer)
    return fiches, echecs


def lot_detail(noms: list[str], ctx: Contexte, paralleles: int = 2, forcer: bool = False) -> tuple[list[dict], dict[str, str], dict[str, Path]]:
    fiches: list[dict] = []
    echecs: dict[str, str] = {}
    attentes: dict[str, Path] = {}

    def une(nom: str):
        try:
            return nom, traiter(nom, ctx, forcer), None, None
        except sous_agents.AttenteAgent as e:
            return nom, None, None, e.demande
        except Exception as e:  # noqa: BLE001 : on note et on continue
            return nom, None, f"{type(e).__name__} : {str(e)[:300]}\n{traceback.format_exc(limit=2)[-300:]}", None

    with ThreadPoolExecutor(max_workers=max(1, paralleles)) as pool:
        for nom, f, err, demande in pool.map(une, noms):
            if f is not None:
                fiches.append(f)
            elif demande is not None:
                attentes[nom] = demande
            else:
                echecs[nom] = err or "échec"
    return fiches, echecs, attentes


def livrables(sorties: Path, ordre: list[str] | None = None, lien_outil: str = "") -> tuple[dict[str, Any], bool]:
    """Le PDF des briefs, les deux tableurs et leurs contrôles, depuis les fiches du dossier `sorties`."""
    from . import audit, tableur
    fiches = charger_fiches(sorties, ordre)
    if ordre:
        fiches.sort(key=lambda f: ordre.index(f["societe"]))
    contenus = [brief.composer(f) for f in fiches]
    problemes = {c["societe"]: brief.verifier_brief(c, f) for c, f in zip(contenus, fiches)}
    dossier = sorties / "livrables"
    dossier.mkdir(parents=True, exist_ok=True)
    rendu = brief.rendre_lot(contenus, dossier / "briefs.pdf")
    verdicts, relance, second = (audit.verdicts(sorties, t) for t in audit.TIRAGES)
    carto = tableur.ecrire_cartographie(fiches, dossier / "cartographie.xlsx", lien_outil, verdicts=verdicts,
                                        auditeur=audit.MODELE_AUDITEUR, relance=relance, second=second)
    longue = tableur.ecrire_trouvailles(fiches, dossier / "trouvailles.xlsx")
    bilan = {"societes": len(fiches), "pdf": rendu, "problemes_brief": {k: v for k, v in problemes.items() if v},
             "tableurs": {p.name: p.stat().st_size for p in (carto, longue)},
             "audit": {t: audit.resume(v.values()) for t, v in zip(audit.TIRAGES, (verdicts, relance, second)) if v} or None,
             "sous_10_mo": all(p.stat().st_size < 10_000_000 for p in (dossier / "briefs.pdf", carto, longue))}
    (dossier / "controles.json").write_text(json.dumps(bilan, ensure_ascii=False, indent=1), encoding="utf-8")
    return bilan, bool(rendu["ok"] and not bilan["problemes_brief"] and bilan["sous_10_mo"])


def charger_fiches(sorties: Path, noms: list[str] | None = None) -> list[dict]:
    fiches = []
    for chemin in sorted((sorties / "societes").glob("*/fiche.json")):
        f = json.loads(chemin.read_text(encoding="utf-8"))
        if noms is None or f["societe"] in noms:
            fiches.append(f)
    return fiches
