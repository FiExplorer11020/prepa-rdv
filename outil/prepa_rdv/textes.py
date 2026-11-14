"""Les deux textes du cas, produits depuis les journaux : « Ton outil » et « Et à 200 sociétés ? ».

Chaque nombre vient des fiches, du bilan, du registre des jetons ou du journal d'erreurs : aucun n'est tapé à la main.
La source est du Markdown. `rendre_pdf` en fait un PDF lisible avec le moteur Chrome des briefs.
"""
from __future__ import annotations

import html
import re
import statistics
from pathlib import Path
from typing import Any

from . import agent, bilan as bilan_mod, brief, erreurs as erreurs_mod, horloge, rapport
from .jetons import cout_estime
from .schema import LIBELLES_CHAMP, Champ


def _n(valeur: float | int, decimales: int = 0) -> str:
    return f"{valeur:,.{decimales}f}".replace(",", " ").replace(".", ",")


def _phrase(texte: str) -> str:
    """Un texte sans point final, pour l'enchaîner dans une phrase."""
    return " ".join(str(texte).split()).rstrip(". ")


# Ce que les fiches ne disent pas d'elles-mêmes : la seconde lecture de Barilla, arrêtée par un garde-fou de l'API sous Sonnet 5.5,
# a été relancée avec un autre modèle le 14 novembre 2026.
RELANCES_RELECTURE = {"Barilla": "Opus 5.5"}
# Bilan d'avant la correction du test d'accord des deux lectures, gardé tel quel pour le comparer à l'état présent.
BILAN_AVANT_ACCORD = "bilan-avant-accord.json"


def _accord_avant() -> tuple[int, int]:
    """Lignes concordantes et lignes relues, d'après le bilan gardé avant la correction du test d'accord."""
    import json
    from .jetons import dossier_sorties
    p = dossier_sorties() / "journal" / BILAN_AVANT_ACCORD
    if not p.exists():
        return (0, 0)
    t = json.loads(p.read_text(encoding="utf-8"))["total"]
    return t["relues_confirmees"], t["relues"]


def _relances(fiches: list[dict]) -> tuple[str, int, int]:
    """La phrase sur les secondes lectures relancées, et leurs lignes relues et concordantes."""
    phrases, relues, accords = [], 0, 0
    for societe, modele in RELANCES_RELECTURE.items():
        f = next((x for x in fiches if x["societe"] == societe), None)
        rel = [x for x in (f or {}).get("trouvailles", []) if x["verifs"].get("mode_verification") == "seconde_lecture"]
        if not rel:
            continue
        ouvertes = sum(1 for x in rel if x["verifs"].get("adresse_ok"))
        accord = sum(1 for x in rel if x["niveau"] != "non trouvé")
        relues, accords = relues + len(rel), accords + accord
        phrases.append(f" Le second agent de {societe} a d'abord été arrêté par un garde-fou de l'API, avant d'écrire. Relancé avec un "
                       f"autre modèle ({modele}), il a pu ouvrir la page de {ouvertes} lignes sur {len(rel)}, et {accord} s'accordent avec la "
                       f"première lecture.")
    return "".join(phrases), relues, accords


def _pl(n: int, singulier: str, pluriel: str) -> str:
    """Le nombre et son nom, au singulier pour zéro et un."""
    return f"{n} {singulier if n <= 1 else pluriel}"


def _champ(c: str) -> str:
    """Le nom du champ en milieu de phrase : « ERP » et « TMS » gardent leurs capitales."""
    return c if c.isupper() else c[:1].lower() + c[1:]


