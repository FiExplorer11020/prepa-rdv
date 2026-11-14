"""Résolution d'entité : Wikidata d'abord, GLEIF pour contrôler le LEI, puis une question si le doute reste.

Le nom saisi devient un groupe précis (identifiant Wikidata, pays, ISIN, LEI, site). Une société qui n'est
pas résolue sans ambiguïté est marquée « à confirmer » avec sa raison : le modèle ne devine pas l'entité.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from urllib.parse import urlparse

import httpx

from . import __version__
from .lecteur import domaine_racine, en_ascii

SPARQL = "https://query.wikidata.org/sparql"
API_WIKIDATA = "https://www.wikidata.org/w/api.php"
GLEIF = "https://api.gleif.org/api/v1/lei-records/{lei}"

# Étiquettes anglaises connues de Wikidata quand le nom courant ne suffit pas. Liste de départ [H].
ETIQUETTES = {
    "voestalpine": ("voestalpine AG", "voestalpine"),
    "fresenius": ("Fresenius SE & Co. KGaA", "Fresenius SE", "Fresenius"),
    "verallia": ("Verallia SA", "Verallia"),
    "barilla": ("Barilla Group", "Barilla"),
    "stadler rail": ("Stadler Rail", "Stadler Rail AG"),
    "ssab": ("SSAB", "SSAB AB"),
    "lvmh": ("LVMH", "LVMH Moët Hennessy Louis Vuitton"),
    "servier": ("Servier", "Laboratoires Servier"),
    "saint-gobain": ("Saint-Gobain", "Compagnie de Saint-Gobain"),
    "deutsche telekom": ("Deutsche Telekom", "Deutsche Telekom AG"),
    "vattenfall": ("Vattenfall", "Vattenfall AB"),
    "nokia": ("Nokia", "Nokia Corporation"),
}


# Table locale des 12 sociétés du cas (plan de repli : Wikidata en panne ou refus du contact).
# Seuls les faits publics et certains y figurent : pays, site officiel, statut. ISIN et LEI restent à
# confirmer par Wikidata et GLEIF.
GRAINES: dict[str, dict] = {
    "ssab": {"nom": "SSAB AB", "pays": "Sweden", "site": "https://www.ssab.com", "statut": "coté"},
    "voestalpine": {"nom": "voestalpine AG", "pays": "Austria", "site": "https://www.voestalpine.com", "statut": "coté"},
    "barilla": {"nom": "Barilla G. e R. Fratelli S.p.A.", "pays": "Italy", "site": "https://www.barillagroup.com", "statut": "privé"},
    "stadler rail": {"nom": "Stadler Rail AG", "pays": "Switzerland", "site": "https://www.stadlerrail.com", "statut": "coté"},
    "lvmh": {"nom": "LVMH Moët Hennessy Louis Vuitton SE", "pays": "France", "site": "https://www.lvmh.com", "statut": "coté"},
    "vattenfall": {"nom": "Vattenfall AB", "pays": "Sweden", "site": "https://group.vattenfall.com", "statut": "public (État suédois)"},
    "servier": {"nom": "Les Laboratoires Servier", "pays": "France", "site": "https://servier.com", "statut": "privé (fondation)"},
    "fresenius": {"nom": "Fresenius SE & Co. KGaA", "pays": "Germany", "site": "https://www.fresenius.com", "statut": "coté"},
    "nokia": {"nom": "Nokia Oyj", "pays": "Finland", "site": "https://www.nokia.com", "statut": "coté"},
    "saint-gobain": {"nom": "Compagnie de Saint-Gobain", "pays": "France", "site": "https://www.saint-gobain.com", "statut": "coté"},
    "deutsche telekom": {"nom": "Deutsche Telekom AG", "pays": "Germany", "site": "https://www.telekom.com", "statut": "coté"},
    "verallia": {"nom": "Verallia SA", "pays": "France", "site": "https://www.verallia.com", "statut": "à vérifier"},
}


@dataclass
class Entite:
    nom_saisi: str
    nom_retenu: str | None = None
    qid: str | None = None
    pays: str | None = None
    statut: str | None = None
    isin: list[str] = field(default_factory=list)
    lei: str | None = None
    lei_controle: bool | None = None
    nom_gleif: str | None = None
    site: str | None = None
    domaines: list[str] = field(default_factory=list)
    alias: list[str] = field(default_factory=list)
    a_confirmer: str | None = None
    source: str = ""

    @property
    def domaine_societe(self) -> list[str]:
        return self.domaines


class Resolveur:
    def __init__(self, contact: str | None = None, client: httpx.Client | None = None):
        contact = contact or os.environ.get("PREPA_RDV_CONTACT")
        # Sans contact, Wikimedia renvoie 403 : on ne l'interroge pas, on retombe sur la table locale.
        self.interroger_wikidata = bool(contact) or client is not None
        contact = contact or "contact : voir le depot du projet"
        self.client = client or httpx.Client(
            headers={"User-Agent": en_ascii(f"prepa-rdv/{__version__} (résolution d'entités, lecture seule ; {contact})"),
                     "Accept": "application/json"}, timeout=60)
        self._dernier = 0.0

    def _get(self, url: str, **params) -> dict:
        reste = self._dernier + 1.0 - time.monotonic()  # Wikidata : débit modeste, 5 requêtes parallèles au plus
        if reste > 0:
            time.sleep(reste)
        self._dernier = time.monotonic()
        r = self.client.get(url, params=params)
        r.raise_for_status()
        return r.json()

    # -- Wikidata --------------------------------------------------------------------------------

    def _par_etiquette(self, etiquettes: tuple[str, ...]) -> list[dict]:
        valeurs = " ".join('"' + e.replace('"', "") + '"@en' for e in etiquettes)
        requete = f"""SELECT ?item ?label ?pays ?site ?isin ?lei ?bourse WHERE {{
          VALUES ?label {{ {valeurs} }}
          ?item rdfs:label ?label .
          ?item wdt:P31/wdt:P279* wd:Q4830453 .
          OPTIONAL {{ ?item wdt:P17 ?p . ?p rdfs:label ?pays FILTER(lang(?pays) = "en") }}
          OPTIONAL {{ ?item wdt:P856 ?site }}
          OPTIONAL {{ ?item wdt:P946 ?isin }}
          OPTIONAL {{ ?item wdt:P1278 ?lei }}
          OPTIONAL {{ ?item wdt:P414 ?bourse }}
        }}"""
        return self._get(SPARQL, query=requete, format="json")["results"]["bindings"]

    def _par_recherche(self, nom: str) -> list[dict]:
        """Candidats par la recherche de Wikidata, quand l'étiquette exacte ne donne rien."""
        d = self._get(API_WIKIDATA, action="wbsearchentities", search=nom, language="en", type="item", limit=5, format="json")
        mots = ("company", "manufacturer", "corporation", "group", "enterprise", "bank", "holding", "producer")
        return [x for x in d.get("search", []) if any(m in (x.get("description") or "").lower() for m in mots)]

    def resoudre(self, nom: str) -> Entite:
        e = Entite(nom_saisi=nom)
        if not self.interroger_wikidata:
            return self._graine(e, "Wikidata non interrogé : PREPA_RDV_CONTACT absent")
        etiquettes = ETIQUETTES.get(nom.lower().strip(), (nom,))
        try:
            lignes = self._par_etiquette(etiquettes)
            if not lignes:
                for c in self._par_recherche(nom)[:2]:
                    lignes += self._par_etiquette((c["label"],))
                    if lignes:
                        e.source = "wikidata (recherche)"
                        break
            else:
                e.source = "wikidata (étiquette exacte)"
        except (httpx.HTTPError, KeyError) as ex:
            raison = "Wikidata refuse l'identité de l'outil (renseigner PREPA_RDV_CONTACT)" if isinstance(ex, httpx.HTTPStatusError) and ex.response.status_code == 403 \
                else f"Wikidata injoignable : {type(ex).__name__}"
            return self._graine(e, raison)
        if not lignes:
            return self._graine(e, "aucun résultat Wikidata")

        par_item: dict[str, dict] = {}
        for l in lignes:
            qid = l["item"]["value"].rsplit("/", 1)[-1]
            x = par_item.setdefault(qid, {"label": l["label"]["value"], "pays": set(), "site": set(), "isin": set(), "lei": set(), "bourse": False})
            for cle, src in (("pays", "pays"), ("site", "site"), ("isin", "isin"), ("lei", "lei")):
                if src in l:
                    x[cle].add(l[src]["value"])
            if "bourse" in l:
                x["bourse"] = True
        # Le plus renseigné d'abord : un groupe porte un LEI, un site et un ISIN.
        classes = sorted(par_item.items(), key=lambda kv: -(len(kv[1]["lei"]) + len(kv[1]["site"]) + len(kv[1]["isin"])))
        qid, x = classes[0]
        e.qid, e.nom_retenu = qid, x["label"]
        e.pays = sorted(x["pays"])[0] if x["pays"] else None
        e.isin = sorted(x["isin"])
        e.site = sorted(x["site"])[0] if x["site"] else None
        e.statut = "coté" if (x["bourse"] or x["isin"]) else "privé ou non précisé"
        if e.site:
            e.domaines = [domaine_racine(urlparse(e.site).hostname or "")]
        if len(classes) > 1:
            e.alias = [c[1]["label"] for c in classes[1:]]
            e.a_confirmer = f"{len(classes)} entités homonymes dans Wikidata ({', '.join(c[0] for c in classes)}) : la plus renseignée est retenue"

        leis = sorted(x["lei"])
        e.lei = self._lei_valide(e, leis) if leis else None
        if not leis:
            e.a_confirmer = (e.a_confirmer + " ; " if e.a_confirmer else "") + "pas de LEI dans Wikidata"
        return e

    @staticmethod
    def _graine(e: Entite, raison: str) -> Entite:
        """Repli : la table locale des 12 sociétés, sinon une entité à confirmer."""
        g = GRAINES.get(e.nom_saisi.lower().strip())
        if g is None:
            e.a_confirmer = raison
            return e
        e.nom_retenu, e.pays, e.site, e.statut = g["nom"], g["pays"], g["site"], g["statut"]
        e.domaines = [domaine_racine(urlparse(g["site"]).hostname or "")]
        e.source = "table locale"
        e.a_confirmer = f"{raison} ; ISIN, LEI et nom légal à confirmer"
        return e

    # -- GLEIF -----------------------------------------------------------------------------------

    def _lei_valide(self, e: Entite, leis: list[str]) -> str | None:
        """Premier LEI que GLEIF connaît comme actif. Contrôle d'un LEI connu, pas une recherche par nom."""
        for lei in leis:
            try:
                d = self._get(GLEIF.format(lei=lei))["data"]["attributes"]
            except (httpx.HTTPError, KeyError):
                continue
            actif = d.get("registration", {}).get("status") == "ISSUED" and d.get("entity", {}).get("status") == "ACTIVE"
            if actif:
                e.lei, e.lei_controle = lei, True
                e.nom_gleif = d["entity"]["legalName"]["name"]
                return lei
        e.lei_controle = False
        return leis[0]
