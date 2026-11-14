"""L'agent : le modèle cherche, lit et remplit un schéma fermé. Le code juge ensuite.

Le prompt est versionné par son empreinte : une fiche dit avec quel prompt elle a été écrite.
Le plan de requêtes est fixe par champ, en anglais et dans la langue du siège, et il est écrit au journal.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from pydantic import ValidationError

from .listes import ACHATS, ERP, FINANCEMENT, TMS
from .modele import ClaudeCLI, ErreurModele, Reponse
from .resolveur import Entite
from .schema import SortieModele, schema_inline

LANGUES_SIEGE = {
    "sweden": ("sv", "svenska"), "finland": ("fi", "suomi"), "germany": ("de", "Deutsch"),
    "austria": ("de", "Deutsch"), "switzerland": ("de", "Deutsch"), "france": ("fr", "français"), "italy": ("it", "italiano"),
}

SYSTEME = """Tu prépares un rendez-vous avec la direction financière d'une grande entreprise, à partir d'informations publiques uniquement.

Ton travail : trouver, pour la société indiquée, quatre informations et leurs preuves.
1. ERP en place (liste fermée ci-dessous).
2. Plateforme d'achats (liste fermée).
3. TMS et trésorerie (liste fermée).
4. Produits de financement court terme déjà en place : affacturage, titrisation de créances, supply chain finance, escompte dynamique, billets de trésorerie, ligne de crédit renouvelable, crédit documentaire (liste fermée).
Plus : le directeur financier ou le trésorier nommé par la société, et un signal récent sur la finance ou les systèmes d'information.

Règles de preuve, sans exception :
- Chaque trouvaille porte une citation recopiée mot pour mot dans la page, de 25 mots au plus, et l'adresse complète de cette page.
- La citation doit nommer la société ou sa filiale, ou la page doit le faire juste à côté. Écris le nom tel que la page l'écrit dans entite_nommee.
- Ne déduis rien. Un ERP déduit du secteur, d'un homonyme ou d'une filiale d'un autre groupe n'est pas une trouvaille. Une offre d'emploi est un signal, pas une preuve de déploiement : donne-la telle quelle.
- Si un document de la société dit qu'elle n'a pas le produit, écris la trouvaille avec statut_valeur absence_declaree et sa citation.
- Si tu ne trouves rien pour un champ après avoir cherché, ne l'invente pas : liste-le dans champs_sans_resultat.
- Date : celle que la page affiche, telle quelle ; null si la page n'en porte pas.
- Pour les valeurs des champs à liste fermée, choisis une valeur de la liste. Si le produit n'y est pas, écris « autre » et donne son nom exact dans precision.
- Une citation étrangère se traduit en français dans traduction_fr. La citation reste dans la langue de la source.
- N'écris aucun commentaire en dehors du schéma. Tu ne notes pas ta propre confiance : le code le fait.

Moyens : la recherche web et la lecture de pages. Au plus 25 recherches et 20 pages lues. Va aux documents de la société d'abord (rapports annuels, présentations, pages de relations investisseurs), puis aux communiqués et études de cas des éditeurs et intégrateurs, puis à la presse spécialisée, enfin aux offres d'emploi.

