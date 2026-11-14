# Audit, lot 5 : 12 cellules sur 12

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

- id `barilla-tms-9`
  Société : Barilla
  Champ : TMS et trésorerie
  Valeur : Kyriba
  Citation : « Barilla also selected Kyriba to increase cash visibility, improve cash forecasting, and digitize FX, interest rate »
  Lien : https://www.kyriba.com/news/kyriba-selected-by-barilla-to-provide-a-global-working-capital-treasury-risk-management-platform/
- id `ssab-financement-12`
  Société : SSAB
  Champ : Financements court terme
  Valeur : Billets de trésorerie
  Citation : « The Swedish commercial paper program has a limit of SEK 5,000 million »
  Lien : https://www.ssab.com/company/investors/debt-financing
- id `barilla-signal-18`
  Société : Barilla
  Champ : Signal récent
  Valeur : Changement de direction financière : nomination d'Oddone Incisa comme directeur financier, effective le 15 septembre 2025
  Citation : « Barilla Group announces the appointment of Oddone Incisa as new Chief Financial Officer, effective September 15, 2025. »
  Lien : https://www.eunews.it/en/2025/07/10/barilla-group-appoints-oddone-incisa-as-cfo/
- id `barilla-financement-14`
  Société : Barilla
  Champ : Financements court terme
  Valeur : Affacturage inversé (supply chain finance)
  Citation : « The integration will centralize Barilla’s multiple supply chain finance programs into a single Dynamic Discounting »
  Lien : https://www.kyriba.com/news/kyriba-selected-by-barilla-to-provide-a-global-working-capital-treasury-risk-management-platform/
- id `vattenfall-achats-7`
  Société : Vattenfall
  Champ : Plateforme d'achats
  Valeur : SAP Ariba
  Citation : « Vattenfall has begun to implement SAP Ariba as our main sourcing and tendering tool for the organization. »
  Lien : https://group.vattenfall.com/uk/contentassets/8cd7332db68c478b9816eac515d0c605/sap_aribas_help_center.pdf
- id `nokia-direction_financiere-2`
  Société : Nokia
  Champ : Direction financière
  Valeur : Marco Wirén, Chief Financial Officer (CFO)
  Citation : « Nokia CFO Marco Wirén said that the market is now relatively stable »
  Lien : https://www.fierce-network.com/broadband/ceo-hails-2025-foundational-year-nokia-sales-grow-3
- id `nokia-financement-15`
  Société : Nokia
  Champ : Financements court terme
  Valeur : Affacturage inversé (supply chain finance)
  Citation : « Supply chain financing (SCF) offers suppliers the opportunity to receive early payment on approved invoices »
  Lien : https://www.nokia.com/suppliers/supply-chain-finance/
- id `deutsche-telekom-tms-11`
  Société : Deutsche Telekom
  Champ : TMS et trésorerie
  Valeur : TIP, présenté comme logiciel de trésorerie (« treasury software ») utilisé depuis de nombreuses années ; l'article évoque l'intention de l'étendre à la gestion des garanties à l'échelle du groupe. Le texte de présentation de l'article décrit TIP comme « Treasury Information Platform ». Article de mars 2019, usage actuel non vérifié.
  Citation : « Deutsche Telekom has been using the treasury software TIP for many years »
  Lien : https://www.theglobaltreasurer.com/2019/03/13/digital-guarantee-management-with-tip-at-deutsche-telekom/
- id `vattenfall-financement-9`
  Société : Vattenfall
  Champ : Financements court terme
  Valeur : Billets de trésorerie
  Citation : « For short-term funding, Vattenfall has a European Commercial Paper programme (EUR 10 billion) »
  Lien : https://group.vattenfall.com/investors/funding-and-ratings/programmes-and-credit-facilities/
- id `stadler-rail-signal-9`
  Société : Stadler Rail
  Champ : Signal récent
  Valeur : Deux emprunts obligataires de 150 M CHF chacun, datés du 3 juillet 2026
  Citation : « Stadler hat am 3. Juli 2026 zwei Anleihensobligationen über je CHF 150.0 Mio. »
  Lien : https://a.storyblok.com/f/269997/x/68ae2197d7/stadler-halbjahresbericht-2026-de.pdf
- id `nokia-erp-6`
  Société : Nokia
  Champ : ERP
  Valeur : SAP S/4HANA
  Citation : « with its next-generation SAP S/4HANA software environment »
  Lien : https://news.sap.com/?p=243821
- id `lvmh-signal-8`
  Société : LVMH
  Champ : Signal récent
  Valeur : Recrutement d'un chef de projet Trésorerie et communication bancaire, offre citant la Direction Projets Transformation Finance
  Citation : « la Direction Projets Transformation Finance pour optimiser leurs processus et leurs organisations »
  Lien : https://www.lvmh.com/fr/nous-rejoindre/nos-offres/LVMH03235

## Réponse attendue

Écris dans le fichier `<racine>/sorties/audit/sortie-5.json` un seul objet JSON, sans texte autour, conforme à ce schéma, avec un jugement par cellule
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
