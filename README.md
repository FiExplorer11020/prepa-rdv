# prepa-rdv

Un outil qui prépare un rendez-vous avec la direction financière d'une grande entreprise, à partir d'informations
publiques. Pour chaque société, il cherche l'ERP, la plateforme d'achats, le TMS et les financements court terme en
place. Chaque information porte sa citation, l'adresse de sa page, sa date et un niveau de confiance, que le code fixe
d'après une table.

Ce dépôt est celui d'un cas pratique fait en novembre 2026 pour La Fabrique by CA (stage Ops & IA). Le cas demande de
préparer douze rendez-vous en trois heures de construction au plus, avec un outil qui fait le travail. Son scénario est
fictif. Tout ce que l'outil a produit pour les douze sociétés est ici, avec le code, les journaux et la méthode.

## Les livrables

| Fichier | Ce qu'il contient |
|---|---|
| [`sorties/livrables/briefs.pdf`](sorties/livrables/briefs.pdf) | Les douze briefs, une page par société |
| [`sorties/livrables/cartographie.xlsx`](sorties/livrables/cartographie.xlsx) | Une ligne par société : les quatre informations, leur niveau et leur source, plus une feuille d'audit |
| [`sorties/livrables/trouvailles.xlsx`](sorties/livrables/trouvailles.xlsx) | Toutes les trouvailles, retenues ou rejetées, avec ce que chaque contrôle a vu |
| [`sorties/livrables/ton-outil.pdf`](sorties/livrables/ton-outil.pdf) | Comment l'outil fonctionne, où il s'est trompé, ce qu'il coûte ([texte source](sorties/livrables/ton-outil.md)) |
| [`sorties/livrables/a-200-societes.pdf`](sorties/livrables/a-200-societes.pdf) | Ce qui change pour passer de douze à deux cents sociétés ([texte source](sorties/livrables/a-200-societes.md)) |

Les douze sociétés : SSAB, voestalpine, Barilla, Stadler Rail, LVMH, Vattenfall, Servier, Fresenius, Nokia,
Saint-Gobain, Deutsche Telekom, Verallia. Le dossier de chacune est dans `sorties/societes/` : la demande faite à
l'agent, sa réponse brute, la fiche vérifiée, le brief et le journal de chaque étape.

