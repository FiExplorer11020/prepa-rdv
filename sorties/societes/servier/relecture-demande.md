# Seconde lecture pour Servier

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

- id `servier-erp-5` : https://www.corcentric.com/company/press-releases/servier-group
  Sujet : erp, SAP ERP, version non précisée : la page n'écrit ni ECC ni S/
- id `servier-erp-6` : https://news.sap.com/africa/2021/12/swiss-pharma-nigeria-ltd-leaps-into-4ir-capabilities-with-sap-s-4hana-deployment/
  Sujet : erp, SAP S/4HANA
- id `servier-achats-8` : https://www.corcentric.com/company/press-releases/servier-procurement-cloud/
  Sujet : achats, Determine (Corcentric), solution Source-to-Pay : usage depui
- id `servier-achats-9` : https://www.corcentric.com/company/press-releases/servier-group
  Sujet : achats, Determine (Corcentric)

## Réponse attendue

Écris dans le fichier `<racine>/sorties/societes/servier/relecture-sortie.json` un seul objet JSON, sans texte autour, conforme à ce schéma. Mets null quand il n'y a pas de
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
      "description": "Un passage de la page qui soutient le sujet, recopié mot pour mot, 15 mots au plus. Null si introuvable."
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
      "description": "Laisse null : un passage plus long ne se recopie pas depuis ton cadre d'exécution."
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
