"""Ligne de commande : une commande par action.

    prepa-rdv essai-modele            appel à vide : l'accès au modèle marche, et son poids de base
    prepa-rdv resoudre NOM...         identité des sociétés (Wikidata, GLEIF, table locale)
    prepa-rdv societe NOM             une société, de bout en bout
    prepa-rdv lot societes.csv        plusieurs sociétés, deux à la fois
    prepa-rdv livrables               PDF des briefs et deux tableurs, avec leurs contrôles
    prepa-rdv demander-audit          demandes de l'agent auditeur (36 cellules tirées au sort, en lots)
    prepa-rdv recevoir-audit LOT      verdicts d'un lot validés, agent enregistré
    prepa-rdv depot DOSSIER           copie publique nettoyée et analysée ; --publier si l'analyse est verte
    prepa-rdv jetons                  jetons de tout le projet
    prepa-rdv horloge debut|pause|reprise|fin
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

from . import __version__, brief, horloge, rapport, run, sous_agents, tableur
from .jetons import dossier_sorties
from .modele import ErreurModele
from .resolveur import Entite


def _dossier_transcriptions(arg: Path | None) -> Path | None:
    if arg:
        return arg
    courant = Path.cwd().resolve()
    for d in (courant, *courant.parents):
        slug = str(d).replace("/", "-").replace(".", "-").replace("_", "-")
        candidat = Path.home() / ".claude" / "projects" / slug
        if candidat.exists():
            return candidat
    return None


def _noms(args: list[str]) -> list[str]:
    """Noms de sociétés : arguments directs, ou un fichier CSV avec une colonne « societe »."""
    if len(args) == 1 and args[0].lower().endswith(".csv"):
        with open(args[0], encoding="utf-8", newline="") as f:
            return [r["societe"].strip() for r in csv.DictReader(f) if r.get("societe", "").strip()]
    return args


def cmd_jetons(a: argparse.Namespace) -> int:
    transcriptions = None if a.sans_dev else _dossier_transcriptions(a.transcriptions)
    lignes = rapport.lignes_projet(transcriptions)
    if a.instantane:
        print(f"Instantané écrit : {rapport.ecrire_instantane(lignes)}", file=sys.stderr)
    print(rapport.formater(lignes))
    return 0


def cmd_horloge(a: argparse.Namespace) -> int:
    print(horloge.marquer(a.evenement, a.note))
    return 0


def cmd_essai_modele(a: argparse.Namespace) -> int:
    ctx = run.Contexte.par_defaut(a.modele, phase="essai")
    r = ctx.modele.verifier_acces()
    print(json.dumps({"reponse": r.texte[:80], "duree_ms": r.duree_ms, "usage": r.usage, "cout_declare_usd": r.cout_declare_usd,
                      "modeles": list((r.brut.get("modelUsage") or {}).keys())}, ensure_ascii=False, indent=1))
    return 0


def cmd_resoudre(a: argparse.Namespace) -> int:
    ctx = run.Contexte.par_defaut()
    for nom in _noms(a.noms):
        print(json.dumps(asdict(ctx.resolveur.resoudre(nom)), ensure_ascii=False))
    return 0


def cmd_demander(a: argparse.Namespace) -> int:
    """Prépare la demande de chaque société pour un sous-agent, et dit quoi lui donner."""
    ctx = run.Contexte.par_defaut(acces="sous-agents")
    for nom in _noms(a.noms):
        dossier = ctx.sorties / "societes" / run.slug(nom)
        dossier.mkdir(parents=True, exist_ok=True)
        chemin_entite = dossier / "entite.json"
        if chemin_entite.exists() and not a.forcer:
            entite = Entite(**json.loads(chemin_entite.read_text(encoding="utf-8")))
        else:
            entite = ctx.resolveur.resoudre(nom)
            chemin_entite.write_text(json.dumps(asdict(entite), ensure_ascii=False, indent=1), encoding="utf-8")
        print(json.dumps({"societe": nom, "demande": str(sous_agents.ecrire_demande(dossier, entite)),
                          "a_confirmer": entite.a_confirmer}, ensure_ascii=False))
    return 0


def cmd_recevoir(a: argparse.Namespace) -> int:
    ctx = run.Contexte.par_defaut(acces="sous-agents")
    dossier = ctx.sorties / "societes" / run.slug(a.nom)
    entite = Entite(**json.loads((dossier / "entite.json").read_text(encoding="utf-8")))
    try:
        sortie = sous_agents.recevoir(dossier, entite, a.agent_id, a.phase, a.modele)
    except ErreurModele as e:
        print(f"Réponse refusée : {e}", file=sys.stderr)
        return 1
    print(json.dumps({"societe": a.nom, "trouvailles": len(sortie.trouvailles),
                      "sans_resultat": [c.value for c in sortie.champs_sans_resultat]}, ensure_ascii=False))
    return 0


def cmd_recevoir_relecture(a: argparse.Namespace) -> int:
    from . import relecture
    dossier = dossier_sorties() / "societes" / run.slug(a.nom)
    try:
        r = relecture.resume(relecture.lire_sortie(dossier))
    except ErreurModele as e:
        print(f"Réponse refusée : {e}", file=sys.stderr)
        return 1
    sous_agents.enregistrer_agent(a.agent_id, a.nom, a.phase, role="relecture")
    print(json.dumps({"societe": a.nom, **r}, ensure_ascii=False))
    return 0


def cmd_demander_audit(a: argparse.Namespace) -> int:
    from . import audit
    fiches = run.charger_fiches(dossier_sorties())
    if not fiches:
        print("Aucune fiche dans", dossier_sorties() / "societes", file=sys.stderr)
        return 1
    for p in (audit.ecrire_second(fiches) if a.second else audit.ecrire_demandes(fiches, a.lots)):
        print(p)
    return 0


def cmd_recevoir_audit(a: argparse.Namespace) -> int:
    from . import audit
    try:
        r = audit.recevoir(a.lot, a.agent_id, a.phase)
    except (ErreurModele, FileNotFoundError) as e:
        print(f"Réponse refusée : {e}", file=sys.stderr)
        return 1
    print(json.dumps(r, ensure_ascii=False))
    return 0


def cmd_societe(a: argparse.Namespace) -> int:
    ctx = run.Contexte.par_defaut(a.modele, a.phase, a.par_champ, a.sans_contacts, a.acces)
    try:
        f = run.traiter(a.nom, ctx, a.forcer)
    except sous_agents.AttenteAgent as e:
        print(f"En attente d'un sous-agent : {e.demande}", file=sys.stderr)
        return 2
    print(json.dumps({"societe": f["societe"], "synthese": {c: s["niveau"] for c, s in f["synthese"].items()},
                      "sources": f["nombre_sources"], "jetons": f["jetons"], "duree_s": f["duree_s"]}, ensure_ascii=False, indent=1))
    return 0


def cmd_lot(a: argparse.Namespace) -> int:
    ctx = run.Contexte.par_defaut(a.modele, a.phase, a.par_champ, a.sans_contacts, a.acces)
    fiches, echecs, attentes = run.lot_detail(_noms(a.noms), ctx, a.paralleles, a.forcer)
    for f in fiches:
        print(f"{f['societe']:18} " + " ".join(f"{c}={s['niveau']}" for c, s in f["synthese"].items() if c != "identite"))
    for nom, demande in attentes.items():
        print(f"EN ATTENTE {nom} : sous-agent à lancer, demande dans {demande}", file=sys.stderr)
    for nom, err in echecs.items():
        print(f"ÉCHEC {nom} : {err.splitlines()[0]}", file=sys.stderr)
    return 1 if echecs else (2 if attentes else 0)


def cmd_bilan(a: argparse.Namespace) -> int:
    from . import bilan
    fiches = run.charger_fiches(dossier_sorties(), a.noms or None)
    b = bilan.bilan_lot(fiches)
    (dossier_sorties() / "journal").mkdir(parents=True, exist_ok=True)
    (dossier_sorties() / "journal" / f"bilan-{a.nom}.json").write_text(json.dumps(b, ensure_ascii=False, indent=1), encoding="utf-8")
    print(bilan.formater(b))
    return 0


def cmd_erreurs(a: argparse.Namespace) -> int:
    from . import erreurs
    ctx = run.Contexte.par_defaut(acces="sous-agents")
    nouvelles = erreurs.releve(run.charger_fiches(dossier_sorties(), a.noms or None), ctx.lecteur)
    for e in nouvelles:
        print(f"{e['id_trouvaille']:28} {e['cause']:20} {e['detecteur']}\n    écrit : {e['ecrit'][:150]}\n    source : {e['source_dit'][:150]}")
    print(json.dumps({"nouvelles": len(nouvelles), **erreurs.comptes()}, ensure_ascii=False))
    return 0


def cmd_erreur_corrigee(a: argparse.Namespace) -> int:
    from . import erreurs
    try:
        print(json.dumps(erreurs.corriger(a.id, a.changement, a.relance, a.cause, a.source_dit), ensure_ascii=False))
    except (KeyError, ValueError) as e:
        print(e, file=sys.stderr)
        return 1
    return 0


def cmd_textes(a: argparse.Namespace) -> int:
    from . import textes
    fiches = run.charger_fiches(dossier_sorties())
    if not fiches:
        print("Aucune fiche dans", dossier_sorties() / "societes", file=sys.stderr)
        return 1
    for p in textes.ecrire(dossier_sorties(), fiches, _dossier_transcriptions(a.transcriptions), a.lien_outil):
        print(p)
    return 0


def cmd_livrables(a: argparse.Namespace) -> int:
    sorties = dossier_sorties()
    ordre = _noms([a.ordre]) if a.ordre else None
    if not run.charger_fiches(sorties, ordre):
        print("Aucune fiche dans", sorties / "societes", file=sys.stderr)
        return 1
    bilan, ok = run.livrables(sorties, ordre, a.lien_outil)
    print(json.dumps(bilan, ensure_ascii=False, indent=1))
    return 0 if ok else 1


def cmd_depot(a: argparse.Namespace) -> int:
    from . import depot
    rapport_depot = depot.construire(a.dossier, prive=a.prive, lien_outil=a.lien_outil, recomposer=not a.sans_livrables,
                                     audit=not a.sans_audit)
    print(json.dumps(rapport_depot.resume(), ensure_ascii=False, indent=1))
    if not rapport_depot.propre:
        print("Analyse non verte : rien n'est publié.", file=sys.stderr)
        return 1
    if a.publier:
        print(depot.publier(a.dossier, a.message))
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="prepa-rdv", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)

    def modele(s):
        s.add_argument("--modele", default="claude-sonnet-5-5")
        s.add_argument("--phase", default="run", help="essai, sonde, run, audit, demo...")
        s.add_argument("--par-champ", action="store_true", help="fenêtres de fraîcheur par champ (cahier des charges, 6.4)")
        s.add_argument("--sans-contacts", action="store_true", help="retire le bloc contacts des briefs")
        s.add_argument("--acces", choices=["claude-cli", "sous-agents"], default=os.environ.get("PREPA_RDV_ACCES", "claude-cli"),
                       help="claude-cli : `claude -p`. sous-agents : demandes écrites, agents lancés par la session de Claude Code")

    j = sub.add_parser("jetons", help="rapport des jetons de tout le projet")
    j.add_argument("--transcriptions", type=Path, help="dossier des transcriptions de Claude Code")
    j.add_argument("--sans-dev", action="store_true", help="ne lit que le registre de l'outil")
    j.add_argument("--instantane", action="store_true", help="écrit sorties/journal/jetons-dev.json")
    j.set_defaults(fonction=cmd_jetons)

    h = sub.add_parser("horloge", help="marque un événement de l'horloge de construction")
    h.add_argument("evenement", choices=["debut", "pause", "reprise", "fin"])
    h.add_argument("--note", default="")
    h.set_defaults(fonction=cmd_horloge)

    e = sub.add_parser("essai-modele", help="appel à vide du modèle")
    e.add_argument("--modele", default="claude-sonnet-5-5")
    e.set_defaults(fonction=cmd_essai_modele)

    r = sub.add_parser("resoudre", help="identité des sociétés")
    r.add_argument("noms", nargs="+")
    r.set_defaults(fonction=cmd_resoudre)

    d = sub.add_parser("demander", help="écrit la demande de chaque société pour un sous-agent")
    d.add_argument("noms", nargs="+")
    d.add_argument("--forcer", action="store_true")
    d.set_defaults(fonction=cmd_demander)

    rc = sub.add_parser("recevoir", help="valide la réponse d'un sous-agent et enregistre l'agent")
    rc.add_argument("nom")
    rc.add_argument("--agent-id", required=True)
    rc.add_argument("--phase", default="run")
    rc.add_argument("--modele", default="claude-sonnet-5-5 (sous-agent)")
    rc.set_defaults(fonction=cmd_recevoir)

    rr = sub.add_parser("recevoir-relecture", help="valide la seconde lecture d'un sous-agent et enregistre l'agent")
    rr.add_argument("nom")
    rr.add_argument("--agent-id", required=True)
    rr.add_argument("--phase", default="run")
    rr.set_defaults(fonction=cmd_recevoir_relecture)

    da = sub.add_parser("demander-audit", help="écrit les demandes de l'agent auditeur, un fichier par lot de cellules")
    da.add_argument("--lots", type=int, default=3, help="nombre de lots, donc d'agents auditeurs")
    da.add_argument("--second", action="store_true", help="après une correction : cellules partielles ou fausses rejugées, et 12 cellules neuves")
    da.set_defaults(fonction=cmd_demander_audit)

    ra = sub.add_parser("recevoir-audit", help="valide les verdicts d'un lot et enregistre l'agent auditeur")
    ra.add_argument("lot", type=int)
    ra.add_argument("--agent-id")
    ra.add_argument("--phase", default="audit")
    ra.set_defaults(fonction=cmd_recevoir_audit)

    s = sub.add_parser("societe", help="une société, de bout en bout")
    s.add_argument("nom")
    s.add_argument("--forcer", action="store_true", help="ignore le cache de l'entité et du modèle")
    modele(s)
    s.set_defaults(fonction=cmd_societe)

    l = sub.add_parser("lot", help="plusieurs sociétés")
    l.add_argument("noms", nargs="+", help="noms, ou un fichier CSV avec une colonne « societe »")
    l.add_argument("--paralleles", type=int, default=2)
    l.add_argument("--forcer", action="store_true")
    modele(l)
    l.set_defaults(fonction=cmd_lot)

    er = sub.add_parser("erreurs", help="relève dans le journal d'erreurs ce que les contrôles du code ont vu")
    er.add_argument("noms", nargs="*")
    er.set_defaults(fonction=cmd_erreurs)

    ec = sub.add_parser("erreur-corrigee", help="note le changement et la relance qui corrigent une erreur")
    ec.add_argument("id")
    ec.add_argument("--changement", required=True, help="ce qui a changé : règle, consigne, liste, code")
    ec.add_argument("--relance", required=True, help="ce qui a été relancé ensuite")
    ec.add_argument("--cause", help="corrige la cause quand l'analyse montre que la première était fausse")
    ec.add_argument("--source-dit", dest="source_dit", help="ce que la page dit réellement, quand la première lecture l'avait manqué")
    ec.set_defaults(fonction=cmd_erreur_corrigee)

    tx = sub.add_parser("textes", help="écrit « Ton outil » et « Et à 200 sociétés ? » depuis les journaux")
    tx.add_argument("--transcriptions", type=Path)
    tx.add_argument("--lien-outil", default="", help="adresse du dépôt public, citée dans « Ton outil »")
    tx.set_defaults(fonction=cmd_textes)

    bl = sub.add_parser("bilan", help="niveaux, motifs de rejet et jetons d'un lot de fiches")
    bl.add_argument("noms", nargs="*", help="sociétés à inclure (toutes par défaut)")
    bl.add_argument("--nom", default="lot", help="nom du fichier de bilan : journal/bilan-NOM.json")
    bl.set_defaults(fonction=cmd_bilan)

    v = sub.add_parser("livrables", help="PDF des briefs et tableurs")
    v.add_argument("--ordre", help="fichier CSV des sociétés, pour l'ordre des pages")
    v.add_argument("--lien-outil", default="", help="adresse du dépôt, écrite dans le tableur")
    v.set_defaults(fonction=cmd_livrables)

    dp = sub.add_parser("depot", help="construit et analyse la copie publique du cas ; la publie si l'analyse est verte")
    dp.add_argument("dossier", type=Path, help="dossier du dépôt public (vide, ou copie précédente)")
    dp.add_argument("--prive", type=Path, help="fichier JSON des noms interdits et des remplacements (jamais copié)")
    dp.add_argument("--lien-outil", default="", help="adresse du dépôt, écrite dans le tableur de la copie")
    dp.add_argument("--sans-livrables", action="store_true", help="ne recompose pas les briefs et les tableurs")
    dp.add_argument("--sans-audit", action="store_true", help="ne lance pas pip-audit")
    dp.add_argument("--publier", action="store_true", help="commit et push si l'analyse est verte")
    dp.add_argument("--message", default="Mise à jour de la copie publique", help="message du commit")
    dp.set_defaults(fonction=cmd_depot)

    a = p.parse_args(argv)
    return a.fonction(a)


if __name__ == "__main__":
    raise SystemExit(main())