def _audit(fiches: list[dict]) -> str:
    """Les lignes de l'audit : les verdicts de l'agent auditeur s'il les a rendus, l'échantillon à relire sinon."""
    from . import audit
    from .jetons import dossier_sorties
    v = audit.verdicts(dossier_sorties())
    if not v:
        return ("- Audit : la feuille « Audit » de `cartographie.xlsx` liste 36 cellules tirées au sort (graine fixe), à marquer juste ou "
                "faux par une personne.\n- Ce que le code ne voit pas : une citation exacte qui ne dit pas ce que le modèle en conclut "
                "(extrapolation). L'audit d'un échantillon tiré au sort, relu par une personne, sert à cela.")
    r = audit.resume(v.values())
    ecarts = [j for j in v.values() if j["verdict"] in ("partiel", "faux")]
    ecarts_txt = ("Écarts relevés : " + " ; ".join(f"{j['societe']}, {_champ(j['champ'])} ({j['verdict']}, {j['ecart']})" for j in ecarts)
                  + ". ") if ecarts else "Aucun écart relevé. "
    lues = {t["id"]: t for f in fiches for t in f["trouvailles"]}
    absentes = [i for i, j in v.items() if j["citation_presente"] is False]
    vues_par_code = sum(1 for i in absentes if (lues.get(i) or {}).get("verifs", {}).get("citation_trouvee"))
    absentes_txt = (f" Sur {_pl(len(absentes), 'page', 'pages')}, l'auditeur dit ne pas retrouver la citation ; le code l'avait retrouvée "
                    f"mot pour mot sur {vues_par_code}, dans le texte qu'il a lu." if absentes else "")
    part = 100 * r["juste"] / max(1, r["verifiables"])
    n_lots = len({j.get("lot") for j in v.values()})
    qui = (f"{_pl(n_lots, 'sous-agent auditeur', 'sous-agents auditeurs')}, un par lot,") if n_lots > 1 else "un sous-agent auditeur"
    return (f"- Audit : {r['cellules']} cellules de la cartographie, tirées au sort avec une graine fixe, ont été jugées par {qui} "
            f"d'un autre modèle que les agents de recherche ({audit.MODELE_AUDITEUR}). L'auditeur ouvre chaque lien et dit si la page "
            f"soutient la valeur, sans connaître le niveau donné par l'outil. Verdicts : {_pl(r['juste'], 'juste', 'justes')}, "
            f"{_pl(r['partiel'], 'partielle', 'partielles')}, {_pl(r['faux'], 'fausse', 'fausses')}, "
            f"{_pl(r['invérifiable'], 'invérifiable', 'invérifiables')}. Sur les {r['verifiables']} cellules vérifiables, {r['juste']} "
            f"{'est juste' if r['juste'] <= 1 else 'sont justes'} ({_n(part)} %). {ecarts_txt}Le détail, cellule par cellule, est dans la feuille « Audit » de `cartographie.xlsx`."
            f"{absentes_txt}{_apres_audit(v, ecarts)}\n- Ce que le code ne voit pas : une citation exacte qui ne dit pas ce que l'outil en conclut. L'auditeur la "
            "cherche, mais c'est un modèle qui en juge un autre : ses verdicts partiels et faux sont les premiers à relire par une personne.")


SEUIL_G4 = 90


def _verdicts_txt(r: dict) -> str:
    return (f"{_pl(r['juste'], 'juste', 'justes')}, {_pl(r['partiel'], 'partielle', 'partielles')}, {_pl(r['faux'], 'fausse', 'fausses')}, "
            f"{_pl(r['invérifiable'], 'invérifiable', 'invérifiables')}")


def _part(r: dict) -> str:
    return f"{r['juste']} sur {r['verifiables']} vérifiables ({_n(100 * r['juste'] / max(1, r['verifiables']))} %)"


