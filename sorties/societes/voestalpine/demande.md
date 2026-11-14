# Demande pour voestalpine

Tu es l'agent de recherche d'un outil de préparation de rendez-vous. Fais le travail décrit ci-dessous et écris le résultat
dans un fichier. Moyens autorisés : WebSearch, WebFetch et Write (pour le seul fichier de réponse). N'utilise ni le skill
agent-reach, ni Firecrawl, ni LinkedIn, ni aucun serveur MCP. Ne modifie aucun autre fichier.

## Consignes

Tu prépares un rendez-vous avec la direction financière d'une grande entreprise, à partir d'informations publiques uniquement.

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
ERP : SAP S/4HANA, SAP ECC, Oracle Fusion, Oracle E-Business Suite, Oracle JD Edwards, Microsoft Dynamics 365, Microsoft Dynamics AX ou NAV, Infor, IFS, Workday, Sage, QAD, Epicor, autre.
Plateforme d'achats : SAP Ariba, Coupa, Jaggaer, Ivalua, Basware, GEP, Zycus, Oracle Procurement, Microsoft Dynamics 365 Supply Chain, autre.
TMS et trésorerie : Kyriba, SAP Treasury, GTreasury, FIS, ION, Coupa Treasury, Bellin, Salmon, Allgeier (Trema), autre.
Financement court terme : Affacturage avec recours, Affacturage sans recours, Affacturage (recours non précisé), Titrisation de créances, Affacturage inversé (supply chain finance), Escompte dynamique, Billets de trésorerie, Ligne de crédit renouvelable, Crédit documentaire ou forfaiting, autre.


## Demande

Société : voestalpine (nom légal retenu : voestalpine AG)
Pays du siège : Austria. Statut : coté.
Site officiel : https://www.voestalpine.com. Domaines de la société : voestalpine.com.
Attention, identité à confirmer : Wikidata non interrogé : PREPA_RDV_CONTACT absent ; ISIN, LEI et nom légal à confirmer.

Plan de requêtes (suis-le, complète-le si besoin) :
- direction_financiere : voestalpine Chief Financial Officer | voestalpine Group Treasurer | voestalpine investor relations management team | voestalpine Finanzvorstand | voestalpine Treasury Leiter
- erp : voestalpine SAP S/4HANA | voestalpine ERP implementation | voestalpine Oracle OR Dynamics OR Workday ERP | voestalpine annual report SAP
- achats : voestalpine SAP Ariba supplier | voestalpine Coupa OR Jaggaer OR Ivalua | voestalpine supplier portal procurement platform
- tms : voestalpine treasury management system | voestalpine Kyriba | voestalpine SAP Treasury
- financement : voestalpine supply chain finance | voestalpine reverse factoring | voestalpine receivables securitisation programme | voestalpine factoring programme | voestalpine annual report supplier finance arrangements | voestalpine Factoring Forderungen Geschäftsbericht
- signal : voestalpine finance transformation treasury 2026 | voestalpine ERP migration

Réponds uniquement par l'objet JSON du schéma.

## Réponse attendue

Écris dans le fichier `<racine>/sorties/societes/voestalpine/agent-sortie.json` un seul objet JSON, sans texte autour, conforme à ce schéma. Tous les champs de chaque
trouvaille sont obligatoires : mets null quand il n'y a pas de valeur. Réponds ensuite par le seul mot OK.

```json
{
 "additionalProperties": false,
 "description": "Réponse complète du modèle pour une société.",
 "properties": {
  "trouvailles": {
   "items": {
    "additionalProperties": false,
    "description": "Ce que le modèle écrit pour une information. Aucun niveau de confiance.",
    "properties": {
     "champ": {
      "enum": [
       "identite",
       "direction_financiere",
       "erp",
       "achats",
       "tms",
       "financement",
       "signal"
      ],
      "type": "string"
     },
     "valeur": {
      "description": "Pour erp, achats, tms et financement : une valeur de la liste fermée, ou « autre ».",
      "type": "string"
     },
     "precision": {
      "anyOf": [
       {
        "type": "string"
       },
       {
        "type": "null"
       }
      ],
      "description": "Nom exact du produit quand la valeur est « autre », ou détail utile. Sinon null."
     },
     "statut_valeur": {
      "enum": [
       "present",
       "absence_declaree"
      ],
      "type": "string"
     },
     "citation": {
      "description": "Phrase recopiée mot pour mot dans la source, 25 mots au plus.",
      "type": "string"
     },
     "citation_langue": {
      "description": "Code de langue de la citation : en, de, fr, sv, fi, it.",
      "type": "string"
     },
     "traduction_fr": {
      "anyOf": [
       {
        "type": "string"
       },
       {
        "type": "null"
       }
      ],
      "description": "Traduction française de la citation si elle n'est pas en français. Sinon null."
     },
     "url": {
      "description": "Adresse complète de la page qui porte la citation.",
      "type": "string"
     },
     "entite_nommee": {
      "description": "Nom de la société ou de la filiale tel que la page le écrit, à côté de la citation.",
      "type": "string"
     },
     "type_source": {
      "enum": [
       "P1",
       "P2",
       "P3",
       "P4",
       "P5"
      ],
      "type": "string"
     },
     "date_source": {
      "anyOf": [
       {
        "type": "string"
       },
       {
        "type": "null"
       }
      ],
      "description": "Date de la page telle qu'elle y est écrite (AAAA, AAAA-MM ou AAAA-MM-JJ). Null si absente."
     }
    },
    "required": [
     "champ",
     "valeur",
     "precision",
     "statut_valeur",
     "citation",
     "citation_langue",
     "traduction_fr",
     "url",
     "entite_nommee",
     "type_source",
     "date_source"
    ],
    "type": "object"
   },
   "type": "array"
  },
  "champs_sans_resultat": {
   "description": "Champs pour lesquels aucune source n'a été trouvée.",
   "items": {
    "enum": [
     "identite",
     "direction_financiere",
     "erp",
     "achats",
     "tms",
     "financement",
     "signal"
    ],
    "type": "string"
   },
   "type": "array"
  },
  "remarques": {
   "description": "Doutes, homonymes, filiales, limites rencontrées. Liste vide si rien.",
   "items": {
    "type": "string"
   },
   "type": "array"
  }
 },
 "required": [
  "trouvailles",
  "champs_sans_resultat",
  "remarques"
 ],
 "type": "object"
}
```
