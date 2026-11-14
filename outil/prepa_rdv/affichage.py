"""Ce qu'une cellule doit dire en plus de sa valeur, pour ne pas dire plus que sa page (D21).

L'audit du 14 novembre 2026 a jugé partielles ou fausses 9 cellules sur 33. Huit venaient de deux oublis d'affichage, pas
du modèle : il avait noté l'entité que la page nomme (Tibnor, Fresenius Kabi, Saint-Gobain China) et, dans son
commentaire, que la migration était prévue ou en préparation. La cellule ne gardait que le nom du produit et laissait
croire au groupe entier et à un outil en place. Deux règles le corrigent, dans le brief, la cartographie et l'audit :

- `entite_autre` : l'entité nommée par la page s'affiche quand ce n'est pas la société elle-même (filiale, division, pays) ;
- `en_projet` : pour un ERP, une plateforme d'achats ou un TMS, la cellule dit « migration prévue ou en cours » quand le
  commentaire du modèle le dit.

Ni le niveau ni la synthèse ne changent : la preuve reste la même, la cellule la décrit mieux.
"""
from __future__ import annotations

from .listes import norm
from .verificateur import forme_courte

DEBUT_ENTITE = {"groupe", "group", "the", "le", "la"}
FIN_ENTITE = {"corporation", "corp", "limited", "ltd", "inc", "llc", "gmbh", "plc", "ab", "ag", "sa", "se", "oyj", "spa"}
HORS_ENTITE = {"portal", "portail", "website", "site", "page"}  # « Barilla Vendor Portal » nomme un portail, pas une filiale
CHAMPS_SYSTEME = {"erp", "achats", "tms"}
MARQUES_PROJET = ("prévu", "préparer", "en préparation", "visé", "en cours", "pas comme achevée", "bascule achevée")
MARQUES_EN_PLACE = ("usage depuis", "utilisé depuis", "utilise depuis", "en place depuis", "existant")  # le système qu'on quitte est en place


def _court(nom: str) -> str:
    mots = norm(forme_courte(nom)).split()
    while mots and mots[0] in DEBUT_ENTITE:
        mots.pop(0)
    while mots and mots[-1] in FIN_ENTITE:
        mots.pop()
    return " ".join(mots)


def entite_autre(nommee: str | None, entite: dict) -> str | None:
    """L'entité que la page nomme quand ce n'est pas la société elle-même ; None pour la société, sa forme courte ou un portail."""
    if not nommee:
        return None
    n = _court(nommee)
    noms = [_court(x) for x in (entite.get("nom_saisi"), entite.get("nom_retenu"), *(entite.get("alias") or [])) if x]
    if not n or set(n.split()) & HORS_ENTITE:
        return None
    if any(n == m or m.startswith(n + " ") for m in noms):  # « Stadler » pour « Stadler Rail » : c'est la société
        return None  # « Moët Hennessy », au milieu de « LVMH Moët Hennessy Louis Vuitton », reste une division
    return nommee


def en_projet(t: dict) -> bool:
    """Le commentaire du modèle dit que le système est prévu, en préparation ou en cours de migration."""
    p = (t.get("precision") or "").lower()
    return t.get("champ") in CHAMPS_SYSTEME and any(m in p for m in MARQUES_PROJET) and not any(m in p for m in MARQUES_EN_PLACE)


def marques(t: dict | None, entite: dict) -> str:
    """Le complément de la cellule : entité nommée, migration prévue ou en cours."""
    if not t:
        return ""
    m = ""
    autre = entite_autre(t.get("entite_nommee"), entite)
    if autre:
        m += f" (entité nommée : {autre})"
    if en_projet(t):
        m += " (migration prévue ou en cours, d'après la page)"
    return m
