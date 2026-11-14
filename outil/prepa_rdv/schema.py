"""Schéma fermé des trouvailles et de la fiche.

Le modèle remplit `SortieModele`. Le code ajoute les vérifications et le niveau de confiance :
le modèle ne note jamais sa propre confiance.
"""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

MAX_MOTS_CITATION = 25


class Champ(StrEnum):
    IDENTITE = "identite"
    DIRECTION_FINANCIERE = "direction_financiere"
    ERP = "erp"
    ACHATS = "achats"
    TMS = "tms"
    FINANCEMENT = "financement"
    SIGNAL = "signal"


# Les cinq lignes du brief, dans l'ordre d'affichage.
CHAMPS_BRIEF = (Champ.DIRECTION_FINANCIERE, Champ.ERP, Champ.ACHATS, Champ.TMS, Champ.FINANCEMENT)
# Les champs dont la valeur vient d'une liste fermée.
CHAMPS_LISTE_FERMEE = (Champ.ERP, Champ.ACHATS, Champ.TMS, Champ.FINANCEMENT)

LIBELLES_CHAMP = {
    Champ.IDENTITE: "Identité",
    Champ.DIRECTION_FINANCIERE: "Direction financière",
    Champ.ERP: "ERP",
    Champ.ACHATS: "Plateforme d'achats",
    Champ.TMS: "TMS et trésorerie",
    Champ.FINANCEMENT: "Financements court terme",
    Champ.SIGNAL: "Signal récent",
}


class StatutValeur(StrEnum):
    PRESENT = "present"
    ABSENCE_DECLAREE = "absence_declaree"


class TypeSource(StrEnum):
    P1 = "P1"  # document de la société
    P2 = "P2"  # document d'un tiers qui nomme la société : éditeur, intégrateur, association
    P3 = "P3"  # presse ou agence de notation
    P4 = "P4"  # signal indirect : offre d'emploi, intervention en conférence
    P5 = "P5"  # base payante : second avis seulement


class Niveau(StrEnum):
    CONFIRME = "confirmé"
    PROBABLE = "probable"
    NON_TROUVE = "non trouvé"
    ABSENCE_DECLAREE = "absence déclarée"
    CONTRADICTION = "contradiction"


class TrouvailleBrute(BaseModel):
    """Ce que le modèle écrit pour une information. Aucun niveau de confiance."""

    model_config = ConfigDict(extra="forbid")

    champ: Champ
    valeur: str = Field(description="Pour erp, achats, tms et financement : une valeur de la liste fermée, ou « autre ».")
    precision: str | None = Field(description="Nom exact du produit quand la valeur est « autre », ou détail utile. Sinon null.")
    statut_valeur: StatutValeur = Field(description="present, ou absence_declaree si un document de la société dit qu'elle n'a pas le produit.")
    citation: str = Field(description="Phrase recopiée mot pour mot dans la source, 25 mots au plus.")
    citation_langue: str = Field(description="Code de langue de la citation : en, de, fr, sv, fi, it.")
    traduction_fr: str | None = Field(description="Traduction française de la citation si elle n'est pas en français. Sinon null.")
    url: str = Field(description="Adresse complète de la page qui porte la citation.")
    entite_nommee: str = Field(description="Nom de la société ou de la filiale tel que la page le écrit, à côté de la citation.")
    type_source: TypeSource = Field(description="Type de source proposé. Le code le recalcule d'après le domaine.")
    date_source: str | None = Field(description="Date de la page telle qu'elle y est écrite (AAAA, AAAA-MM ou AAAA-MM-JJ). Null si absente.")


class SortieModele(BaseModel):
    """Réponse complète du modèle pour une société."""

    model_config = ConfigDict(extra="forbid")

    trouvailles: list[TrouvailleBrute]
    champs_sans_resultat: list[Champ] = Field(description="Champs pour lesquels aucune source n'a été trouvée.")
    remarques: list[str] = Field(description="Doutes, homonymes, filiales, limites rencontrées. Liste vide si rien.")


class Verifs(BaseModel):
    """Résultat des contrôles du code sur une trouvaille."""

    mode_verification: str = "code"  # code : le code a relu la page. seconde_lecture : un second agent l'a relue à l'aveugle.
    # citation_remplacee : la citation du modèle n'était pas dans la page ; le code a gardé un passage de la page qui porte la valeur.
    refus_du_code: str | None = None  # seconde lecture : ce que le code avait rencontré (robots.txt, HTTP 403...) avant qu'un second agent relise la page
    lu_via: str = "direct"  # direct : page lue par le code. jina : rendue par JavaScript quand la lecture directe était pauvre.
    citation_du_modele: str | None = None
    score_avant_reparation: float | None = None
    citation_trouvee: bool = False
    score_similarite: float = 0.0
    citation_mots: int = 0
    citation_longueur_ok: bool = False
    adresse_ok: bool = False
    statut_http: int | None = None
    domaine: str | None = None
    type_source_code: TypeSource | None = None
    type_corrige: bool = False
    entite: str = "absente"  # groupe | filiale | absente
    date_page: str | None = None
    date_retenue: str | None = None
    page_vivante: bool = False  # page de la société sans date propre (contact, équipe) : elle vaut à la date de lecture
    sans_date: bool = False
    age_mois: int | None = None
    dans_fenetre: bool | None = None
    page_numero: int | None = None
    erreurs: list[str] = Field(default_factory=list)


class Trouvaille(TrouvailleBrute):
    """Une trouvaille vérifiée, prête pour la fiche."""

    id: str
    societe: str
    valeur_normalisee: str
    date_lecture: datetime
    empreinte_source: str | None = None
    modele: str
    version_outil: str
    empreinte_prompt: str
    verifs: Verifs = Field(default_factory=Verifs)
    niveau: Niveau = Niveau.NON_TROUVE


def schema_inline(modele: type[BaseModel]) -> dict[str, Any]:
    """Schéma JSON sans `$ref` ni `$defs`, pour les accès au modèle qui n'en veulent pas."""
    schema = modele.model_json_schema()
    defs = schema.pop("$defs", {})

    def resoudre(noeud: Any) -> Any:
        if isinstance(noeud, dict):
            if "$ref" in noeud:
                nom = noeud["$ref"].split("/")[-1]
                return resoudre(defs[nom])
            return {k: resoudre(v) for k, v in noeud.items() if k != "title"}
        if isinstance(noeud, list):
            return [resoudre(x) for x in noeud]
        return noeud

    return resoudre(schema)
