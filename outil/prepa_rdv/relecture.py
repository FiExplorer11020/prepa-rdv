"""Seconde lecture à l'aveugle, pour les pages que le code n'a pas le droit de lire (robots.txt, HTTP 401, 403, 429).

Le code ne contourne aucun refus. Mais un site qui interdit les clients inconnus autorise souvent les agents d'assistants
(Claude-User, par exemple). Un second sous-agent rouvre alors la page, sans connaître la citation du premier : on lui
donne l'adresse et le sujet (« ERP : SAP S/4HANA »), il recopie le passage qui soutient ce sujet. Le code compare les deux
textes mot pour mot (similarité de 0,95 au moins). Deux lectures indépendantes qui s'accordent valent preuve, mais pas
au niveau « confirmé » : le plafond est « probable » et la fiche garde la trace du mode de vérification.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .lecteur import Page
from .modele import ErreurModele, _extraire_json
from .resolveur import Entite
from .schema import Trouvaille, TrouvailleBrute, schema_inline

FICHIER_DEMANDE = "relecture-demande.md"
FICHIER_SORTIE = "relecture-sortie.json"
MOTIFS_REFUS = ("robots.txt", "HTTP 401", "HTTP 403", "HTTP 429")


class Lecture(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="Identifiant de la trouvaille, recopié de la demande.")
    lue: bool = Field(description="True si tu as pu ouvrir la page et lire son contenu.")
    passage: str | None = Field(description="Un passage de la page qui soutient le sujet, recopié mot pour mot, 15 mots au plus. Null si introuvable.")
    contexte: str | None = Field(description="Laisse null : un passage plus long ne se recopie pas depuis ton cadre d'exécution.")
    titre: str | None = Field(description="Titre de la page tel qu'elle l'affiche. Null si absent.")
    date_page: str | None = Field(description="Date de publication affichée par la page, telle quelle. Null si absente.")


class SortieRelecture(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lectures: list[Lecture]


def a_relire(trouvailles: list[Trouvaille]) -> list[Trouvaille]:
    """Trouvailles rejetées parce que la page n'a pas pu être lue par le code (et pas pour une autre raison)."""
    return [t for t in trouvailles if not t.verifs.adresse_ok and any(m in " ".join(t.verifs.erreurs) for m in MOTIFS_REFUS)
            and t.verifs.mode_verification == "code"]


def sujet(t: Trouvaille) -> str:
    """Le sujet à chercher, court et sans la thèse du premier agent : le produit, pas ce qu'on en dit."""
    if t.champ.value in ("erp", "achats", "tms", "financement"):
        return t.valeur_normalisee if t.valeur_normalisee != "autre" else (t.precision or t.valeur).split(". ")[0][:60]
    return t.valeur[:80]


def ecrire_demande(dossier: Path, societe: str, trouvailles: list[Trouvaille]) -> Path:
    """Une demande par société, sans les citations : l'adresse, le champ et la valeur seulement."""
    sortie = (dossier / FICHIER_SORTIE).resolve()
    lignes = "\n".join(f"- id `{t.id}` : {t.url}\n  Sujet : {t.champ.value}, {sujet(t)}" for t in trouvailles)
    texte = f"""# Seconde lecture pour {societe}

Tu relis des pages web pour contrôler un travail de recherche. Pour chaque ligne ci-dessous, ouvre l'adresse avec WebFetch et
cherche le passage de la page qui soutient le sujet indiqué. Moyens autorisés : WebFetch, WebSearch et Write (pour le seul
fichier de réponse). N'utilise ni le skill agent-reach, ni Firecrawl, ni LinkedIn, ni aucun serveur MCP.

Règles, sans exception :
- Recopie un seul passage, mot pour mot, tel que la page l'écrit, dans la langue de la page. 15 mots au plus. Ne reformule rien, ne résume rien.
- Choisis la phrase qui dit le plus directement que la société utilise le sujet indiqué. Si tu hésites entre deux, prends la plus courte.
- Si tu ne peux pas ouvrir la page, mets `lue` à false. Si la page s'ouvre mais ne soutient pas le sujet, mets `lue` à true et `passage` à null.
- Ne cherche pas le sujet ailleurs : une seule adresse par ligne, la sienne.
- `contexte` : laisse null. N'essaie pas de reconstituer un texte plus long en demandant la page par morceaux.

## Lignes à relire

{lignes}

## Réponse attendue

Écris dans le fichier `{sortie}` un seul objet JSON, sans texte autour, conforme à ce schéma. Mets null quand il n'y a pas de
valeur. Réponds ensuite par le seul mot OK.

```json
{json.dumps(schema_inline(SortieRelecture), ensure_ascii=False, indent=1)}
```
"""
    chemin = dossier / FICHIER_DEMANDE
    chemin.write_text(texte, encoding="utf-8")
    return chemin


def lire_sortie(dossier: Path) -> SortieRelecture:
    chemin = dossier / FICHIER_SORTIE
    if not chemin.exists():
        raise ErreurModele(f"Pas de réponse : {chemin} n'existe pas")
    try:
        return SortieRelecture.model_validate(_extraire_json(chemin.read_text(encoding="utf-8")))
    except json.JSONDecodeError as e:
        raise ErreurModele(f"Réponse sans JSON valide : {e}") from e
    except ValidationError as e:
        raise ErreurModele(f"Réponse hors schéma : {str(e)[:600]}") from e


def page_relue(url: str, lecture: Lecture) -> Page:
    """Page reconstituée d'après la seconde lecture : passage et contexte recopiés par le second agent."""
    texte = "\n".join(x for x in (lecture.passage, lecture.contexte) if x)
    ok = lecture.lue and bool(texte.strip())
    return Page(url=url, url_finale=url, statut=200 if ok else None, type_contenu="text/html", texte=texte, titre=lecture.titre,
                date_page=lecture.date_page, empreinte=hashlib.sha256(texte.encode()).hexdigest() if texte else None,
                via="seconde_lecture", erreur=None if ok else "seconde lecture sans passage")


def resume(sortie: SortieRelecture) -> dict[str, Any]:
    return {"lectures": len(sortie.lectures), "lues": sum(1 for l in sortie.lectures if l.lue),
            "avec_passage": sum(1 for l in sortie.lectures if l.passage)}
