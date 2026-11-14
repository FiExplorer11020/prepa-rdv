"""Audit d'un échantillon tiré au sort, jugé par un sous-agent auditeur (D20).

Le code vérifie qu'une citation figure sur sa page, que la page nomme la société et qu'elle tient dans sa fenêtre. Il ne
voit pas la citation exacte dont la conclusion est fausse : une filiale prise pour le groupe, un outil évalué pris pour un
outil en place, une phrase qui ne dit pas ce que l'outil en tire. L'audit mesure cette erreur sur 36 cellules de la
cartographie, tirées au sort avec une graine fixe.

Le circuit est celui des agents de recherche (D13) :
1. `ecrire_demandes` répartit les cellules en lots et écrit, par lot, `demande-N.md` et `demande-N.json`. L'auditeur
   reçoit la société, le champ, la valeur, la citation et le lien, ce qu'une personne voit dans la feuille « Audit ».
   Il ne reçoit ni le niveau de confiance ni les contrôles du code.
2. Un sous-agent d'un autre modèle que les agents de recherche ouvre chaque lien, juge la cellule et écrit `sortie-N.json`.
3. `recevoir` valide la réponse contre un schéma fermé, exige un jugement par cellule du lot, écrit `verdicts.json` et
   enregistre l'agent, pour que ses jetons se comptent dans la phase « audit ».
4. La feuille « Audit » de la cartographie et « Ton outil » reprennent les verdicts.

Un modèle qui en juge un autre ne vaut pas une relecture par une personne : les livrables le disent.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from . import sous_agents, tableur
from .jetons import dossier_sorties
from .modele import ErreurModele, _extraire_json
from .schema import schema_inline

DOSSIER = "audit"
LOTS = 3
MODELE_AUDITEUR = "Opus 5.5"
VERDICTS = ("juste", "partiel", "faux", "invérifiable")
TIRAGES = ("premier", "relance", "second")
GRAINE_SECONDE = 2027
ECARTS = ("filiale ou division", "précision non soutenue", "autre société", "projet ou évaluation", "autre produit",
          "extrapolation", "personne remplacée", "page sans la valeur")


class Jugement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="Identifiant de la cellule, recopié de la demande.")
    page_ouverte: bool = Field(description="True si tu as pu ouvrir le lien et lire la page.")
    citation_presente: bool | None = Field(description="True si la citation de la cellule figure sur la page, à la ponctuation près. Null si la page n'a pas pu être lue.")
    verdict: Literal["juste", "partiel", "faux", "invérifiable"] = Field(description="Voir les définitions de la demande.")
    ecart: Literal["filiale ou division", "précision non soutenue", "autre société", "projet ou évaluation", "autre produit",
                   "extrapolation", "personne remplacée", "page sans la valeur"] | None = Field(
        description="Pour un verdict partiel ou faux : la nature de l'écart. Null pour juste et invérifiable.")
    raison: str = Field(description="Une phrase de 30 mots au plus : ce que la page établit, ou n'établit pas.")
    passage: str | None = Field(description="Le passage de la page qui fonde le verdict, recopié mot pour mot, 15 mots au plus. Null si aucun.")


class SortieAudit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    jugements: list[Jugement]


def dossier(sorties: Path | None = None) -> Path:
    return (sorties or dossier_sorties()) / DOSSIER


def lots(cellules: list[dict], n: int = LOTS) -> list[list[dict]]:
    """Lots de tailles égales, dans l'ordre du tirage."""
    taille = max(1, -(-len(cellules) // n))
    return [cellules[i:i + taille] for i in range(0, len(cellules), taille)]


def _vue(c: dict) -> dict[str, str]:
    """Ce que l'auditeur reçoit d'une cellule : ni le niveau, ni les contrôles du code."""
    return {k: c[k] for k in ("id", "societe", "champ", "valeur", "citation", "url")}


def _ligne(c: dict) -> str:
    return (f"- id `{c['id']}`\n  Société : {c['societe']}\n  Champ : {c['champ']}\n  Valeur : {c['valeur']}\n"
            f"  Citation : « {c['citation']} »\n  Lien : {c['url']}")


def texte_demande(k: int, lot: list[dict], total: int, sortie: Path) -> str:
    schema = json.dumps(schema_inline(SortieAudit), ensure_ascii=False, indent=1)
    return f"""# Audit, lot {k} : {len(lot)} cellules sur {total}

Tu es l'auditeur d'un outil qui prépare des rendez-vous avec la direction financière de grandes sociétés. L'outil a rempli
une cartographie depuis des pages web publiques. Chaque cellule ci-dessous porte une valeur, la citation sur laquelle
l'outil la fonde et le lien de la page. Pour chaque cellule, dis si la page soutient la valeur pour la société. Tu n'as pas
produit ces cellules et tu ne connais pas le niveau de confiance que l'outil leur a donné.

Moyens autorisés : WebFetch, et Write pour le seul fichier de réponse. N'utilise ni WebSearch, ni le skill agent-reach, ni
Firecrawl, ni LinkedIn, ni aucun serveur MCP. Ne modifie aucun autre fichier.

## Méthode, pour chaque cellule

1. Ouvre le lien avec WebFetch. Demande si la page dit, pour la société, ce que dit la valeur, si la citation y figure, et
   fais recopier la phrase qui tranche. Un lien par cellule, le sien : ne cherche pas ailleurs.
2. Juge d'après la page seule, sans ta mémoire ni une autre source.
3. Écris le verdict, l'écart s'il y en a un, une raison d'une phrase et le passage.

## Ce que veut dire chaque champ

- ERP : le progiciel de gestion intégré que la société utilise ou déploie.
- Plateforme d'achats : l'outil des achats (sourcing, achat à paiement, gestion des fournisseurs) que la société utilise.
- TMS et trésorerie : le système de gestion de la trésorerie que la société utilise.
- Financements court terme : un financement à moins d'un an ou une ligne de liquidité au nom de la société (billets de
  trésorerie, crédit renouvelable, affacturage, financement de la chaîne fournisseurs).
- Direction financière : la personne qui tient la fonction finance nommée dans la valeur.
- Signal récent : un événement que la page rapporte pour la société.

## Les verdicts

- juste : la page dit ce que dit la valeur, pour la société ou pour le groupe qu'elle forme.
- partiel : la page ne soutient qu'une partie de la valeur. Elle parle d'une filiale, d'une division ou d'un pays du groupe,
  pas du groupe ; ou la valeur ajoute une précision que la page ne donne pas.
- faux : la page ne soutient pas la valeur. Autre société, outil seulement évalué ou abandonné, autre produit, conclusion
  qui dépasse le texte, personne qui n'occupe plus la fonction d'après la page elle-même.
- invérifiable : la page ne s'ouvre pas, ou son contenu ne permet pas de trancher.

Deux conventions de l'outil. Une offre d'emploi de la société qui demande la pratique d'un outil pour un poste chez elle
vaut usage de l'outil. Une étude de cas d'un éditeur ou d'un intégrateur qui nomme la société comme cliente vaut usage.

L'écart se choisit dans la liste du schéma : pour un verdict partiel ou faux, il est obligatoire ; pour juste et
invérifiable, il est null. Une page qui ne s'ouvre pas donne `page_ouverte` false et le verdict invérifiable.

## Cellules du lot

{chr(10).join(_ligne(c) for c in lot)}

## Réponse attendue

Écris dans le fichier `{sortie}` un seul objet JSON, sans texte autour, conforme à ce schéma, avec un jugement par cellule
du lot et un seul. Mets null quand il n'y a pas de valeur. Réponds ensuite par le seul mot OK.

```json
{schema}
```
"""


def _ecrire_lot(d: Path, k: int, lot: list[dict], total: int, tirage: str) -> Path:
    sortie = (d / f"sortie-{k}.json").resolve()
    chemin = d / f"demande-{k}.md"
    chemin.write_text(texte_demande(k, lot, total, sortie), encoding="utf-8")
    (d / f"demande-{k}.json").write_text(json.dumps({"lot": k, "tirage": tirage, "modele": MODELE_AUDITEUR, "cellules": [_vue(c) for c in lot],
                                                     "sortie": str(sortie)}, ensure_ascii=False, indent=1), encoding="utf-8")
    return chemin


def ecrire_demandes(fiches: list[dict], n: int = LOTS, sorties: Path | None = None) -> list[Path]:
    """Une demande par lot. Le tirage est celui de la feuille « Audit » (graine fixe), dans le même ordre."""
    d = dossier(sorties)
    d.mkdir(parents=True, exist_ok=True)
    cellules = tableur.echantillon_audit(fiches)
    return [_ecrire_lot(d, k, lot, len(cellules), "premier") for k, lot in enumerate(lots(cellules, n), start=1)]


def ecrire_second(fiches: list[dict], n: int = 12, graine: int = GRAINE_SECONDE, sorties: Path | None = None) -> list[Path]:
    """Après une correction par règle (porte G4) : les cellules partielles ou fausses du premier tirage, rejugées telles que
    l'outil les affiche désormais, et un second tirage de `n` cellules que le premier n'a pas pris."""
    d = dossier(sorties)
    premier = verdicts(sorties, "premier")
    toutes = {c["id"]: c for c in tableur.cellules_audit(fiches)}
    a_rejuger = [toutes[i] for i, j in premier.items() if j["verdict"] in ("partiel", "faux") and i in toutes]
    nouvelles = tableur.echantillon_audit(fiches, n=n, graine=graine, exclure=set(premier))
    k = max((int(p.stem.split("-")[1]) for p in d.glob("demande-*.json")), default=0)
    return [_ecrire_lot(d, k + 1, a_rejuger, len(a_rejuger), "relance"), _ecrire_lot(d, k + 2, nouvelles, len(nouvelles), "second")]


def lire_sortie(chemin: Path) -> SortieAudit:
    if not chemin.exists():
        raise ErreurModele(f"Pas de réponse : {chemin} n'existe pas")
    try:
        return SortieAudit.model_validate(_extraire_json(chemin.read_text(encoding="utf-8")))
    except json.JSONDecodeError as e:
        raise ErreurModele(f"Réponse sans JSON valide : {e}") from e
    except ValidationError as e:
        raise ErreurModele(f"Réponse hors schéma : {str(e)[:600]}") from e


def controler(sortie: SortieAudit, attendus: list[str]) -> list[str]:
    """Ce qui empêche de garder la réponse : une cellule oubliée, en double ou inconnue, un verdict incohérent."""
    vus = Counter(j.id for j in sortie.jugements)
    problemes = [f"cellule sans jugement : {i}" for i in attendus if i not in vus]
    problemes += [f"cellule jugée {n} fois : {i}" for i, n in vus.items() if n > 1]
    problemes += [f"cellule hors du lot : {i}" for i in vus if i not in attendus]
    for j in sortie.jugements:
        if j.verdict in ("partiel", "faux") and not j.ecart:
            problemes.append(f"{j.id} : verdict {j.verdict} sans écart")
        if j.verdict in ("juste", "invérifiable") and j.ecart:
            problemes.append(f"{j.id} : verdict {j.verdict} avec un écart")
        if not j.page_ouverte and j.verdict != "invérifiable":
            problemes.append(f"{j.id} : page fermée mais verdict {j.verdict}")
    return problemes


def _lot(d: Path, k: int) -> tuple[dict, SortieAudit]:
    demande = json.loads((d / f"demande-{k}.json").read_text(encoding="utf-8"))
    sortie = lire_sortie(d / f"sortie-{k}.json")
    problemes = controler(sortie, [c["id"] for c in demande["cellules"]])
    if problemes:
        raise ErreurModele("; ".join(problemes))
    return demande, sortie


def verdicts(sorties: Path | None = None, tirage: str = "premier") -> dict[str, dict[str, Any]]:
    """Les jugements des lots reçus et valides d'un tirage, par identifiant de cellule. Un lot refusé n'en donne aucun.

    Tirages : « premier » (les 36 cellules de la feuille), « relance » (ses cellules partielles ou fausses, rejugées après une
    correction par règle), « second » (un nouvel échantillon)."""
    d = dossier(sorties)
    out: dict[str, dict[str, Any]] = {}
    for p in sorted(d.glob("demande-*.json"), key=lambda x: int(x.stem.split("-")[1])):
        k = int(p.stem.split("-")[1])
        if json.loads(p.read_text(encoding="utf-8")).get("tirage", "premier") != tirage:
            continue
        try:
            demande, sortie = _lot(d, k)
        except (ErreurModele, FileNotFoundError):
            continue
        vues = {c["id"]: c for c in demande["cellules"]}
        for j in sortie.jugements:
            out[j.id] = {**vues[j.id], **j.model_dump(), "lot": k}
    return out


def resume(jugements: Iterable[dict[str, Any]]) -> dict[str, Any]:
    js = list(jugements)
    compte = Counter(j["verdict"] for j in js)
    verifiables = sum(compte[v] for v in ("juste", "partiel", "faux"))
    return {"cellules": len(js), **{v: compte[v] for v in VERDICTS}, "verifiables": verifiables,
            "citation_absente": sum(1 for j in js if j["citation_presente"] is False),
            "ecarts": dict(Counter(j["ecart"] for j in js if j["ecart"]))}


def recevoir(k: int, agent_id: str | None = None, phase: str = "audit", sorties: Path | None = None) -> dict[str, Any]:
    """Valide le lot `k`, réécrit `verdicts.json` avec tous les lots valides et enregistre l'agent."""
    d = dossier(sorties)
    demande, sortie = _lot(d, k)
    tirages = {t: verdicts(sorties, t) for t in TIRAGES}
    (d / "verdicts.json").write_text(json.dumps({"modele": demande["modele"], **{t: {"resume": resume(v.values()), "jugements": v}
                                                                                for t, v in tirages.items() if v}},
                                                ensure_ascii=False, indent=1), encoding="utf-8")
    if agent_id:
        # Pas de société : l'audit porte sur tout le lot, ses jetons vont à la phase « audit » et pas au tableau par société.
        sous_agents.enregistrer_agent(agent_id, "", phase, role=f"audit, lot {k}")
    return {"lot": k, **resume(j.model_dump() for j in sortie.jugements)}