Les briefs se lisent aussi en ligne, sans compte, sur
[outil-fiexplorer11020s-projects.vercel.app](https://outil-fiexplorer11020s-projects.vercel.app/) : une page par
société, avec ses sources et la citation de chaque trouvaille retenue. Ce site statique est tiré des mêmes fiches par la
commande `vitrine`, après la fin des trois heures (D24). Ses fichiers sont dans [`vitrine/`](vitrine/).

## Les réponses, société par société

Ce que l'outil a retenu pour chaque société, tiré des fiches vérifiées au moment où ce dépôt est construit. Chaque
réponse renvoie à sa source. « Confirmé » : la citation est retrouvée dans une
page récente de la société, ou d'un tiers qui la nomme. « Probable » : la citation est retrouvée, mais la source est
ancienne, sans date, de presse ou d'offre d'emploi, ou la société est nommée plus loin. La table complète est en
section 4 de la méthodologie. Le brief de chaque société est dans
[`briefs.pdf`](sorties/livrables/briefs.pdf).

<!-- reponses -->
<details><summary><b>SSAB</b></summary>

| Champ | Réponse | Niveau |
|---|---|---|
| Direction financière | Leena Craelius, directrice financière (CFO) [[1]](https://www.ssab.com/en/news/2026/10/report-for-q3-2026) ; Kati Vellinki, Head of Treasury [[2]](https://www.ssab.com/en/news/2025/04/ssab-secures-green-financing-of-eur-23-billion) | confirmé |
| ERP | SAP S/4HANA (entité nommée : Tibnor) (seconde lecture) [[3]](https://news.sap.com/sweden/2025/04/varldspremiar-hos-tibnor-forst-ut-med-saps-nya-molnplattform/) | probable |
| Plateforme d'achats | SAP Ariba [[4]](https://www.casestudies.com/company/sap-ariba/case-study/increased-focus-on-higher-value-add-activities-as-a-result-of-global-e-procurement-journey) | probable |
| TMS et trésorerie | Twin (entité nommée : SSAB EMEA AB) [[5]](https://vakanser.se/jobb/ssab+-+middle+office+manager) ; UFW Unic Finance 2010 (entité nommée : SSAB EMEA AB) [[5]](https://vakanser.se/jobb/ssab+-+middle+office+manager) | probable |
| Financements court terme | Billets de trésorerie [[6]](https://www.ssab.com/company/investors/debt-financing) ; Committed back-stop facilities [[6]](https://www.ssab.com/company/investors/debt-financing) | confirmé |
| Signal récent | Première notation de crédit de SSAB par Moody's, attribuée au troisième trimestre 2026 [[1]](https://www.ssab.com/en/news/2026/10/report-for-q3-2026) | confirmé |

Le dossier complet : [`sorties/societes/ssab/`](sorties/societes/ssab/).

</details>

<details><summary><b>voestalpine</b></summary>

| Champ | Réponse | Niveau |
|---|---|---|
| Direction financière | Gerald Mayer, Chief Financial Officer (CFO) [[1]](https://reports.voestalpine.com/2526/ar/the-group/corporate-governance/management-board.html) ; Günther Pastl, Head of Group Treasury at voestalpine [[2]](https://mypodcast-voestalpine.podigee.io/18-neue-episode) | confirmé |
| ERP | SAP S/4HANA (entité nommée : voestalpine Steel Division) [[3]](https://www.voestalpine.com/group-it/en/NewsStories/S4HANA/?year=2023) | probable |
| Plateforme d'achats | SAP Ariba [[4]](https://www.voestalpine.com/group/en/group/supplier/) ; Jaggaer [[5]](https://www.casestudies.com/company/jaggaer/case-study/voestalpine-brings-the-local-market-global) | confirmé |
| TMS et trésorerie | Non trouvé | non trouvé |
| Financements court terme | Affacturage (recours non précisé) [[6]](https://reports.voestalpine.com/2526/ar/notes/other-notes/d-30-disclosures.html) ; Affacturage sans recours [[6]](https://reports.voestalpine.com/2526/ar/notes/other-notes/d-30-disclosures.html) ; Affacturage inversé (supply chain finance) [[7]](https://reports.voestalpine.com/2526/ar/notes/notes-to-the-statement-of-financial-position-equity-and-liabilities/d-23-supplier-finance-arrangements.html) | confirmé |
| Signal récent | Mandat du CFO du groupe, Gerald Mayer, renouvelé pour la période du 01/04/2027 au 31/03/2032 (2026) [[1]](https://reports.voestalpine.com/2526/ar/the-group/corporate-governance/management-board.html) | confirmé |

Le dossier complet : [`sorties/societes/voestalpine/`](sorties/societes/voestalpine/).

</details>

<details><summary><b>Barilla</b></summary>

| Champ | Réponse | Niveau |
|---|---|---|
| Direction financière | Oddone Incisa, directeur financier (Chief Financial Officer) du groupe Barilla [[1]](https://www.eunews.it/en/2025/07/10/barilla-group-appoints-oddone-incisa-as-cfo/) | probable |
| ERP | Non trouvé | non trouvé |
| Plateforme d'achats | SAP Ariba [[2]](https://webthesis.biblio.polito.it/15527/1/tesi.pdf) | probable |
| TMS et trésorerie | Kyriba [[3]](https://www.kyriba.com/news/kyriba-selected-by-barilla-to-provide-a-global-working-capital-treasury-risk-management-platform/) | probable |
| Financements court terme | Affacturage inversé (supply chain finance) [[3]](https://www.kyriba.com/news/kyriba-selected-by-barilla-to-provide-a-global-working-capital-treasury-risk-management-platform/) ; Escompte dynamique [[3]](https://www.kyriba.com/news/kyriba-selected-by-barilla-to-provide-a-global-working-capital-treasury-risk-management-platform/) | probable |

Le dossier complet : [`sorties/societes/barilla/`](sorties/societes/barilla/).

</details>

<details><summary><b>Stadler Rail</b></summary>

| Champ | Réponse | Niveau |
|---|---|---|
| Direction financière | Raphael Widmer, Group CFO [[1]](https://stadlerrail.com/en/group-executive-board) | probable |
| ERP | Infor [[2]](https://www.infor.com/de-de/resources/stadler-rail-gruppe) | probable |
| Plateforme d'achats | Non trouvé | non trouvé |
| TMS et trésorerie | Non trouvé | non trouvé |
| Financements court terme | Ligne de crédit renouvelable [[3]](https://chambers.com/articles/ubs-switzerland-ag-and-an-international-bank-syndicate-arrange-up-to-chf-2-8bn-financing-for-stadler) ; Betriebskredite (crédits d'exploitation) [[4]](https://a.storyblok.com/f/269997/x/68ae2197d7/stadler-halbjahresbericht-2026-de.pdf) | probable |
| Signal récent | Coûts des garanties bancaires, charges d'intérêts et d'impôts en hausse au premier semestre 2026 [[5]](https://www.bluewin.ch/en/news/stadler-reports-significantly-higher-revenue-and-operating-profit-in-the-first-half-of-the-year-li.3575699) | probable |

Le dossier complet : [`sorties/societes/stadler-rail/`](sorties/societes/stadler-rail/).

</details>

<details><summary><b>LVMH</b></summary>

| Champ | Réponse | Niveau |
|---|---|---|
| Direction financière | Cécile Cabanis, directrice financière (CFO) du groupe LVMH [[1]](https://www.lvmh.com/en/our-group/governance/cecile-cabanis) | confirmé |
| ERP | SAP S/4HANA (entité nommée : LVMH Perfumes & Cosmetics) [[2]](https://www.lvmh.com/join-us/our-job-offers/SSCPC02560) ; SAP ECC (entité nommée : Moët Hennessy) [[3]](https://leanix.net/en/blog/erp-mo%C3%ABt-hennessy) | probable |
| Plateforme d'achats | Aprovall (entité nommée : Moët Hennessy) [[4]](https://www.aprovall.com/?p=5410) | probable |
| TMS et trésorerie | Non trouvé | non trouvé |
| Financements court terme | Billets de trésorerie [[5]](https://www.lvmh.com/investors/investors-and-analysts/debt-financing/) | confirmé |
| Signal récent | Recrutement d'un chef de projet Trésorerie et communication bancaire, offre citant la Direction Projets Transformation Finance (2026) [[6]](https://www.lvmh.com/fr/nous-rejoindre/nos-offres/LVMH03235) | confirmé |

Le dossier complet : [`sorties/societes/lvmh/`](sorties/societes/lvmh/).

</details>

<details><summary><b>Vattenfall</b></summary>

| Champ | Réponse | Niveau |
|---|---|---|
| Direction financière | Kerstin Ahlfont, Chief Financial Officer [[1]](https://group.vattenfall.com/who-we-are/corporate-governance/group-management) ; Maria Paulinz, Head of Treasury [[2]](https://group.vattenfall.com/press-and-media/pressreleases/2022/maria-paulinz-new-head-of-treasury-at-vattenfall/) | confirmé |
| ERP | SAP S/4HANA (migration prévue ou en cours, d'après la page) [[3]](https://www.natuvion.com/success-stories/vattenfall-erp-consolidation/) ; SAP ERP [[4]](https://www.crxmarkets.com/en/successful-migration-of-vattenfalls-supply-chain-finance-data-during-sap-migration-2) | probable |
| Plateforme d'achats | SAP Ariba [[5]](https://group.vattenfall.com/uk/contentassets/8cd7332db68c478b9816eac515d0c605/sap_aribas_help_center.pdf) | probable |
| TMS et trésorerie | SAP Treasury [[6]](https://vakanser.se/jobb/system+manager+sap+treasury+m+f) | probable |
| Financements court terme | Billets de trésorerie [[7]](https://group.vattenfall.com/investors/funding-and-ratings/programmes-and-credit-facilities/) ; Ligne de crédit renouvelable [[7]](https://group.vattenfall.com/investors/funding-and-ratings/programmes-and-credit-facilities/) ; Back-up Credit Facility de 1 milliard d'euros [[7]](https://group.vattenfall.com/investors/funding-and-ratings/programmes-and-credit-facilities/) | confirmé |

Le dossier complet : [`sorties/societes/vattenfall/`](sorties/societes/vattenfall/).

</details>

<details><summary><b>Servier</b></summary>

| Champ | Réponse | Niveau |
|---|---|---|
| Direction financière | Pascal Lemaire, Executive Vice President Finance [[1]](https://servier.com/en/servier-group/executive-committee/) ; Cédric DONDAIN, trésorier international en charge de la gestion de crédit [[2]](https://www.coface.com/fr/actualites-economie-conseils-d-experts/servier-x-coface-programme-mondial-et-confiance-durable-pour-conquerir-de-nouveaux-marches) | confirmé |
| ERP | Non trouvé | non trouvé |
| Plateforme d'achats | Coupa [[3]](https://servier.fr/nos-engagements/relations-fournisseurs/travailler-avec-nous/) ; Determine (Corcentric) (seconde lecture) [[4]](https://www.corcentric.com/company/press-releases/servier-procurement-cloud/) ; Determine (Corcentric) (seconde lecture) [[5]](https://www.corcentric.com/company/press-releases/servier-group) | confirmé |
| TMS et trésorerie | Non trouvé | non trouvé |
| Financements court terme | Ligne de crédit renouvelable [[6]](https://www.whitecase.com/news/press-release/white-case-advises-servier-financing-edgewise-therapeutics-acquisition-and) | probable |
| Signal récent | Acquisition d'Edgewise (1,55 Md$ à la signature) finalisée le 13 juillet (2026) [[7]](https://european-biotechnology.com/latest-news/serviers-1-55b-edgewise-acquisition-backfires-after-phase-3-setback/) | probable |

Le dossier complet : [`sorties/societes/servier/`](sorties/societes/servier/).

</details>

<details><summary><b>Fresenius</b></summary>

| Champ | Réponse | Niveau |
|---|---|---|
| Direction financière | Sara Hennicken, Chief Financial Officer [[1]](https://report.fresenius.com/2025/annual-report/to-our-shareholders/management-board.html) ; Dirk Schreiber, Head of Group Treasury [[2]](https://www.nomentia.com/references/fresenius) | confirmé |
| ERP | SAP ECC [[3]](https://www.cio.de/article/3699040/it-management-in-tueckischem-gewaesser.html) ; SAP (seconde lecture) [[4]](https://www.fresenius.com/node/6625) ; SAP S/4HANA (entité nommée : Fresenius Kabi) (seconde lecture) [[5]](https://www.everestgrp.com/report/egr-2025-56-pp-7623) | probable |
| Plateforme d'achats | SAP Ariba (entité nommée : Fresenius Kabi) [[6]](https://fresenius-kabi.com/sap-ariba) | probable |
| TMS et trésorerie | TIP (Treasury Information Platform) (seconde lecture) [[7]](https://www.theglobaltreasurer.com/2019/04/11/twin-treasury-pillars-fx-risk-and-more-at-dax-listed-fresenius/) ; Nomentia [[2]](https://www.nomentia.com/references/fresenius) | probable |
| Financements court terme | Billets de trésorerie [[8]](https://report.fresenius.com/2025/annual-report/management-report/economic-report/financial-position.html) ; Ligne de crédit renouvelable [[8]](https://report.fresenius.com/2025/annual-report/management-report/economic-report/financial-position.html) ; Programmes de créances cités comme instrument [[8]](https://report.fresenius.com/2025/annual-report/management-report/economic-report/financial-position.html) | confirmé |
| Signal récent | Placement obligataire de 1 Md€ en deux tranches en 2025 (2026) [[8]](https://report.fresenius.com/2025/annual-report/management-report/economic-report/financial-position.html) | confirmé |

Le dossier complet : [`sorties/societes/fresenius/`](sorties/societes/fresenius/).

</details>

<details><summary><b>Nokia</b></summary>

| Champ | Réponse | Niveau |
|---|---|---|
| Direction financière | Marco Wirén, Chief Financial Officer (CFO) [[1]](https://www.fierce-network.com/broadband/ceo-hails-2025-foundational-year-nokia-sales-grow-3) ; Jani Relander, VP, Corporate Finance & Tax and Group Treasurer [[2]](https://www.eurofinance.com/news/trailblazing-the-digital-treasury) | probable |
| ERP | SAP S/4HANA (seconde lecture) [[3]](https://news.sap.com/?p=243821) | probable |
| Plateforme d'achats | SAP Ariba (entité nommée : Nokia Mobile Networks) [[4]](https://nokia.com/suppliers/rfx-guidance) | probable |
| TMS et trésorerie | TMS interne de Nokia [[5]](https://treasurytoday.com/asa-2019-winners/harnessing-the-power-of-technology-highly-commended-nokia/) ; TMS interne [[2]](https://www.eurofinance.com/news/trailblazing-the-digital-treasury) | probable |
| Financements court terme | Affacturage inversé (supply chain finance) [[6]](https://www.nokia.com/suppliers/supply-chain-finance/) ; Ligne de crédit renouvelable [[7]](https://www.sec.gov/Archives/edgar/data/924613/000110465926086081/tm2621179d1_6k.htm) ; Affacturage (recours non précisé) [[7]](https://www.sec.gov/Archives/edgar/data/924613/000110465926086081/tm2621179d1_6k.htm) | confirmé |
| Signal récent | Rapport du T3 2026 : Nokia prévoit 400 millions d'euros supplémentaires de fonds de roulement en 2026 [[9]](https://www.inderes.fi/en/releases/nokia-corporation-interim-report-for-q3-2026) | probable |

Le dossier complet : [`sorties/societes/nokia/`](sorties/societes/nokia/).

</details>

<details><summary><b>Saint-Gobain</b></summary>

| Champ | Réponse | Niveau |
|---|---|---|
| Direction financière | Maud Thuaudet, Chief Financial Officer [[1]](https://www.glassonweb.com/news/saint-gobain-announces-new-cfo-and-asia-pacific-ceo) ; Daniel Biarneix, Deputy Chief Financial Officer [[2]](https://www.lesrencontreseconomiques.fr/2025/en/speakers/daniel-biarneix/) | probable |
| ERP | SAP S/4HANA (migration prévue ou en cours, d'après la page) [[3]](https://www.casestudies.com/company/mulesoft/case-study/saint-gobain-deploys-90-workflows-in-6-months-with-mulesoft) | probable |
| Plateforme d'achats | Non trouvé | non trouvé |
| TMS et trésorerie | Non trouvé | non trouvé |
| Financements court terme | Affacturage inversé (supply chain finance) (entité nommée : Saint-Gobain China) [[4]](https://www.saint-gobain.com.cn/en/node/20560) ; Billets de trésorerie [[5]](https://www.finanzwire.com/press-release/saint-gobain-epa-sgo-first-half-2026-results-zWy3AgjYyxk) ; Ligne de crédit renouvelable [[5]](https://www.finanzwire.com/press-release/saint-gobain-epa-sgo-first-half-2026-results-zWy3AgjYyxk) | confirmé |
| Signal récent | Nomination d'Annica Hagen comme Chief Artificial Intelligence Officer et membre du Comité exécutif du Groupe (2026) [[6]](https://www.glassonweb.com/news/saint-gobain-appoints-annica-hagen-chief-artificial-intelligence-officer-and-accelerates-ai) | probable |

Le dossier complet : [`sorties/societes/saint-gobain/`](sorties/societes/saint-gobain/).

</details>

<details><summary><b>Deutsche Telekom</b></summary>

| Champ | Réponse | Niveau |
|---|---|---|
| Direction financière | Christian P. Illek, membre du directoire responsable des finances (directeur financier) [[1]](https://www.telekom.com/en/about-us/corporate-governance/board-of-management/profile-christian-p-illek) ; Dhananjay Mirchandani, directeur financier désigné (CFO), en fonction à compter du 1er mai 2027 [[2]](https://www.telekom.com/en/newsroom/latest-updates/media-information/2026/09/deutsche-telekom-reorganizes-leadership-functions) | confirmé |
| ERP | SAP S/4HANA (entité nommée : Deutsche Telekom IT) (migration prévue ou en cours, d'après la page) [[3]](https://www.t-systems.com/gb/en/success-stories/cloud-and-infrastructure/deutsche-telekom-it-moves-to-rise-with-sap) ; One-Finance Instance (OFI) [[4]](https://www.cio.de/article/4141604/sap-transformation-bei-der-telekom-weniger-systeme-mehr-standard-2.html) | probable |
| Plateforme d'achats | SAP Ariba [[5]](https://www.telekom.com/en/general/procurement) ; One.Source 2.0 [[5]](https://www.telekom.com/en/general/procurement) | confirmé |
| TMS et trésorerie | TIP (seconde lecture) [[6]](https://www.theglobaltreasurer.com/2019/03/13/digital-guarantee-management-with-tip-at-deutsche-telekom/) | probable |
| Financements court terme | Affacturage (recours non précisé) [[7]](https://report.telekom.com/annual-report-2025/notes/other-disclosures/43-financial-instruments-and-risk-management.html) ; Titrisation de créances (entité nommée : T‑Mobile US) [[8]](https://report.telekom.com/annual-report-2025/notes/notes-to-the-statement-of-financial-position/2-trade-receivables.html) ; Billets de trésorerie [[9]](https://www.telekom.com/en/investor-relations/debt-capital/financing-mix/commercial-paper-disclaimer/commercial-paper) | confirmé |
| Signal récent | Changement de directeur financier annoncé le 2 septembre 2026 : Dhananjay Mirchandani succède à Christian Illek le 1er mai 2027 [[2]](https://www.telekom.com/en/newsroom/latest-updates/media-information/2026/09/deutsche-telekom-reorganizes-leadership-functions) | confirmé |

Le dossier complet : [`sorties/societes/deutsche-telekom/`](sorties/societes/deutsche-telekom/).

</details>

<details><summary><b>Verallia</b></summary>

| Champ | Réponse | Niveau |
|---|---|---|
| Direction financière | Cristina Riesgo, Chief Financial Officer (directrice financière), à compter du 1er mars 2026 [[1]](https://www.verallia.com/en/communique-de-presse/cristina-riesgo/) | confirmé |
| ERP | SAP [[2]](https://www.lemondeinformatique.fr/actualites/lire-verallia-mise-sur-bonitasoft-pour-creer-des-applications-metiers-67870.html) | probable |
| Plateforme d'achats | Ivalua [[3]](https://www.casestudies.com/company/ivalua/case-study/verallia-group-customer-case-study) | probable |
| TMS et trésorerie | Non trouvé | non trouvé |
| Financements court terme | Affacturage (recours non précisé) [[4]](https://www.abcbourse.com/marches/obtention-du-consentement-des-preteurs-du-groupe-dans-le-cadre-de-loffre-publiq_664343) ; Billets de trésorerie [[5]](https://www.zonebourse.com/actualite-bourse/verallia-resultats-annuels-2025-croissance-organique-des-volumes-doublement-de-la-generation-de-ce7e5cdadf8ff126) ; Ligne de crédit renouvelable [[4]](https://www.abcbourse.com/marches/obtention-du-consentement-des-preteurs-du-groupe-dans-le-cadre-de-loffre-publiq_664343) | probable |
| Signal récent | Résultats du troisième trimestre 2026 : désendettement en cours, liquidité de 1.048 millions d'euros au 30 septembre 2026 [[6]](https://www.abcbourse.com/marches/verallia-chiffre-daffaires-en-baisse-au-t3-2026-marge-debitda-ajuste-preserv_705004) | probable |

Le dossier complet : [`sorties/societes/verallia/`](sorties/societes/verallia/).

</details>
<!-- /reponses -->

## Le principe

Le modèle cherche et lit les pages, puis remplit un schéma fermé. Le code relit chaque page citée, y retrouve la
citation mot pour mot, recalcule le type de source, contrôle la date et la présence de la société, puis fixe le niveau
de confiance par une table. Aucune cellule n'est corrigée à la main. Une erreur se corrige dans le code ou dans la
consigne du modèle, et la société est relancée.

La méthode complète, étape par étape, avec les décisions et leurs raisons, est dans [METHODOLOGIE.md](METHODOLOGIE.md).
Le cahier des charges et la planification sont dans [`conception/`](conception/).

## Ce que les journaux mesurent

- 185 trouvailles sur les douze sociétés. 163 passent les contrôles (55 confirmées, 107 probables, une absence
  déclarée) et 22 sont rejetées.
- Sur les 141 trouvailles dont le code a pu relire la page, 134 citations du modèle y sont retrouvées mot pour mot.
  Trois sont remplacées par un passage de la page qui porte la valeur, quatre sont écartées.
- Une société prend en moyenne 16,4 minutes d'agent et 5,7 millions de jetons traités, soit 2,39 $ estimés au tarif de
  liste de l'API. L'accès passe par un abonnement : ce chiffre est estimé, il n'est pas facturé.
- Des auditeurs d'un autre modèle (Opus 5.5) ont jugé 36 cellules tirées au sort, sans connaître leur niveau : 24 justes
  sur 33 vérifiables, 26 après deux règles d'affichage. Un second tirage de 12 cellules neuves, sur lequel se mesure la
  porte de 90 %, donne 9 justes sur 9 vérifiables. Une cellule tirée d'une page sur une filiale reste dans la fiche, la
  filiale signalée. Le détail est dans la feuille « Audit » de la cartographie.
- Le temps de construction, les jetons de tout le projet et les quatorze erreurs relevées sont détaillés dans
  [« Ton outil »](sorties/livrables/ton-outil.md).

## Reproduire

Python 3.12 et [uv](https://docs.astral.sh/uv/). Chrome ou Chromium pour le PDF des briefs.

```bash
cd outil
uv sync --frozen
uv run pytest -q
```

Les tests tournent hors ligne, sans réseau ni modèle. Pour recomposer les briefs et les tableurs depuis les fiches :

```bash
cd outil
PREPA_RDV_SORTIES=../sorties uv run python -m prepa_rdv livrables --ordre societes.csv
```

Pour préparer une société nouvelle, avec un abonnement Claude Code (`claude auth login`) :

```bash
cd outil
uv run python -m prepa_rdv societe "Nom de la société" --acces claude-cli
```

Les autres commandes et les accès au modèle sont décrits dans [`outil/README.md`](outil/README.md).

## Ce qui n'est pas publié, et pourquoi

- **Le plan de travail.** Il porte des notes personnelles. Ses décisions, de D1 à D24, sont reprises avec leurs raisons
  dans la méthodologie (section 8).
- **Le cache des pages lues** (`sorties/cache/`). Ce sont des textes de tiers. Chaque trouvaille garde l'adresse de sa
  page et sa citation, ce qui suffit pour vérifier.
- **Une adresse électronique nominative** que l'outil a déduite pour une société (motif prénom.nom) et que la société ne
  publie pas. Elle est retirée des fiches et des briefs de cette copie. Les adresses générales publiées restent.
- **Les chemins de la machine**, remplacés par `<racine>`. Trois phrases du cahier des charges, qui renvoyaient à
  d'autres travaux, sont reformulées.

## Comment cette copie est faite

La commande `prepa-rdv depot` construit ce dépôt depuis le dossier de travail. Elle copie une liste blanche, remplace
les chemins, applique des remplacements lus dans un fichier privé qui ne part pas, retire les adresses déduites et
recompose les briefs et les tableurs depuis les fiches nettoyées, puis la vitrine. Elle analyse ensuite chaque fichier, PDF et tableurs
compris, à la recherche de noms à taire, de secrets, de chemins de la machine et des adresses retirées. Elle écrit la
liste des licences et lance `pip-audit`. Elle ne publie que si l'analyse ne trouve rien.

## Licence

MIT, voir [LICENSE](LICENSE). Licences des dépendances : [LICENCES-TIERS.md](LICENCES-TIERS.md).
