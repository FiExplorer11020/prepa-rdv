# Audit, lot 3 : 12 cellules sur 36

Tu es l'auditeur d'un outil qui prépare des rendez-vous avec la direction financière de grandes sociétés. L'outil a rempli
une cartographie depuis des pages web publiques. Chaque cellule ci-dessous porte une valeur, la citation sur laquelle
l'outil la fonde et le lien de la page. Pour chaque cellule, dis si la page soutient la valeur pour la société. Tu n'as pas
produit ces cellules et tu ne connais pas le niveau de confiance que l'outil leur a donné.

Moyens autorisés : WebFetch, et Write pour le seul fichier de réponse. N'utilise ni WebSearch, ni le skill agent-reach, ni
Firecrawl, ni LinkedIn, ni aucun serveur MCP. Ne modifie aucun autre fichier.

## Méthode, pour chaque cellule

1. Ouvre le lien avec WebFetch. Demande si la page dit, pour la société, ce que dit la valeur, si la citation y figure, et
   fais recopier la phrase qui tranche. Un lien par cellule, le sien : ne cherche pas ailleurs.
2. Juge d'après la page seule, sans ta mémoire ni une autre source.
3. Écris le verdict, l'écart s'il y en a un, une raison d'une phrase et le passage.

## Ce que veut dire chaque champ

- ERP : le progiciel de gestion intégré que la société utilise ou déploie.
- Plateforme d'achats : l'outil des achats (sourcing, achat à paiement, gestion des fournisseurs) que la société utilise.
- TMS et trésorerie : le système de gestion de la trésorerie que la société utilise.
- Financements court terme : un financement à moins d'un an ou une ligne de liquidité au nom de la société (billets de
  trésorerie, crédit renouvelable, affacturage, financement de la chaîne fournisseurs).
- Direction financière : la personne qui tient la fonction finance nommée dans la valeur.
- Signal récent : un événement que la page rapporte pour la société.

## Les verdicts

- juste : la page dit ce que dit la valeur, pour la société ou pour le groupe qu'elle forme.
- partiel : la page ne soutient qu'une partie de la valeur. Elle parle d'une filiale, d'une division ou d'un pays du groupe,
  pas du groupe ; ou la valeur ajoute une précision que la page ne donne pas.
- faux : la page ne soutient pas la valeur. Autre société, outil seulement évalué ou abandonné, autre produit, conclusion
  qui dépasse le texte, personne qui n'occupe plus la fonction d'après la page elle-même.
- invérifiable : la page ne s'ouvre pas, ou son contenu ne permet pas de trancher.

Deux conventions de l'outil. Une offre d'emploi de la société qui demande la pratique d'un outil pour un poste chez elle
vaut usage de l'outil. Une étude de cas d'un éditeur ou d'un intégrateur qui nomme la société comme cliente vaut usage.

L'écart se choisit dans la liste du schéma : pour un verdict partiel ou faux, il est obligatoire ; pour juste et
invérifiable, il est null. Une page qui ne s'ouvre pas donne `page_ouverte` false et le verdict invérifiable.

## Cellules du lot

- id `verallia-signal-15`
  Société : Verallia
  Champ : Signal récent
  Valeur : Changement de directrice financière : Cristina Riesgo succède à Nathalie Delbreuve le 1er mars 2026
  Citation : « announces the appointment of Cristina Riesgo as Chief Financial Officer, effective March 1st, 2026 »
  Lien : https://www.verallia.com/en/communique-de-presse/cristina-riesgo/
- id `stadler-rail-financement-7`
  Société : Stadler Rail
  Champ : Financements court terme
  Valeur : Ligne de crédit renouvelable
  Citation : « partially committed up to CHF 2.8 billion syndicated revolving credit facilities financing »
  Lien : https://chambers.com/articles/ubs-switzerland-ag-and-an-international-bank-syndicate-arrange-up-to-chf-2-8bn-financing-for-stadler
- id `stadler-rail-direction_financiere-3`
  Société : Stadler Rail
  Champ : Direction financière
  Valeur : Raphael Widmer, Group CFO
  Citation : « RAPHAEL WIDMER Group CFO »
  Lien : https://stadlerrail.com/en/group-executive-board
- id `vattenfall-erp-4`
  Société : Vattenfall
  Champ : ERP
  Valeur : SAP S/4HANA
  Citation : « Vattenfall gets ready for SAP S/4HANA »
  Lien : https://www.natuvion.com/success-stories/vattenfall-erp-consolidation/
- id `voestalpine-achats-7`
  Société : voestalpine
  Champ : Plateforme d'achats
  Valeur : SAP Ariba
  Citation : « For operational collaboration with suppliers, voestalpine uses the SAP Business Network (formerly SAP Ariba). »
  Lien : https://www.voestalpine.com/group/en/group/supplier/
