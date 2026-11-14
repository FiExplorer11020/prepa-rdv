# Audit, lot 1 : 12 cellules sur 36

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

- id `deutsche-telekom-financement-12`
  Société : Deutsche Telekom
  Champ : Financements court terme
  Valeur : Affacturage (recours non précisé)
  Citation : « Deutsche Telekom is party to factoring agreements under which trade receivables from consumers and business customers »
  Lien : https://report.telekom.com/annual-report-2025/notes/other-disclosures/43-financial-instruments-and-risk-management.html
- id `lvmh-achats-6`
  Société : LVMH
  Champ : Plateforme d'achats
  Valeur : Aprovall : plateforme KYS (Know Your Supplier) de collecte, de partage et d'exploitation des données fournisseurs, utilisée par les équipes achats, juridique et contrôle interne de Moët Hennessy, présentée par la page comme la division Vins et Spiritueux du groupe LVMH. Aucune plateforme de la liste (SAP Ariba, Coupa, Jaggaer, Ivalua, Basware, GEP, Zycus) n'a été trouvée pour LVMH.
  Citation : « partnership with Aprovall led to the creation of the KYS – Know Your Supplier platform »
  Lien : https://www.aprovall.com/?p=5410
- id `ssab-signal-17`
  Société : SSAB
  Champ : Signal récent
  Valeur : Première notation de crédit de SSAB par Moody's, attribuée au troisième trimestre 2026
  Citation : « During the third quarter, Moody’s assigned a credit rating to SSAB for the first time. »
  Lien : https://www.ssab.com/en/news/2026/10/report-for-q3-2026
- id `voestalpine-financement-9`
  Société : voestalpine
  Champ : Financements court terme
  Valeur : Affacturage (recours non précisé)
  Citation : « In the voestalpine Group, trade receivables are sold monthly to various banks on a revolving basis. »
  Lien : https://reports.voestalpine.com/2526/ar/notes/other-notes/d-30-disclosures.html
- id `servier-signal-12`
  Société : Servier
  Champ : Signal récent
  Valeur : Acquisition d'Edgewise (1,55 Md$ à la signature) finalisée le 13 juillet
  Citation : « The transaction, completed July 13, was intended to accelerate Servier's expansion into rare neurological diseases. »
  Lien : https://european-biotechnology.com/latest-news/serviers-1-55b-edgewise-acquisition-backfires-after-phase-3-setback/
- id `verallia-achats-5`
  Société : Verallia
  Champ : Plateforme d'achats
  Valeur : Ivalua
  Citation : « Verallia Group achieves 360° supplier visibility and 80% supplier base reduction with Ivalua »
  Lien : https://www.casestudies.com/company/ivalua/case-study/verallia-group-customer-case-study
- id `deutsche-telekom-erp-6`
  Société : Deutsche Telekom
  Champ : ERP
  Valeur : SAP S/4HANA
  Citation : « The roadmap includes migrating SAP applications and transitioning to S/4HANA by 2025, with full migration planned by 2030. »
  Lien : https://www.t-systems.com/gb/en/success-stories/cloud-and-infrastructure/deutsche-telekom-it-moves-to-rise-with-sap
- id `fresenius-achats-9`
  Société : Fresenius
  Champ : Plateforme d'achats
  Valeur : SAP Ariba
  Citation : « Fresenius Kabi has engaged with SAP Ariba to standardise the onboarding of suppliers. »
  Lien : https://fresenius-kabi.com/sap-ariba
- id `servier-direction_financiere-2`
  Société : Servier
  Champ : Direction financière
  Valeur : Pascal Lemaire
  Citation : « Pascal Lemaire Executive Vice President Finance »
  Lien : https://servier.com/en/servier-group/executive-committee/
- id `servier-financement-10`
  Société : Servier
  Champ : Financements court terme
  Valeur : Ligne de crédit renouvelable
  Citation : « White & Case advises Servier on financing for Edgewise Therapeutics acquisition and revolving credit facility refinancing »
  Lien : https://www.whitecase.com/news/press-release/white-case-advises-servier-financing-edgewise-therapeutics-acquisition-and
- id `saint-gobain-erp-4`
  Société : Saint-Gobain
  Champ : ERP
  Valeur : SAP S/4HANA
  Citation : « The outdated, disjointed IT architecture was also blocking their 'OneSG' strategy and a planned migration to SAP S/4HANA. »
  Lien : https://www.casestudies.com/company/mulesoft/case-study/saint-gobain-deploys-90-workflows-in-6-months-with-mulesoft
- id `nokia-signal-18`
  Société : Nokia
  Champ : Signal récent
  Valeur : Accord pluriannuel Nokia, SAP et Microsoft : migration du paysage SAP vers RISE with SAP sur Microsoft Azure, finance et logistique clé comprises
  Citation : « migrating Nokia’s SAP landscape to the RISE with SAP journey »
  Lien : https://news.sap.com/?p=243821

## Réponse attendue

Écris dans le fichier `<racine>/sorties/audit/sortie-1.json` un seul objet JSON, sans texte autour, conforme à ce schéma, avec un jugement par cellule
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