Listes fermées.
ERP : {erp}.
Plateforme d'achats : {achats}.
TMS et trésorerie : {tms}.
Financement court terme : {financement}.
"""


def systeme() -> str:
    return SYSTEME.format(erp=", ".join(ERP), achats=", ".join(ACHATS), tms=", ".join(TMS), financement=", ".join(FINANCEMENT))


def plan_de_requetes(entite: Entite) -> dict[str, list[str]]:
    """Requêtes fixes par champ, en anglais et dans la langue du siège. Écrit au journal avant la recherche."""
    n = entite.nom_retenu or entite.nom_saisi
    court = entite.nom_saisi
    pays = (entite.pays or "").lower()
    code, _ = LANGUES_SIEGE.get(pays, ("en", "English"))
    locales = {
        "de": (f"{court} Finanzvorstand", f"{court} Treasury Leiter", f"{court} Factoring Forderungen Geschäftsbericht"),
        "fr": (f"{court} directeur financier", f"{court} trésorerie groupe", f"{court} affacturage titrisation créances document d'enregistrement universel"),
        "sv": (f"{court} CFO ekonomichef", f"{court} factoring kundfordringar årsredovisning"),
        "fi": (f"{court} talousjohtaja CFO", f"{court} factoring myyntisaamiset vuosikertomus"),
        "it": (f"{court} direttore finanziario CFO", f"{court} factoring cessione crediti bilancio"),
        "en": (),
    }[code]
    return {
        "direction_financiere": [f"{court} Chief Financial Officer", f"{court} Group Treasurer", f"{court} investor relations management team", *locales[:2]],
        "erp": [f"{court} SAP S/4HANA", f"{court} ERP implementation", f"{court} Oracle OR Dynamics OR Workday ERP", f"{court} annual report SAP"],
        "achats": [f"{court} SAP Ariba supplier", f"{court} Coupa OR Jaggaer OR Ivalua", f"{court} supplier portal procurement platform"],
        "tms": [f"{court} treasury management system", f"{court} Kyriba", f"{court} SAP Treasury"],
        "financement": [f"{court} supply chain finance", f"{court} reverse factoring", f"{court} receivables securitisation programme",
                        f"{court} factoring programme", f"{court} annual report supplier finance arrangements", *locales[2:]],
        "signal": [f"{court} finance transformation treasury 2026", f"{court} ERP migration"],
    }


def prompt_societe(entite: Entite, plan: dict[str, list[str]]) -> str:
    lignes = [
        f"Société : {entite.nom_saisi}" + (f" (nom légal retenu : {entite.nom_retenu})" if entite.nom_retenu else ""),
        f"Pays du siège : {entite.pays or 'non précisé'}. Statut : {entite.statut or 'non précisé'}.",
        f"Site officiel : {entite.site or 'non précisé'}. Domaines de la société : {', '.join(entite.domaines) or 'non précisés'}.",
    ]
    if entite.a_confirmer:
        lignes.append(f"Attention, identité à confirmer : {entite.a_confirmer}.")
    lignes += ["", "Plan de requêtes (suis-le, complète-le si besoin) :"]
    for champ, requetes in plan.items():
        lignes.append(f"- {champ} : " + " | ".join(requetes))
    lignes += ["", "Réponds uniquement par l'objet JSON du schéma."]
    return "\n".join(lignes)


def empreinte_prompt() -> str:
    return hashlib.sha256((systeme() + json.dumps(schema_inline(SortieModele), sort_keys=True)).encode()).hexdigest()[:12]


@dataclass
class Demande:
    """Tout ce qu'un agent doit recevoir pour une société : consignes, demande, schéma, plan de requêtes."""

    societe: str
    systeme: str
    prompt: str
    schema: dict
    plan: dict[str, list[str]]
    empreinte_prompt: str


def preparer(entite: Entite) -> Demande:
    plan = plan_de_requetes(entite)
    return Demande(entite.nom_saisi, systeme(), prompt_societe(entite, plan), schema_inline(SortieModele), plan, empreinte_prompt())


@dataclass
class ResultatAgent:
    sortie: SortieModele
    reponses: list[Reponse]
    plan: dict[str, list[str]]
    prompt: str


def lancer(entite: Entite, modele: ClaudeCLI, phase: str = "run") -> ResultatAgent:
    """Un appel agent (recherche et lecture comprises). Un seul nouvel essai si la sortie ne valide pas le schéma."""
    plan = plan_de_requetes(entite)
    prompt = prompt_societe(entite, plan)
    schema = schema_inline(SortieModele)
    outils = ("WebSearch", "WebFetch")
    reponses: list[Reponse] = []
    erreur_precedente = ""
    for tentative in (1, 2):
        corps = prompt if tentative == 1 else (
            f"{prompt}\n\nTa réponse précédente ne respecte pas le schéma : {erreur_precedente}\nCorrige et réponds de nouveau.")
        r = modele.appeler(corps, schema=schema, systeme=systeme(), outils=outils, phase=phase,
                           societe=entite.nom_saisi, note=f"agent, tentative {tentative}")
        reponses.append(r)
        try:
            return ResultatAgent(SortieModele.model_validate(r.donnees), reponses, plan, prompt)
        except ValidationError as e:
            erreur_precedente = str(e)[:400]
    raise ErreurModele(f"Sortie hors schéma après deux essais : {erreur_precedente}")