- id `fresenius-financement-13`
  Société : Fresenius
  Champ : Financements court terme
  Valeur : Billets de trésorerie
  Citation : « For short-term financing needs, Fresenius SE & Co. KGaA maintains bilateral credit lines and a commercial paper program. »
  Lien : https://report.fresenius.com/2025/annual-report/management-report/economic-report/financial-position.html
- id `nokia-achats-8`
  Société : Nokia
  Champ : Plateforme d'achats
  Valeur : SAP Ariba
  Citation : « Nokia Mobile Networks will use SAP Ariba for RFx management »
  Lien : https://nokia.com/suppliers/rfx-guidance
- id `deutsche-telekom-achats-9`
  Société : Deutsche Telekom
  Champ : Plateforme d'achats
  Valeur : SAP Ariba
  Citation : « SAP Ariba Network is the portal for electronical billing and purchase ordering exchange with our suppliers. »
  Lien : https://www.telekom.com/en/general/procurement
- id `fresenius-direction_financiere-4`
  Société : Fresenius
  Champ : Direction financière
  Valeur : Sara Hennicken, Chief Financial Officer
  Citation : « Sara Hennicken was appointed CFO of Fresenius as of September 1, 2022. »
  Lien : https://report.fresenius.com/2025/annual-report/to-our-shareholders/management-board.html
- id `ssab-erp-7`
  Société : SSAB
  Champ : ERP
  Valeur : SAP S/4HANA
  Citation : « Tibnor använder S/4HANA som den primära källan för sina affärsdata. »
  Lien : https://news.sap.com/sweden/2025/04/varldspremiar-hos-tibnor-forst-ut-med-saps-nya-molnplattform/
- id `saint-gobain-direction_financiere-2`
  Société : Saint-Gobain
  Champ : Direction financière
  Valeur : Maud Thuaudet, Chief Financial Officer
  Citation : « Maud Thuaudet has been appointed Chief Financial Officer »
  Lien : https://www.glassonweb.com/news/saint-gobain-announces-new-cfo-and-asia-pacific-ceo
- id `fresenius-erp-6`
  Société : Fresenius
  Champ : ERP
  Valeur : SAP ECC
  Citation : « von SAP ECC 6 auf S/4HANA migrieren und mithilfe des RISE-Modells von SAP betreiben »
  Lien : https://www.cio.de/article/3699040/it-management-in-tueckischem-gewaesser.html

## Réponse attendue

Écris dans le fichier `<racine>/sorties/audit/sortie-3.json` un seul objet JSON, sans texte autour, conforme à ce schéma, avec un jugement par cellule
du lot et un seul. Mets null quand il n'y a pas de valeur. Réponds ensuite par le seul mot OK.

```json
{
 "additionalProperties": false,
 "properties": {
  "jugements": {
   "items": {
    "additionalProperties": false,
    "properties": {
     "id": {
      "description": "Identifiant de la cellule, recopié de la demande.",
      "type": "string"
     },
     "page_ouverte": {
      "description": "True si tu as pu ouvrir le lien et lire la page.",
      "type": "boolean"
     },
     "citation_presente": {
      "anyOf": [
       {
        "type": "boolean"
       },
       {
        "type": "null"
       }
      ],
      "description": "True si la citation de la cellule figure sur la page, à la ponctuation près. Null si la page n'a pas pu être lue."
     },
     "verdict": {
      "description": "Voir les définitions de la demande.",
      "enum": [
       "juste",
       "partiel",
       "faux",
       "invérifiable"
      ],
      "type": "string"
     },
     "ecart": {
      "anyOf": [
       {
        "enum": [
         "filiale ou division",
         "précision non soutenue",
         "autre société",
         "projet ou évaluation",
         "autre produit",
         "extrapolation",
         "personne remplacée",
         "page sans la valeur"
        ],
        "type": "string"
       },
       {
        "type": "null"
       }
      ],
      "description": "Pour un verdict partiel ou faux : la nature de l'écart. Null pour juste et invérifiable."
     },
     "raison": {
      "description": "Une phrase de 30 mots au plus : ce que la page établit, ou n'établit pas.",
      "type": "string"
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
      "description": "Le passage de la page qui fonde le verdict, recopié mot pour mot, 15 mots au plus. Null si aucun."
     }
    },
    "required": [
     "id",
     "page_ouverte",
     "citation_presente",
     "verdict",
     "ecart",
     "raison",
     "passage"
    ],
    "type": "object"
   },
   "type": "array"
  }
 },
 "required": [
  "jugements"
 ],
 "type": "object"
}
```