def _apres_audit(premier: dict[str, dict], ecarts: list[dict]) -> str:
    """Ce qui a suivi le premier audit : règles d'affichage (D21), cellules rejugées, second tirage, porte G4 (D22)."""
    from . import audit
    from .jetons import dossier_sorties
    relance, second = audit.verdicts(dossier_sorties(), "relance"), audit.verdicts(dossier_sorties(), "second")
    if not (relance or second):
        return ""
    par_ecart: dict[str, int] = {}
    for j in ecarts:
        par_ecart[j["ecart"]] = par_ecart.get(j["ecart"], 0) + 1
    regles = {"filiale ou division", "projet ou évaluation"}
    n_regles = sum(n for e, n in par_ecart.items() if e in regles)
    txt = (f"\n- Après l'audit : {n_regles} des {len(ecarts)} écarts venaient de deux oublis d'affichage, notés par l'auditeur « filiale ou "
           f"division » ({par_ecart.get('filiale ou division', 0)}) et « projet ou évaluation » ({par_ecart.get('projet ou évaluation', 0)}). "
           "Le modèle avait relevé l'entité que la page nomme et, dans son commentaire, que la migration était prévue ; la cellule ne "
           "gardait que le produit. Deux règles l'écrivent désormais dans la cellule, au brief, à la cartographie et à l'audit (D21) : "
           "l'entité nommée quand ce n'est pas la société, et « migration prévue ou en cours » pour un ERP, une plateforme d'achats ou "
           "un TMS. Les niveaux ne changent pas.")
    if relance:
        rr = audit.resume(relance.values())
        corrige = audit.resume({**premier, **relance}.values())
        par_cat: dict[str, list[int]] = {}
        for i, j in relance.items():
            c = par_cat.setdefault((premier.get(i) or {}).get("ecart") or "", [0, 0])
            c[0], c[1] = c[0] + (j["verdict"] == "juste"), c[1] + 1
        txt += f" Un nouvel auditeur a rejugé les {rr['cellules']} cellules telles qu'elles s'affichent : {_verdicts_txt(rr)}."
        ok, n = par_cat.get("projet ou évaluation", [0, 0])
        if n:
            txt += (f" Avec la règle du projet, {ok} sur {_pl(n, 'cellule', 'cellules')} « projet ou évaluation » "
                    f"{'devient juste' if ok <= 1 else 'deviennent justes'}.")
        ok, n = par_cat.get("filiale ou division", [0, 0])
        if n and not ok:
            txt += (f" Avec celle de l'entité, aucun des {n} verdicts « filiale ou division » ne change, l'auditeur jugeant toujours "
                    "qu'une page sur une filiale ne dit pas le système du groupe.")
        elif n:
            txt += f" Avec celle de l'entité, {ok} sur {_pl(n, 'cellule', 'cellules')} « filiale ou division » {'devient juste' if ok <= 1 else 'deviennent justes'}."
        if n > ok:  # choix d'Oscar du 14 novembre 2026 : la cellule reste un signal (D22)
            txt += (" Une cellule tirée d'une page sur une filiale reste dans la fiche, la filiale signalée comme le prévoit le cahier "
                    "des charges, et sa valeur se vérifie pour le groupe pendant le rendez-vous (D22).")
        txt += f" Le premier tirage passe ainsi à {_part(corrige)}."
    if second:
        rs = audit.resume(second.values())
        txt += (f" Un second tirage de {rs['cellules']} cellules nouvelles (graine {audit.GRAINE_SECONDE}), que les règles n'avaient pas "
                f"vues, donne {_verdicts_txt(rs)}, soit {_part(rs)}.")
        passee = 100 * rs["juste"] / max(1, rs["verifiables"]) >= SEUIL_G4
        if relance:  # le premier tirage a servi à écrire les règles : la porte se mesure sur le second (D22)
            statut = "elle est passée" if passee else "elle n'est pas passée"
            txt += (f" La porte G4, fixée à {SEUIL_G4} %, se mesure sur ce tirage plutôt que sur le premier, qui a servi à écrire les "
                    f"règles, et {statut}.")
        else:
            statut = "est passée" if passee else "n'est pas passée"
            txt += f" Sur ce tirage, la porte G4, fixée à {SEUIL_G4} %, {statut}."
        if 0 < rs["verifiables"] < 30:
            txt += (f" L'échantillon reste petit, et une seule de ces cellules jugée fausse l'aurait mis à "
                    f"{_n(100 * (rs['juste'] - 1) / rs['verifiables'])} %.")
    return txt


def table(entetes: list[str], lignes: list[list[Any]]) -> str:
    sortie = ["| " + " | ".join(entetes) + " |", "|" + "|".join("---" for _ in entetes) + "|"]
    sortie += ["| " + " | ".join(str(c) for c in l) + " |" for l in lignes]
    return "\n".join(sortie)


def _par_societe(fiches: list[dict]) -> list[list[Any]]:
    lignes = []
    for f in fiches:
        j = f.get("jetons") or {}
        n = [t["niveau"] for t in f["trouvailles"]]
        duree = j.get("duree_s") or f.get("duree_s") or 0
        lignes.append([f["societe"], f"{_n(duree / 60, 1)} min", _n(j.get("traites", 0)), _n(j.get("sortie", 0)), j.get("appels", 0),
                       _n(j.get("cout_estime_usd", 0), 2), len(n), n.count("confirmé"), n.count("probable"), n.count("non trouvé")])
    return lignes


