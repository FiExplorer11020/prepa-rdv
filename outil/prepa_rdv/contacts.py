"""Contacts en suggestion non vérifiée (cahier des charges, section 10).

Ce que le module fait :
- il relève les adresses générales que la société publie sur ses propres pages déjà lues (relations investisseurs, presse) ;
- il propose une adresse nominative pour le directeur financier, seulement si la société le nomme dans un document de moins
  de 12 mois, si au moins deux adresses nominatives du même domaine sont publiées avec le même motif, et si le domaine a un
  enregistrement MX. Elle est marquée « déduite, non vérifiée ».

Ce qu'il ne fait pas : pas de sonde SMTP, pas d'envoi, pas de base tierce, pas de ligne directe, aucun autre dirigeant.
Un interrupteur (`--sans-contacts`) retire tout le bloc.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .lecteur import domaine_racine
from .listes import norm
from .resolveur import Entite
from .schema import Champ, Niveau

COURRIEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._%+-]*@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
GENERIQUES = ("investor", "investors", "ir", "press", "media", "presse", "communications", "info", "contact", "kommunikation", "prensa")
# Mots qui ressemblent à un prénom ou à un nom en début de phrase, mais écrivent une fonction ou un service.
MOTS_DE_FONCTION = {
    "investor", "investors", "relations", "relation", "press", "media", "office", "contact", "email", "mail", "telephone", "phone",
    "director", "manager", "officer", "head", "chief", "financial", "finance", "treasury", "treasurer", "group", "corporate",
    "communications", "communication", "presse", "investisseurs", "relations", "directeur", "directrice", "responsable",
    "autre", "domaine", "for", "pour", "service", "team", "equipe", "équipe",
}
MOIS_MAX_DIRIGEANT = 12
MENTION = "déduite, non vérifiée"
MENTION_ALLEMAGNE = ("En Allemagne, un premier courriel demande un consentement préalable, même entre professionnels (UWG, article 7). "
                     "Le téléphone professionnel y reste possible.")


def _pages_de_la_societe(cache: Path, domaines: list[str]) -> list[str]:
    racines = {domaine_racine(d) for d in domaines}
    textes = []
    for f in cache.glob("*.json"):
        try:
            p = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        hote = re.sub(r"^https?://", "", p.get("url_finale") or p.get("url") or "").split("/")[0]
        if domaine_racine(hote) in racines and p.get("texte"):
            textes.append(p["texte"])
    return textes


def relever(textes: list[str], domaines: list[str]) -> list[dict[str, Any]]:
    """Adresses publiées sur le domaine de la société, avec le nom écrit à côté si la page en donne un."""
    racines = {domaine_racine(d) for d in domaines}
    vues: dict[str, dict[str, Any]] = {}
    for t in textes:
        for m in COURRIEL.finditer(t):
            adresse = m.group(0).rstrip(".").lower()
            local, _, dom = adresse.partition("@")
            if domaine_racine(dom) not in racines or adresse in vues:
                continue
            avant = t[max(0, m.start() - 90):m.start()]
            paires = [p for p in re.findall(r"([A-ZÀ-Ý][a-zà-ÿ'’-]+)\s+([A-ZÀ-Ý][A-Za-zà-ÿ'’-]+)", avant)
                      if not ({p[0].lower(), p[1].lower()} & MOTS_DE_FONCTION)]
            vues[adresse] = {"adresse": adresse, "local": local, "domaine": dom,
                             "generique": local.split(".")[0] in GENERIQUES or local in GENERIQUES,
                             "nom": " ".join(paires[-1]) if paires else None}
    return list(vues.values())


def motif(local: str, nom: str | None) -> str | None:
    """Motif d'une adresse nominative d'après le nom écrit à côté : prenom.nom, nom.prenom, p.nom ou pnom."""
    if not nom or " " not in nom:
        return None
    prenom, famille = (norm(x).replace(" ", "") for x in nom.split(" ", 1))
    for nom_motif, attendu in (("prenom.nom", f"{prenom}.{famille}"), ("nom.prenom", f"{famille}.{prenom}"),
                               ("p.nom", f"{prenom[:1]}.{famille}"), ("pnom", f"{prenom[:1]}{famille}"),
                               ("prenom_nom", f"{prenom}_{famille}"), ("prenomnom", f"{prenom}{famille}")):
        if local.replace("-", "") == attendu:
            return nom_motif
    return None


def appliquer(m: str, nom: str) -> str | None:
    prenom, famille = (norm(x).replace(" ", "") for x in nom.split(" ", 1))
    return {"prenom.nom": f"{prenom}.{famille}", "nom.prenom": f"{famille}.{prenom}", "p.nom": f"{prenom[:1]}.{famille}",
            "pnom": f"{prenom[:1]}{famille}", "prenom_nom": f"{prenom}_{famille}", "prenomnom": f"{prenom}{famille}"}.get(m)


def mx_existe(domaine: str) -> bool | None:
    """Le domaine reçoit-il du courrier ? Une requête DNS, sans dialoguer avec le serveur. None si `dig` manque."""
    dig = shutil.which("dig")
    if dig is None:
        return None
    sortie = subprocess.run([dig, "+short", "MX", domaine], capture_output=True, text=True, timeout=15).stdout
    return bool(sortie.strip())


_FONCTIONS = {norm(m) for m in MOTS_DE_FONCTION | {"direction", "financiere", "financier", "cfo", "ceo", "vice", "president", "senior"}}


def est_nom_de_personne(nom: str) -> bool:
    """Deux à quatre mots qui commencent par une majuscule, dont aucun ne désigne une fonction ou un service."""
    mots = nom.split()
    return 2 <= len(mots) <= 4 and all(m[:1].isupper() and norm(m) not in _FONCTIONS for m in mots)


def dirigeant(fiche: dict) -> str | None:
    """Nom du directeur financier si la société le nomme dans un document de moins de 12 mois, au niveau confirmé ou probable."""
    s = fiche["synthese"][Champ.DIRECTION_FINANCIERE.value]
    if s["niveau"] not in (Niveau.CONFIRME.value, Niveau.PROBABLE.value) or s["contradiction"]:
        return None
    for v in s["valeurs"]:
        for t in fiche["trouvailles"]:
            age = t["verifs"].get("age_mois")
            if t["id"] in v["ids"] and t["verifs"].get("type_source_code") in ("P1", "P2") and (age is None or age <= MOIS_MAX_DIRIGEANT):
                nom = v["valeur"].split(",")[0].split("(")[0].strip()
                if est_nom_de_personne(nom):
                    return nom
    return None


def construire(fiche: dict, entite: Entite, cache: Path | None, sans_contacts: bool = False) -> dict[str, Any] | None:
    if sans_contacts:
        return None
    adresses = relever(_pages_de_la_societe(cache, entite.domaines) if cache else [], entite.domaines)
    generiques = [a["adresse"] for a in adresses if a["generique"]][:3]
    nominatives = [a for a in adresses if not a["generique"]]
    contact: dict[str, Any] = {"generiques": generiques, "suggestion": None, "mention": None, "adresses_nominatives_publiees": len(nominatives)}
    if (entite.pays or "").lower() == "germany":
        contact["mention"] = MENTION_ALLEMAGNE
    nom = dirigeant(fiche)
    if nom:
        motifs = [motif(a["local"], a["nom"]) for a in nominatives]
        motifs = [m for m in motifs if m]
        if len(motifs) >= 2 and len(set(motifs)) == 1:
            local = appliquer(motifs[0], nom)
            domaine = nominatives[0]["domaine"]
            mx = mx_existe(domaine)
            if local and mx is not False:
                contact["suggestion"] = {"nom": nom, "adresse": f"{local}@{domaine}", "motif": motifs[0], "mention": MENTION, "mx": mx}
    return contact


def ligne(contact: dict[str, Any] | None) -> str | None:
    """Ligne du brief : une phrase courte, ou rien si le module n'a rien à dire."""
    if not contact:
        return None
    morceaux = []
    if contact["generiques"]:
        morceaux.append("Adresses publiées : " + ", ".join(contact["generiques"]) + ".")
    s = contact["suggestion"]
    if s:
        morceaux.append(f"Directeur financier : {s['nom']}, adresse {s['adresse']} ({s['mention']}).")
    if contact["mention"]:
        morceaux.append(contact["mention"])
    return " ".join(morceaux) or None
