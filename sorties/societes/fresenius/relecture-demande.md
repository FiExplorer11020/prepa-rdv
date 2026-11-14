# Seconde lecture pour Fresenius

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

- id `fresenius-identite-2` : https://www.fresenius.com/faq
  Sujet : identite, ISIN DE000FRE5EN2 (actions nominatives), WKN FRE5EN
- id `fresenius-identite-3` : https://www.fresenius.com/faq
  Sujet : identite, Fresenius SE & Co. KGaA, société en commandite par actions (KGaA) depuis le 28 j
- id `fresenius-erp-7` : https://www.fresenius.com/node/6625
  Sujet : erp, SAP, version de l'ERP non précisée : la page ne dit pas si c
- id `fresenius-erp-8` : https://www.everestgrp.com/report/egr-2025-56-pp-7623
  Sujet : erp, SAP S/4HANA
- id `fresenius-tms-10` : https://www.theglobaltreasurer.com/2019/04/11/twin-treasury-pillars-fx-risk-and-more-at-dax-listed-fresenius/
  Sujet : tms, SAP Treasury
- id `fresenius-tms-11` : https://www.theglobaltreasurer.com/2019/04/11/twin-treasury-pillars-fx-risk-and-more-at-dax-listed-fresenius/
  Sujet : tms, TIP (Treasury Information Platform), nommé dans l'article de

## Réponse attendue

Écris dans le fichier `<racine>/sorties/societes/fresenius/relecture-sortie.json` un seul objet JSON, sans texte autour, conforme à ce schéma. Mets null quand il n'y a pas de
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