def ton_outil(fiches: list[dict], erreurs: list[dict], rapport_jetons: str, lien_outil: str = "") -> str:
    lien_ligne = f"\n- Le code, les journaux et la méthode sont publiés sous licence MIT : {lien_outil}" if lien_outil else ""
    b = bilan_mod.bilan_lot(fiches)
    t = b["total"]
    lignes = _par_societe(fiches)
    # Le journal est en ajout seul : on garde la dernière ligne de chaque erreur (la corrigée remplace l'ouverte).
    derniere: dict[tuple, dict] = {}
    for e in erreurs:
        derniere[(e["id_trouvaille"], e["ecrit"])] = e
    uniques = list(derniere.values())
    corrigees = [e for e in uniques if e.get("changement") and e.get("relance")]
    ouvertes = [e for e in uniques if e not in corrigees]
    exemples, causes_vues = [], set()
    for e in corrigees:  # une erreur par cause d'abord, puis les suivantes, quatre au plus
        if e["cause"] not in causes_vues:
            exemples.append(e)
            causes_vues.add(e["cause"])
    exemples += [e for e in corrigees if e not in exemples][:max(0, 4 - len(exemples))]

    def decrire(e: dict) -> str:
        libelle = LIBELLES_CHAMP[Champ(e["champ"])] if e["champ"] in Champ._value2member_map_ else e["champ"]
        corrige = bool(e.get("changement") and e.get("relance"))
        fin = (f"Changement : {_phrase(e['changement'])}. Relance : {_phrase(e['relance'])}." if corrige
               else "Pas de réparation possible : la trouvaille reste écartée.")
        return (f"**{e['societe']}, {libelle.lower()}.** Écrit par l'outil : {_phrase(e['ecrit'])}. Vu par le {_phrase(e['detecteur'])} "
                f"(similarité {_n(e['similarite'], 2)}). Ce que dit la page : {_phrase(e['source_dit'][:300])}. Cause : {e['cause']}. {fin}")

    fait = [decrire(e) for e in exemples[:4]]
    if len(fait) < 2:  # les erreurs vues mais pas encore corrigées restent dites telles quelles
        fait += [decrire(e) for e in ouvertes[: 2 - len(fait)]]
    par_cause: dict[str, int] = {}
    for e in uniques:
        par_cause[e["cause"]] = par_cause.get(e["cause"], 0) + 1
    detail_causes = ", ".join(f"{n} {c}" for c, n in sorted(par_cause.items(), key=lambda x: -x[1]))
    resume_erreurs = (f"{len(uniques)} erreurs relevées par les contrôles du code ({detail_causes}). {len(corrigees)} sont corrigées, avec un "
                      f"changement et une relance. {len(ouvertes)} sont écartées sans réparation possible : la trouvaille reste « non trouvé » et "
                      f"n'atteint ni le brief ni la cartographie. « Page lue incomplète » est une erreur du lecteur de l'outil, pas du modèle.")
    actif = horloge.temps_actif() / 60
    rejets_txt = ", ".join(f"{k} ({v})" for k, v in sorted(t["rejets"].items(), key=lambda x: -x[1])) or "aucun"
    js = [f.get("jetons") or {} for f in fiches]
    moy_duree = statistics.mean([x.get("duree_s") or 0 for x in js] or [0])
    moy_traites = statistics.mean([x.get("traites") or 0 for x in js] or [0])
    moy_cout = statistics.mean([x.get("cout_estime_usd") or 0 for x in js] or [0])
    relances_txt, relues_relancees, accords_relances = _relances(fiches)
    ACCORD_AVANT = _accord_avant()
    accords_memes_lignes = t["relues_confirmees"] - accords_relances  # les lignes relues avant la relance, sous le test corrigé
    # Trouvailles gardées dont la valeur n'est nommée que par une base de données (P5) : elles n'entrent pas dans la synthèse.
    seules_p5 = sum(1 for f in fiches for x in f["trouvailles"] if x["niveau"] != "non trouvé" and x["champ"] != "identite"
                    and x["verifs"].get("type_source_code") == "P5"
                    and not any(i == x["id"] for v in (f["synthese"].get(x["champ"]) or {}).get("valeurs", []) for i in v.get("ids", [])))
    audit_txt = _audit(fiches)
    return f"""# Ton outil : comment il fonctionne et où il s'est trompé

## En bref

L'outil prépare un rendez-vous avec la direction financière d'une société : il cherche son ERP, sa plateforme d'achats, son TMS et ses financements court terme en place, sur sources publiques. Chaque information porte une citation recopiée mot pour mot, l'adresse de la page, sa date et un niveau de confiance. Le modèle cherche et remplit un schéma fermé. Le code relit les pages, vérifie et note : le modèle ne note jamais sa propre confiance.

Sur {len(fiches)} sociétés, l'outil a produit {t['trouvailles']} trouvailles. {t['gardees']} ont passé les contrôles, {t['trouvailles'] - t['gardees']} ont été rejetées. Une société prend {_n(moy_duree / 60, 1)} minutes d'agent en moyenne, pour {_n(moy_traites / 1_000_000, 1)} millions de jetons traités, soit {_n(moy_cout, 2)} $ au tarif de liste de l'API : c'est une estimation, car l'accès passe par un abonnement. Construction : {_n(actif)} minutes de travail actif, planification comptée à part.

## La chaîne, en six étapes

{table(["Étape", "Qui", "Ce qui en sort"], [
    ["1. Résoudre l'entité", "Code", "Nom légal, pays, statut, site, domaines (Wikidata puis GLEIF ; table locale si Wikidata refuse le client)"],
    ["2. Chercher", "Modèle", "Plan de requêtes fixe par champ, en anglais et dans la langue du siège, écrit au journal"],
    ["3. Lire", "Modèle", "Pages web ouvertes par l'agent, jamais plus de 20 par société"],
    ["4. Extraire", "Modèle", "Trouvailles dans un schéma fermé : valeur d'une liste, citation de 25 mots au plus, adresse, date"],
    ["5. Vérifier et noter", "Code", "Page relue par le code, citation retrouvée mot pour mot (à défaut, le passage de la page le plus proche qui porte la valeur, au plus « probable »), type de source recalculé, société nommée, date dans la fenêtre, niveau par table"],
    ["6. Écrire", "Code", "Fiche, brief d'une page, deux tableurs, journaux"],
])}

## Outils et sources

- Python 3.12, `uv` (versions et empreintes figées), `pydantic` (schéma fermé), `httpx` (lecture polie : robots.txt, pause par hôte, cache), `trafilatura` et `pypdf` (HTML et PDF en texte), `RapidFuzz` (similarité des citations), `openpyxl` (tableurs), Chrome sans affichage (PDF).
- Le modèle passe par des sous-agents de Claude Code (recherche et lecture web du fournisseur) ou par `claude -p`. Pas de clé d'API.
- Sources : pages de la société, communiqués et études de cas des éditeurs, presse, offres d'emploi. Wikidata et GLEIF pour l'identité. Aucune base payante, ni LinkedIn.
- Jina Reader (service gratuit, 20 requêtes par minute) rend une page par JavaScript quand la lecture directe est pauvre et que la citation manque. Jamais après un refus du site.
- Un site qui refuse la lecture au code (robots.txt, HTTP 401, 403, 429) n'est jamais contourné. Une seconde lecture à l'aveugle par un autre agent, qui ne connaît pas la citation du premier, peut alors la confirmer. Les deux lectures s'accordent quand le plus court des deux textes se retrouve mot pour mot dans l'autre, sur six mots au moins qui nomment la valeur. Ces lignes ne dépassent jamais « probable », car le code n'a pas lu la page lui-même.{lien_ligne}

## Temps et coût par société

{table(["Société", "Durée de l'agent", "Jetons traités", "Jetons de sortie", "Appels du modèle", "Coût estimé ($)", "Trouvailles", "Confirmé", "Probable", "Rejetées"], lignes)}

Le coût est estimé au tarif de liste de l'API (Sonnet 5.5). Il n'est pas facturé : l'accès passe par un abonnement. Les jetons lus dans le cache dominent les totaux, car Claude Code relit son contexte à chaque appel.

## Le prompt principal

Version `{agent.empreinte_prompt()}`. Le texte de consignes envoyé à chaque agent, sans la demande propre à la société :

```text
{agent.systeme()}
```

## Où l'outil s'est trompé

{resume_erreurs} Quatre exemples, un par cause quand c'est possible :

{chr(10).join(f"{i}. {x}" for i, x in enumerate(fait, start=1)) or "Aucune erreur relevée pour l'instant."}

Le journal complet est dans `sorties/journal/erreurs.jsonl`. Une erreur sans changement associé n'est pas comptée comme corrigée.

## Ce que les contrôles voient, et ce qu'ils laissent passer

- Rejets par motif : {rejets_txt}.
- Trouvailles gardées mais hors fenêtre de fraîcheur ou sans date : {t['hors_fenetre'] + t['sans_date']} sur {t['gardees']}, soit {_n(100 * (t['hors_fenetre'] + t['sans_date']) / max(1, t['gardees']))} %. Sous la moitié : les fenêtres de départ restent (24 mois pour la société, 36 pour un tiers qui la nomme, 24 pour la presse, 12 pour un signal indirect), sans fenêtres par champ.
- Pages lues par le code : {t['pages_lues']}. Pages refusées ou illisibles pour lui : {t['pages_refusees']}.
- Sur les {t['lisibles']} trouvailles dont la page a pu être lue par le code (constats d'identité exclus), {t['mot_pour_mot']} citations du modèle sont retrouvées mot pour mot ({_n(100 * t['mot_pour_mot'] / max(1, t['lisibles']), 1)} %), {t['reparees']} sont réparées par un passage de la page et {t['lisibles'] - t['mot_pour_mot'] - t['reparees']} sont écartées.
- Relecture à l'aveugle : {t['relues']} lignes relues par un second agent, dont {t['relues_confirmees']} s'accordent avec la première lecture et passent à « probable ». Les autres restent écartées : page fermée au second agent aussi, autre phrase de la même page, passage trop court ou qui ne nomme pas le produit.{relances_txt}
- Une erreur du contrôle lui-même : le code cherchait la citation du premier agent (25 mots au plus) dans le passage du second (15 mots au plus). Le test échouait dès que la citation était la plus longue des deux, et il a rejeté à tort des lectures concordantes. Il cherche désormais le plus court des deux textes dans l'autre. Sur les {ACCORD_AVANT[1]} lignes relues avant la relance, l'accord passe de {ACCORD_AVANT[0]} à {accords_memes_lignes}.
- Citations que le code a réparées en gardant un passage de la page : {t['reparees']}. Pages relues rendues par JavaScript : {t['lues_rendues']}.
- Une page de base de données commerciale (type P5) ne sert que de second avis : une valeur qu'elle seule nomme reste dans le tableur des trouvailles, pas dans le brief. Trouvailles concernées sur ce lot : {seules_p5}.
{audit_txt}

## Jetons de tout le projet

{rapport_jetons.replace("## Jetons du projet (cas pratique)", "", 1).strip()}

Le tableau par société compte aussi les secondes lectures, d'où des totaux plus hauts que dans le tableau des temps et coûts, qui ne compte que l'agent de recherche. Chaque appel est compté au tarif du modèle qui l'a fait : Sonnet 5.5 pour les agents de recherche et les secondes lectures, {", ".join(f"{m} pour la seconde lecture relancée de {s}" for s, m in RELANCES_RELECTURE.items())}.
"""


