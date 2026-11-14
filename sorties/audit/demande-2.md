# Audit, lot 2 : 12 cellules sur 36

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

- id `saint-gobain-financement-13`
  Société : Saint-Gobain
  Champ : Financements court terme
  Valeur : Affacturage inversé (supply chain finance)
  Citation : « HSBC China provides Saint-Gobain's suppliers in mainland China with a tier-price financing solution »
  Lien : https://www.saint-gobain.com.cn/en/node/20560
- id `vattenfall-tms-8`
  Société : Vattenfall
  Champ : TMS et trésorerie
  Valeur : SAP Treasury
  Citation : « for the central Vattenfall SAP Treasury solution »
  Lien : https://vakanser.se/jobb/system+manager+sap+treasury+m+f
- id `vattenfall-direction_financiere-2`
  Société : Vattenfall
  Champ : Direction financière
  Valeur : Kerstin Ahlfont, Chief Financial Officer
  Citation : « Kerstin Ahlfont Chief Financial Officer »
  Lien : https://group.vattenfall.com/who-we-are/corporate-governance/group-management
- id `ssab-achats-8`
  Société : SSAB
  Champ : Plateforme d'achats
  Valeur : SAP Ariba
  Citation : « Case Study: SSAB achieves rapid global spend visibility and shifts to higher-value procurement with SAP Ariba »
  Lien : https://www.casestudies.com/company/sap-ariba/case-study/increased-focus-on-higher-value-add-activities-as-a-result-of-global-e-procurement-journey
- id `saint-gobain-signal-14`
  Société : Saint-Gobain
  Champ : Signal récent
  Valeur : Nomination d'Annica Hagen comme Chief Artificial Intelligence Officer et membre du Comité exécutif du Groupe
  Citation : « Annica Hagen has been appointed Chief Artificial Intelligence Officer (CAIO) and member of the Group Executive Committee »
  Lien : https://www.glassonweb.com/news/saint-gobain-appoints-annica-hagen-chief-artificial-intelligence-officer-and-accelerates-ai
- id `ssab-direction_financiere-2`
  Société : SSAB
  Champ : Direction financière
  Valeur : Leena Craelius, directrice financière (CFO)
  Citation : « The report will be presented by SSAB’s President and CEO Johnny Sjöström, and CFO Leena Craelius. »
  Lien : https://www.ssab.com/en/news/2026/10/report-for-q3-2026
- id `fresenius-signal-17`
  Société : Fresenius
  Champ : Signal récent
  Valeur : Placement obligataire de 1 Md€ en deux tranches en 2025
  Citation : « In 2025, Fresenius SE & Co. KGaA successfully placed bonds with an aggregate volume of €1 billion across two tranches. »
  Lien : https://report.fresenius.com/2025/annual-report/management-report/economic-report/financial-position.html
- id `barilla-direction_financiere-3`
  Société : Barilla
  Champ : Direction financière
  Valeur : Oddone Incisa, directeur financier (Chief Financial Officer) du groupe Barilla
  Citation : « Barilla Group announces the appointment of Oddone Incisa as new Chief Financial Officer, effective September 15, 2025. »
  Lien : https://www.eunews.it/en/2025/07/10/barilla-group-appoints-oddone-incisa-as-cfo/
- id `verallia-direction_financiere-2`
  Société : Verallia
  Champ : Direction financière
  Valeur : Cristina Riesgo, Chief Financial Officer (directrice financière), à compter du 1er mars 2026
  Citation : « announces the appointment of Cristina Riesgo as Chief Financial Officer, effective March 1st, 2026 »
  Lien : https://www.verallia.com/en/communique-de-presse/cristina-riesgo/
- id `deutsche-telekom-direction_financiere-3`
  Société : Deutsche Telekom
  Champ : Direction financière
  Valeur : Christian P. Illek, membre du directoire responsable des finances (directeur financier)
  Citation : « assumed responsibility for the Finance portfolio on the Board of Management on January 1, 2019. »
  Lien : https://www.telekom.com/en/about-us/corporate-governance/board-of-management/profile-christian-p-illek
- id `voestalpine-signal-15`
  Société : voestalpine
  Champ : Signal récent
  Valeur : Nouvelle CFO de la division Metal Engineering, membre du directoire de la division depuis le 01/04/2026
  Citation : « Eva Aigner has been a member of the Management Board of the Metal Engineering Division of the voestalpine Group since April 1, 2026 »
  Lien : https://www.voestalpine.com/group/en/media/press-releases/Eva-Aigner-is-the-new-Chief-Financial-Officer-of-the-Metal-Engineering-Division-of-the-voestalpine-Group/
- id `lvmh-erp-3`
  Société : LVMH
  Champ : ERP
  Valeur : SAP S/4HANA
  Citation : « support key phases of our SAP S/4HANA Public Cloud Edition (PCE) »
  Lien : https://www.lvmh.com/join-us/our-job-offers/SSCPC02560

## Réponse attendue

Écris dans le fichier `<racine>/sorties/audit/sortie-2.json` un seul objet JSON, sans texte autour, conforme à ce schéma, avec un jugement par cellule
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
