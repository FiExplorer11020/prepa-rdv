"""La fiche : source unique du brief et des tableurs.

Elle regroupe les trouvailles vérifiées d'une société, la synthèse par champ, les questions et l'angle.
L'angle et les questions viennent de tables : le modèle n'écrit que dans les trouvailles.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from .confiance import SyntheseChamp, synthese_champ
from .listes import nom_court
from .resolveur import Entite
from .schema import CHAMPS_BRIEF, Champ, LIBELLES_CHAMP, Niveau, StatutValeur, Trouvaille

QUESTIONS_TYPES: dict[Champ, str] = {
    Champ.DIRECTION_FINANCIERE: "Qui décide aujourd'hui du financement du poste clients et fournisseurs, et à quel niveau du groupe ?",
    Champ.ERP: "Sur quel ERP tournent les entités du groupe, et une migration est-elle prévue sur les flux de facturation ?",
    Champ.ACHATS: "Quelle plateforme porte les commandes et les factures fournisseurs, et sur quels périmètres ?",
    Champ.TMS: "Quel outil de trésorerie centralise les positions de trésorerie et les paiements ?",
    Champ.FINANCEMENT: "Existe-t-il des programmes de financement des créances ou des dettes fournisseurs, et avec quelles banques ?",
}
QUESTIONS_COMPLEMENT = (
    "Où se décident les arbitrages entre financement bancaire et financement des fournisseurs ?",
    "Un projet de système d'information financier est-il prévu, et sur quel calendrier ?",
    "Des flux de paiement fournisseurs passent-ils déjà par un portail en ligne ?",
)

# Une question ne présuppose aucun fait que la fiche n'établit pas : pas de « migration en cours », pas de « projet en cours ».
# Pistes d'angle, par cas (cahier des charges, section 7). Le code choisit la piste.
PISTES = {
    "pile_sans_financement": "Financer les factures fournisseurs depuis l'outil déjà en place",
    "affacturage_declare": "Étendre ou comparer le programme existant, en l'intégrant à l'ERP",
    "inverse_declare": "Ouvrir la discussion sur les fournisseurs de second rang et sur l'intégration",
    "rien": "Ouvrir la discussion par les questions",
}


def _valeurs(s: SyntheseChamp) -> str:
    return ", ".join(
        (v.valeur if v.valeur != "autre" else nom_court(v.precision or "autre"))
        + (" (absence déclarée)" if v.statut == StatutValeur.ABSENCE_DECLAREE else "")
        for v in s.valeurs[:3])


def piste(syntheses: dict[Champ, SyntheseChamp]) -> str:
    fin = syntheses.get(Champ.FINANCEMENT)
    noms = {v.valeur for v in fin.valeurs if v.statut == StatutValeur.PRESENT} if fin else set()
    if any(n.startswith("Affacturage inversé") or n == "Escompte dynamique" for n in noms):
        return "inverse_declare"
    if any(n.startswith("Affacturage") or n.startswith("Titrisation") for n in noms):
        return "affacturage_declare"
    pile = [syntheses.get(c) for c in (Champ.ERP, Champ.ACHATS)]
    if all(s and s.niveau in (Niveau.CONFIRME, Niveau.PROBABLE) for s in pile):
        return "pile_sans_financement"
    return "rien"


def questions(syntheses: dict[Champ, SyntheseChamp], maximum: int = 5) -> list[str]:
    """Une question par champ non trouvé ou contredit, puis des questions de complément jusqu'à trois."""
    qs = [QUESTIONS_TYPES[c] for c in CHAMPS_BRIEF if syntheses[c].niveau in (Niveau.NON_TROUVE, Niveau.CONTRADICTION)]
    for extra in QUESTIONS_COMPLEMENT:
        if len(qs) >= 3:
            break
        qs.append(extra)
    return qs[:maximum]


def angle(syntheses: dict[Champ, SyntheseChamp], societe: str) -> list[str]:
    """Trois phrases, marquées comme hypothèse, qui citent des faits de la fiche."""
    cle = piste(syntheses)
    faits = []
    for c in (Champ.ERP, Champ.ACHATS, Champ.TMS, Champ.FINANCEMENT):
        s = syntheses[c]
        if s.valeurs and s.niveau in (Niveau.CONFIRME, Niveau.PROBABLE, Niveau.ABSENCE_DECLAREE):
            faits.append(f"{LIBELLES_CHAMP[c]} : {_valeurs(s)} ({s.niveau.value})")
    # Une phrase par fait : la phrase la plus longue d'un brief ne dépasse pas 30 mots (contrôle de langue).
    appui = " ".join(f"{f}." for f in faits[:2]) if faits else "La fiche n'établit pas encore de fait sur la pile ni sur les financements."
    return [
        f"Hypothèse : {PISTES[cle]}.",
        f"Elle s'appuie sur ces faits de la fiche. {appui}",
        "Les questions ci-dessous servent à confirmer ou à écarter cette piste en début de rendez-vous.",
    ]


def construire(
    entite: Entite,
    trouvailles: list[Trouvaille],
    *,
    run_id: str,
    version_outil: str,
    empreinte_prompt: str,
    modele: str,
    plan_requetes: dict[str, list[str]],
    remarques: list[str],
    champs_sans_resultat: list[str],
    jetons: dict[str, Any],
    duree_s: float,
) -> dict[str, Any]:
    syntheses = {c: synthese_champ(c, trouvailles) for c in Champ}
    sources = sorted({t.url for t in trouvailles if t.niveau != Niveau.NON_TROUVE})
    return {
        "societe": entite.nom_saisi,
        "run_id": run_id,
        "date_fiche": datetime.now(timezone.utc).date().isoformat(),
        "version_outil": version_outil,
        "modele": modele,
        "empreinte_prompt": empreinte_prompt,
        "entite": asdict(entite),
        "plan_requetes": plan_requetes,
        "trouvailles": [t.model_dump(mode="json") for t in trouvailles],
        "synthese": {
            c.value: {
                "niveau": s.niveau.value,
                "contradiction": s.contradiction,
                "valeurs": [{"valeur": v.valeur, "precision": v.precision, "statut": v.statut.value, "niveau": v.niveau.value, "ids": v.ids}
                            for v in s.valeurs],
            } for c, s in syntheses.items()
        },
        "nombre_sources": len(sources),
        "questions": questions(syntheses),
        "angle": angle(syntheses, entite.nom_saisi),
        "remarques_modele": remarques,
        "champs_sans_resultat_modele": champs_sans_resultat,
        "jetons": jetons,
        "duree_s": round(duree_s, 1),
    }