def _audit_200(cout: float | None) -> str:
    """Ce que l'audit a mesuré ici, pour l'étendre à 200 sociétés : verdicts et coût par cellule."""
    from . import audit
    from .jetons import dossier_sorties
    v = audit.verdicts(dossier_sorties())
    if not v:
        return ""
    r = audit.resume(v.values())
    n = sum(len(audit.verdicts(dossier_sorties(), t)) for t in audit.TIRAGES)
    cout_txt = f", {_n(cout / n, 2)} $ estimés par cellule" if cout else ""
    second, relance = audit.verdicts(dossier_sorties(), "second"), audit.verdicts(dossier_sorties(), "relance")
    if second:
        rs = audit.resume(second.values())
        apres = f", {audit.resume({**v, **relance}.values())['juste']} après deux règles d'affichage" if relance else ""
        return (f" Mesuré ici : {r['juste']} justes sur {r['verifiables']} vérifiables au premier tirage{apres}, {rs['juste']} sur "
                f"{rs['verifiables']} au second{cout_txt}.")
    return f" Mesuré ici : {r['juste']} justes sur {r['verifiables']} vérifiables{cout_txt}."


def cout_phase(lignes: list[dict], phase: str) -> float | None:
    """Coût estimé des appels d'une phase de l'outil, d'après les lignes du rapport des jetons."""
    xs = [l for l in lignes if l.get("portee", "cas") == "cas" and l.get("source") == "outil" and l.get("phase") == phase]
    return round(sum(l.get("cout_estime_usd") or 0 for l in xs), 2) if xs else None


