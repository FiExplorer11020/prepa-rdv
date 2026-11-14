# Seconde lecture pour Saint-Gobain

Tu relis des pages web pour contrôler un travail de recherche. Pour chaque ligne ci-dessous, ouvre l'adresse avec WebFetch et
cherche le passage de la page qui soutient le sujet indiqué. Moyens autorisés : WebFetch, WebSearch et Write (pour le seul
fichier de réponse). N'utilise ni le skill agent-reach, ni Firecrawl, ni LinkedIn, ni aucun serveur MCP.

Règles, sans exception :
- Recopie le passage mot pour mot, tel que la page l'écrit, dans la langue de la page. 40 mots au plus. Ne reformule rien.
- Si tu ne peux pas ouvrir la page, mets `lue` à false. Si la page s'ouvre mais ne soutient pas le sujet, mets `lue` à true et `passage` à null.
- Ne cherche pas le sujet ailleurs : une seule adresse par ligne, la sienne.
- `contexte` : les 600 caractères de la page autour du passage, recopiés mot pour mot.

## Lignes à relire

- id `saint-gobain-achats-6` : https://www.jaggaer.com/success-stories/saint-gobain
  Sujet : achats, Jaggaer

## Réponse attendue

Écris dans le fichier `<racine>/sorties/societes/saint-gobain/relecture-sortie.json` un seul objet JSON, sans texte autour, conforme à ce schéma. Mets null quand il n'y a pas de
valeur. Réponds ensuite par le seul mot OK.

```json
{
 "additionalProperties": false,
 "properties": {
  "lectures": {
   "items": {
    "additionalProperties": false,
    "properties": {
     "id": {
      "description": "Identifiant de la trouvaille, recopié de la demande.",
      "type": "string"
     },
     "lue": {
      "description": "True si tu as pu ouvrir la page et lire son contenu.",
      "type": "boolean"
     },
     "passage": {
      "anyOf": [
       {
        "type": "string"
       },
       {
        "type": "null"
       }
      ],
      "description": "Passage de la page qui soutient le sujet, recopié mot pour mot, 40 mots au plus. Null si introuvable."
     },
     "contexte": {
      "anyOf": [
       {
        "type": "string"
       },
       {
        "type": "null"
       }
      ],
      "description": "Les 600 caractères de la page autour du passage, recopiés mot pour mot. Null si introuvable."
     },
     "titre": {
      "anyOf": [
       {
        "type": "string"
       },
       {
        "type": "null"
       }
      ],
      "description": "Titre de la page tel qu'elle l'affiche. Null si absent."
     },
     "date_page": {
      "anyOf": [
       {
        "type": "string"
       },
       {
        "type": "null"
       }
      ],
      "description": "Date de publication affichée par la page, telle quelle. Null si absente."
     }
    },
    "required": [
     "id",
     "lue",
     "passage",
     "contexte",
     "titre",
     "date_page"
    ],
    "type": "object"
   },
   "type": "array"
  }
 },
 "required": [
  "lectures"
 ],
 "type": "object"
}
```