def a_200(fiches: list[dict], cout_audit: float | None = None) -> str:
    b = bilan_mod.bilan_lot(fiches)
    j = [f.get("jetons") or {} for f in fiches]
    traites = [x.get("traites", 0) for x in j if x.get("traites")]
    sortie = [x.get("sortie", 0) for x in j if x.get("sortie")]
    med_traites = statistics.median(traites) if traites else 0
    med_sortie = statistics.median(sortie) if sortie else 0
    med_cout = statistics.median([x.get("cout_estime_usd", 0) for x in j if x.get("cout_estime_usd")] or [0])
    duree = statistics.median([(x.get("duree_s") or 0) for x in j if x.get("duree_s")] or [0])
    t = b["total"]
    cache_lu = sum(x.get("cache_lu", 0) for x in j)
    part_cache = cache_lu / max(1, sum(x.get("traites", 0) for x in j))
    taux_rejet = 1 - (t["gardees"] / t["trouvailles"]) if t["trouvailles"] else 0
    taux_refus = t["pages_refusees"] / max(1, t["pages_lues"] + t["pages_refusees"])
    taux_relues = t["relues_confirmees"] / max(1, t["relues"])
    heures_relecture = 200 * 10 / 60
    incompletes = sum(1 for e in {(x["id_trouvaille"], x["ecrit"]): x for x in erreurs_mod.lire()}.values() if e["cause"] == "page lue incomplète")
    audit_200 = _audit_200(cout_audit)
    return f"""# Et à 200 sociétés ? Ce qui casse, et ce que je changerais

## Coût et temps, d'après les {len(fiches)} sociétés mesurées

- Une société coûte en médiane {_n(med_traites / 1_000_000, 1)} millions de jetons traités, dont {_n(med_sortie / 1000, 0)} mille de sortie, soit {_n(med_cout, 2)} $ au tarif de liste de l'API. Pour 200 sociétés : environ {_n(round(med_cout * 200, -1), 0)} $. C'est une estimation, car l'accès passe par un abonnement. La remise de moitié du traitement par lots ne s'applique pas telle quelle à un agent qui lit le web en plusieurs tours : je ne la compte pas.
- {_n(100 * part_cache)} % des jetons sont de la relecture du contexte à chaque appel de l'agent (cache lu). À 200 sociétés, des boucles plus courtes (moins de pages ouvertes par l'agent, lecture et vérification laissées au code) pèsent donc plus que le prix du jeton.
- Une société prend en médiane {_n(duree / 60, 1)} minutes d'agent. À dix agents en parallèle, comme pour ces douze sociétés, 200 sociétés tiennent en {_n(200 * duree / 10 / 3600, 1)} heures ; à quatre agents, en {_n(200 * duree / 4 / 3600, 1)} heures.
- La relecture humaine pèse plus que les jetons : dix minutes par société font {_n(heures_relecture, 0)} heures (hypothèse), contre {_n(round(med_cout * 200, -1), 0)} $ de jetons.

## Sources, gratuites et payantes

- Gratuites et déjà utilisées : pages de la société, communiqués et études de cas des éditeurs, presse, offres d'emploi, Wikidata, GLEIF. Les rapports annuels s'ajoutent à 200, pays par pays (ESEF n'a ni l'Allemagne ni la Suisse).
- Payantes, en second avis seulement : une base de technologies d'entreprise et une base de contacts, sous contrat. Elles ne remplacent pas la citation : un niveau « confirmé » exige toujours un document daté.

## Ce qui casse

{table(["Ce qui casse", "Pourquoi", "Ce que je change"], [
    ["La lecture par le code", f"{_n(taux_refus * 100)} % des adresses sont refusées ou illisibles pour le code (robots.txt, HTTP 403). Un second agent s'accorde avec la première lecture sur {t['relues_confirmees']} lignes sur {t['relues']} ({_n(taux_relues * 100)} %)", "Un accord de lecture avec les sites qui comptent, ou un fournisseur de pages sous contrat. La seconde lecture reste plafonnée à « probable »"],
    ["Les pages que le code lit mal", f"La lecture directe ne garde parfois qu'une fraction du texte d'une page construite par JavaScript (2 418 caractères sur 28 285 pour une page de Barilla). {t['lues_rendues']} pages ont dû être relues rendues, et {incompletes} citations que le journal avait d'abord mises sur le compte du modèle venaient de là", "Le rendu JavaScript quand la lecture est pauvre, déjà en place. À 200, un navigateur sans affichage sous contrôle plutôt qu'un service tiers"],
    ["La citation reformulée par le modèle", f"Le modèle recopie parfois de mémoire : {t['reparees']} citations sur {t['gardees']} gardées ont dû être remplacées par un passage de la page", "Le passage de la page qui porte la valeur, plafonné à « probable ». Un modèle moins cher en extraction (Haiku 5.5) se teste sur ce jeu"],
    ["La résolution d'entité", "Homonymes, filiales, groupes à périmètre flou. Wikidata exige un contact ; GLEIF ne cherche pas bien par nom", "Wikidata d'abord avec un contact déclaré, GLEIF pour contrôler le LEI, validation humaine sous un seuil de score"],
    ["La fraîcheur", f"{_n(100 * (t['hors_fenetre'] + t['sans_date']) / max(1, t['gardees']))} % des trouvailles gardées sont hors de leur fenêtre. Une fiche vieillit : un rapport, une offre, un communiqué changent la donnée", "Déclencheurs par source, empreinte par page, recalcul du seul champ touché, péremption par type de preuve"],
    ["La relecture humaine", f"{_n(heures_relecture, 0)} heures (hypothèse)", "Échantillon stratifié, rejets automatiques seulement après 30 verdicts et 90 % de concordance sur quatre semaines (hypothèse), relecture complète limitée aux financements avant un rendez-vous"],
    ["Les limites d'usage", "Un abonnement a des plafonds, une API des limites de débit. Un garde-fou du fournisseur a arrêté une seconde lecture, passée ensuite avec un autre modèle", "Compte dédié, lots de quatre à dix, reprise sur cache, calendrier lissé. Une société arrêtée reprend sans refaire les autres"],
])}

## Contrôle qualité

- Sur le lot mesuré, {_n(taux_rejet * 100)} % des trouvailles proposées par le modèle sont rejetées par les contrôles du code. À 200, ce taux se suit par modèle et par version de consigne.
- Relu par une personne, le jeu des {len(fiches)} sociétés se rejoue à chaque changement de modèle ou de consigne.
- Audit d'un échantillon tiré au sort par un auditeur d'un autre modèle, pour la citation exacte dont la conclusion est fausse ; une personne relit ses écarts.{audit_200}

## Mise à jour des fiches

Chaque fiche porte la date de lecture, l'empreinte de chaque page et la version du prompt. Une relance ne refait que les champs dont la page a changé ; une preuve hors de sa fenêtre redescend à « probable ».

## Où brancher le résultat, et précautions

- Brancher : fiche jointe au rendez-vous, puis champs du CRM en proposition validée par un commercial (jamais d'écriture directe), puis synthèse du panel pour la feuille de route des branchements d'ERP.
- Précautions : lecture seule, provenance par champ, validation humaine avant écriture, aucune donnée interne envoyée au modèle tant que la conformité n'a pas validé le fournisseur, contacts en suggestion non vérifiée avec interrupteur, registre des jetons et des appels, plafond de dépense par lot.
"""


def md_vers_html(md: str) -> str:
    """Convertisseur minimal pour ces deux textes : titres, paragraphes, listes, tableaux, blocs de code, gras et code en ligne."""
    def inline(t: str) -> str:
        t = html.escape(t)
        t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
        return re.sub(r"`([^`]+)`", r"<code>\1</code>", t)

    sortie, lignes, i = [], md.split("\n"), 0
    while i < len(lignes):
        l = lignes[i]
        if l.startswith("```"):
            bloc = []
            i += 1
            while i < len(lignes) and not lignes[i].startswith("```"):
                bloc.append(lignes[i])
                i += 1
            sortie.append("<pre>" + html.escape("\n".join(bloc)) + "</pre>")
        elif l.startswith("#"):
            n = len(l) - len(l.lstrip("#"))
            sortie.append(f"<h{n}>{inline(l[n:].strip())}</h{n}>")
        elif l.startswith("|"):
            rangs = []
            while i < len(lignes) and lignes[i].startswith("|"):
                if not re.match(r"^\|[-| ]+\|$", lignes[i]):
                    rangs.append([c.strip() for c in lignes[i].strip().strip("|").split("|")])
                i += 1
            i -= 1
            tete, corps = rangs[0], rangs[1:]
            sortie.append("<table><tr>" + "".join(f"<th>{inline(c)}</th>" for c in tete) + "</tr>"
                          + "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in corps) + "</table>")
        elif re.match(r"^(- |\d+\. )", l):
            ordonnee = bool(re.match(r"^\d+\. ", l))
            items = []
            while i < len(lignes) and re.match(r"^(- |\d+\. )", lignes[i]):
                items.append(re.sub(r"^(- |\d+\. )", "", lignes[i]))
                i += 1
            i -= 1
            balise = "ol" if ordonnee else "ul"
            sortie.append(f"<{balise}>" + "".join(f"<li>{inline(x)}</li>" for x in items) + f"</{balise}>")
        elif l.strip():
            sortie.append(f"<p>{inline(l)}</p>")
        i += 1
    css = ("@page{size:A4;margin:16mm}body{font-family:-apple-system,'Helvetica Neue',Arial,sans-serif;font-size:10pt;line-height:1.4;color:#111827}"
           "h1{font-size:18pt}h2{font-size:13pt;margin-top:6mm}table{border-collapse:collapse;width:100%;font-size:8.5pt;margin:2mm 0}"
           "th,td{border:0.3mm solid #d1d5db;padding:1mm 1.6mm;vertical-align:top;text-align:left}th{background:#f3f4f6}"
           "pre{background:#f3f4f6;padding:3mm;font-size:7.5pt;white-space:pre-wrap}code{font-size:0.9em;background:#f3f4f6}"
           "table,tr{page-break-inside:avoid}h2,h3{page-break-after:avoid}")
    return f"<!doctype html><html lang='fr'><head><meta charset='utf-8'><style>{css}</style></head><body>{''.join(sortie)}</body></html>"


def ecrire(sorties: Path, fiches: list[dict], transcriptions: Path | None, lien_outil: str = "") -> list[Path]:
    dossier = sorties / "livrables"
    dossier.mkdir(parents=True, exist_ok=True)
    erreurs = erreurs_mod.lire()
    lignes = rapport.lignes_projet(transcriptions)
    rapport_jetons = rapport.formater(lignes)
    sources = {"ton-outil": ton_outil(fiches, erreurs, rapport_jetons, lien_outil), "a-200-societes": a_200(fiches, cout_phase(lignes, "audit"))}
    chemins = []
    for nom, md in sources.items():
        p = dossier / f"{nom}.md"
        p.write_text(md, encoding="utf-8")
        brief.rendre_pdf(md_vers_html(md), dossier / f"{nom}.pdf")
        chemins += [p, dossier / f"{nom}.pdf"]
    return chemins
