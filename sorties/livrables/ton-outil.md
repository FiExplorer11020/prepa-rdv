# Ton outil : comment il fonctionne et où il s'est trompé

## En bref

L'outil prépare un rendez-vous avec la direction financière d'une société : il cherche son ERP, sa plateforme d'achats, son TMS et ses financements court terme en place, sur sources publiques. Chaque information porte une citation recopiée mot pour mot, l'adresse de la page, sa date et un niveau de confiance. Le modèle cherche et remplit un schéma fermé. Le code relit les pages, vérifie et note : le modèle ne note jamais sa propre confiance.

Sur 12 sociétés, l'outil a produit 185 trouvailles. 163 ont passé les contrôles, 22 ont été rejetées. Une société prend 16,4 minutes d'agent en moyenne, pour 5,7 millions de jetons traités, soit 2,39 $ au tarif de liste de l'API : c'est une estimation, car l'accès passe par un abonnement. Construction : 168 minutes de travail actif, planification comptée à part.

## La chaîne, en six étapes

| Étape | Qui | Ce qui en sort |
|---|---|---|
| 1. Résoudre l'entité | Code | Nom légal, pays, statut, site, domaines (Wikidata puis GLEIF ; table locale si Wikidata refuse le client) |
| 2. Chercher | Modèle | Plan de requêtes fixe par champ, en anglais et dans la langue du siège, écrit au journal |
| 3. Lire | Modèle | Pages web ouvertes par l'agent, jamais plus de 20 par société |
| 4. Extraire | Modèle | Trouvailles dans un schéma fermé : valeur d'une liste, citation de 25 mots au plus, adresse, date |
| 5. Vérifier et noter | Code | Page relue par le code, citation retrouvée mot pour mot (à défaut, le passage de la page le plus proche qui porte la valeur, au plus « probable »), type de source recalculé, société nommée, date dans la fenêtre, niveau par table |
| 6. Écrire | Code | Fiche, brief d'une page, deux tableurs, journaux |

## Outils et sources

- Python 3.12, `uv` (versions et empreintes figées), `pydantic` (schéma fermé), `httpx` (lecture polie : robots.txt, pause par hôte, cache), `trafilatura` et `pypdf` (HTML et PDF en texte), `RapidFuzz` (similarité des citations), `openpyxl` (tableurs), Chrome sans affichage (PDF).
- Le modèle passe par des sous-agents de Claude Code (recherche et lecture web du fournisseur) ou par `claude -p`. Pas de clé d'API.
- Sources : pages de la société, communiqués et études de cas des éditeurs, presse, offres d'emploi. Wikidata et GLEIF pour l'identité. Aucune base payante, ni LinkedIn.
- Jina Reader (service gratuit, 20 requêtes par minute) rend une page par JavaScript quand la lecture directe est pauvre et que la citation manque. Jamais après un refus du site.
- Un site qui refuse la lecture au code (robots.txt, HTTP 401, 403, 429) n'est jamais contourné. Une seconde lecture à l'aveugle par un autre agent, qui ne connaît pas la citation du premier, peut alors la confirmer. Les deux lectures s'accordent quand le plus court des deux textes se retrouve mot pour mot dans l'autre, sur six mots au moins qui nomment la valeur. Ces lignes ne dépassent jamais « probable », car le code n'a pas lu la page lui-même.
- Le code, les journaux et la méthode sont publiés sous licence MIT : https://github.com/FiExplorer11020/prepa-rdv

## Temps et coût par société

| Société | Durée de l'agent | Jetons traités | Jetons de sortie | Appels du modèle | Coût estimé ($) | Trouvailles | Confirmé | Probable | Rejetées |
|---|---|---|---|---|---|---|---|---|---|
| Barilla | 17,9 min | 6 695 845 | 122 623 | 33 | 2,65 | 19 | 0 | 15 | 4 |
| Deutsche Telekom | 16,8 min | 4 011 733 | 138 360 | 18 | 2,47 | 19 | 12 | 6 | 1 |
| Fresenius | 16,4 min | 7 067 318 | 106 359 | 37 | 2,35 | 18 | 6 | 9 | 2 |
| LVMH | 17,9 min | 5 202 400 | 118 862 | 24 | 2,32 | 9 | 4 | 5 | 0 |
| Nokia | 17,8 min | 6 048 909 | 129 848 | 28 | 2,55 | 20 | 1 | 18 | 1 |
| Saint-Gobain | 17,4 min | 5 155 906 | 133 102 | 23 | 2,64 | 14 | 1 | 12 | 1 |
| Servier | 15,7 min | 6 341 107 | 107 536 | 32 | 2,29 | 12 | 2 | 5 | 5 |
| SSAB | 13,8 min | 4 423 482 | 104 691 | 21 | 2,08 | 18 | 8 | 6 | 4 |
| Stadler Rail | 14,7 min | 3 871 198 | 113 351 | 19 | 2,11 | 11 | 2 | 6 | 3 |
| Vattenfall | 13,2 min | 4 078 819 | 105 019 | 20 | 2,05 | 14 | 4 | 9 | 1 |
| Verallia | 19,0 min | 9 705 102 | 124 582 | 49 | 2,86 | 15 | 3 | 12 | 0 |
| voestalpine | 16,2 min | 5 982 479 | 105 975 | 29 | 2,26 | 16 | 12 | 4 | 0 |

Le coût est estimé au tarif de liste de l'API (Sonnet 5.5). Il n'est pas facturé : l'accès passe par un abonnement. Les jetons lus dans le cache dominent les totaux, car Claude Code relit son contexte à chaque appel.

## Le prompt principal

Version `6ee5257d0713`. Le texte de consignes envoyé à chaque agent, sans la demande propre à la société :

```text
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

```

## Où l'outil s'est trompé

14 erreurs relevées par les contrôles du code (5 citation inventée, 3 entité, 2 page lue incomplète, 2 citation reformulée, 2 autre). 5 sont corrigées, avec un changement et une relance. 9 sont écartées sans réparation possible : la trouvaille reste « non trouvé » et n'atteint ni le brief ni la cartographie. « Page lue incomplète » est une erreur du lecteur de l'outil, pas du modèle. Quatre exemples, un par cause quand c'est possible :

1. **Barilla, tms et trésorerie.** Écrit par l'outil : Kyriba : « Kyriba è stata scelta da Barilla per fornire una piattaforma globale di Working Capital, Treasury e Risk Management ». Vu par le contrôle 1 : citation dans le texte relu (similarité 0,63). Ce que dit la page : Kyriba è stata scelta da Barilla per fornire una piattaforma globale di Working Capital, Treasury e Risk Management. La phrase figure dans la page rendue, de 28 285 caractères, contre 2 418 à la lecture directe. Cause : page lue incomplète. Changement : Quand la citation du modèle manque et que la page lue directement est pauvre (moins de 4 000 caractères), le code relit la page rendue par JavaScript (Jina Reader) avant de conclure. Deux tests couvrent ce cas. Le journal avait d'abord classé l'erreur chez le modèle, alors que la lecture directe avait perdu la phrase. Relance : Société relancée sur la même réponse de l'agent (run 20261113T232420Z) : barilla-tms-12 passe de « non trouvé » à « probable », citation du modèle retrouvée mot pour mot dans la page rendue.
2. **Nokia, direction financière.** Écrit par l'outil : Daniel Gramunt, Head of Cash Management : « Daniel Gramunt, Head of Cash Management, Nokia ». Vu par le contrôle 1 : citation dans le texte relu (similarité 0,83). Ce que dit la page : Daniel Gramunt, Nokia’s Head of Cash Management, adds that the company has been able to achieve fully-automated reconciliation of its Sales of Receivables (SoR) transactions. Cause : citation reformulée. Changement : Le code garde le passage de la page le plus proche, qui porte la valeur et la société, à la place de la citation du modèle (verificateur.reparer_citation) ; niveau plafonné à « probable ». Relance : même passage (20261113T232118Z) : trouvaille gardée avec le passage de la page, niveau probable.
3. **Vattenfall, financements court terme.** Écrit par l'outil : Affacturage inversé (supply chain finance) : « The agreed partnership comprises the implementation of an supply chain finance program in Vattenfall’s operations in Germany ». Vu par le contrôle 1 : citation dans le texte relu (similarité 0,55). Ce que dit la page : CRX Markets signs up Vattenfall in a supply chain finance program. Cause : citation inventée. Changement : Le code garde le passage de la page le plus proche, qui porte la valeur et la société, à la place de la citation du modèle (verificateur.reparer_citation) ; niveau plafonné à « probable ». Relance : même passage (20261113T232116Z) : trouvaille gardée avec le passage de la page, niveau probable.
4. **Saint-Gobain, signal récent.** Écrit par l'outil : Nomination d'Annica Hagen comme Chief Artificial Intelligence Officer et membre du Comité exécutif du Groupe : « Annica Hagen has been appointed Chief Artificial Intelligence Officer (CAIO) and member of the Group Executive Committee ». Vu par le contrôle 1 : citation dans le texte relu (similarité 0,46). Ce que dit la page : Annica Hagen has been appointed Chief Artificial Intelligence Officer (CAIO) and member of the Group Executive Committee, effective September 1, 2026. La phrase figure dans la page rendue, de 18 842 caractères, contre 898 à la lecture directe. Cause : page lue incomplète. Changement : Quand la citation du modèle manque et que la page lue directement est pauvre (moins de 4 000 caractères), le code relit la page rendue par JavaScript (Jina Reader) avant de conclure. Deux tests couvrent ce cas. Le journal avait d'abord classé l'erreur chez le modèle, alors que la lecture directe avait perdu la phrase. Relance : Société relancée sur la même réponse de l'agent (run 20261113T232425Z) : saint-gobain-signal-14 passe de « non trouvé » à « probable », citation du modèle retrouvée mot pour mot dans la page rendue.

Le journal complet est dans `sorties/journal/erreurs.jsonl`. Une erreur sans changement associé n'est pas comptée comme corrigée.

## Ce que les contrôles voient, et ce qu'ils laissent passer

- Rejets par motif : citation introuvable (14), société non nommée (6), page introuvable (2).
- Trouvailles gardées mais hors fenêtre de fraîcheur ou sans date : 47 sur 163, soit 29 %. Sous la moitié : les fenêtres de départ restent (24 mois pour la société, 36 pour un tiers qui la nomme, 24 pour la presse, 12 pour un signal indirect), sans fenêtres par champ.
- Pages lues par le code : 98. Pages refusées ou illisibles pour lui : 17.
- Sur les 141 trouvailles dont la page a pu être lue par le code (constats d'identité exclus), 134 citations du modèle sont retrouvées mot pour mot (95,0 %), 3 sont réparées par un passage de la page et 4 sont écartées.
- Relecture à l'aveugle : 26 lignes relues par un second agent, dont 15 s'accordent avec la première lecture et passent à « probable ». Les autres restent écartées : page fermée au second agent aussi, autre phrase de la même page, passage trop court ou qui ne nomme pas le produit. Le second agent de Barilla a d'abord été arrêté par un garde-fou de l'API, avant d'écrire. Relancé avec un autre modèle (Opus 5.5), il a pu ouvrir la page de 6 lignes sur 8, et 4 s'accordent avec la première lecture.
- Une erreur du contrôle lui-même : le code cherchait la citation du premier agent (25 mots au plus) dans le passage du second (15 mots au plus). Le test échouait dès que la citation était la plus longue des deux, et il a rejeté à tort des lectures concordantes. Il cherche désormais le plus court des deux textes dans l'autre. Sur les 18 lignes relues avant la relance, l'accord passe de 5 à 11.
- Citations que le code a réparées en gardant un passage de la page : 3. Pages relues rendues par JavaScript : 10.
- Une page de base de données commerciale (type P5) ne sert que de second avis : une valeur qu'elle seule nomme reste dans le tableur des trouvailles, pas dans le brief. Trouvailles concernées sur ce lot : 2.
- Audit : 36 cellules de la cartographie, tirées au sort avec une graine fixe, ont été jugées par 3 sous-agents auditeurs, un par lot, d'un autre modèle que les agents de recherche (Opus 5.5). L'auditeur ouvre chaque lien et dit si la page soutient la valeur, sans connaître le niveau donné par l'outil. Verdicts : 24 justes, 7 partielles, 2 fausses, 3 invérifiables. Sur les 33 cellules vérifiables, 24 sont justes (73 %). Écarts relevés : LVMH, plateforme d'achats (partiel, filiale ou division) ; Servier, signal récent (partiel, précision non soutenue) ; Deutsche Telekom, ERP (partiel, filiale ou division) ; Fresenius, plateforme d'achats (partiel, filiale ou division) ; Saint-Gobain, ERP (faux, projet ou évaluation) ; Saint-Gobain, financements court terme (partiel, filiale ou division) ; LVMH, ERP (partiel, filiale ou division) ; Vattenfall, ERP (faux, projet ou évaluation) ; SSAB, ERP (partiel, filiale ou division). Le détail, cellule par cellule, est dans la feuille « Audit » de `cartographie.xlsx`.
- Après l'audit : 8 des 9 écarts venaient de deux oublis d'affichage, notés par l'auditeur « filiale ou division » (6) et « projet ou évaluation » (2). Le modèle avait relevé l'entité que la page nomme et, dans son commentaire, que la migration était prévue ; la cellule ne gardait que le produit. Deux règles l'écrivent désormais dans la cellule, au brief, à la cartographie et à l'audit (D21) : l'entité nommée quand ce n'est pas la société, et « migration prévue ou en cours » pour un ERP, une plateforme d'achats ou un TMS. Les niveaux ne changent pas. Un nouvel auditeur a rejugé les 9 cellules telles qu'elles s'affichent : 2 justes, 7 partielles, 0 fausse, 0 invérifiable. Avec la règle du projet, 2 sur 2 cellules « projet ou évaluation » deviennent justes. Avec celle de l'entité, aucun des 6 verdicts « filiale ou division » ne change, l'auditeur jugeant toujours qu'une page sur une filiale ne dit pas le système du groupe. Une cellule tirée d'une page sur une filiale reste dans la fiche, la filiale signalée comme le prévoit le cahier des charges, et sa valeur se vérifie pour le groupe pendant le rendez-vous (D22). Le premier tirage passe ainsi à 26 sur 33 vérifiables (79 %). Un second tirage de 12 cellules nouvelles (graine 2027), que les règles n'avaient pas vues, donne 9 justes, 0 partielle, 0 fausse, 3 invérifiables, soit 9 sur 9 vérifiables (100 %). La porte G4, fixée à 90 %, se mesure sur ce tirage plutôt que sur le premier, qui a servi à écrire les règles, et elle est passée. L'échantillon reste petit, et une seule de ces cellules jugée fausse l'aurait mis à 89 %.
- Ce que le code ne voit pas : une citation exacte qui ne dit pas ce que l'outil en conclut. L'auditeur la cherche, mais c'est un modèle qui en juge un autre : ses verdicts partiels et faux sont les premiers à relire par une personne.

## Jetons de tout le projet

| | Appels | Entrée fraîche | Cache écrit | Cache lu | Sortie | Total traité | Coût estimé ($) |
|---|---|---|---|---|---|---|---|
| dev / construction | 567 | 1 136 | 2 931 725 | 228 805 997 | 1 148 713 | 232 887 571 | 65,93 |
| dev / planification | 226 | 452 | 3 083 404 | 83 036 656 | 1 236 962 | 87 357 474 | 31,78 |
| outil / audit | 35 | 78 | 817 973 | 4 840 297 | 188 478 | 5 846 826 | 8,83 |
| outil / run | 317 | 648 | 3 473 302 | 58 514 831 | 1 354 289 | 63 343 070 | 28,59 |
| outil / sonde | 64 | 132 | 786 046 | 12 070 573 | 282 380 | 13 139 131 | 6,00 |
| **Total du cas** | 1 209 | 2 446 | 11 092 450 | 387 268 354 | 4 210 822 | 402 574 072 | 141,13 |

Coût estimé au tarif de liste du modèle de chaque appel, par million de jetons : Sonnet 5.5 à 2 $ en entrée, 10 $ en sortie et 0,10 $ en lecture du cache ; Opus 5.5 à 4 $ en entrée, 20 $ en sortie et 0,20 $ en lecture du cache. Ce n'est pas une facture : l'accès passe par un abonnement ou par un compte non facturé. Les jetons lus dans le cache dominent le total, car Claude Code relit tout son contexte à chaque appel.

Hors du cas (une session antérieure du même dossier, sans lien avec l'outil) : 648 766 jetons traités, 0,78 $ estimés.

### Par société (appels de l'outil)

| Société | Appels | Entrée fraîche | Cache écrit | Cache lu | Sortie | Total traité | Coût estimé ($) |
|---|---|---|---|---|---|---|---|
| Barilla | 39 | 82 | 474 933 | 6 981 567 | 127 846 | 7 584 428 | 3,68 |
| Deutsche Telekom | 24 | 48 | 397 983 | 4 358 422 | 144 164 | 4 900 617 | 2,87 |
| Fresenius | 44 | 90 | 414 509 | 7 761 675 | 166 629 | 8 342 903 | 3,48 |
| LVMH | 24 | 50 | 261 013 | 4 822 475 | 118 862 | 5 202 400 | 2,32 |
| Nokia | 35 | 70 | 414 538 | 6 620 567 | 164 764 | 7 199 939 | 3,35 |
| SSAB | 29 | 58 | 411 641 | 5 259 287 | 160 669 | 5 831 655 | 3,16 |
| Saint-Gobain | 31 | 64 | 465 511 | 5 817 954 | 159 757 | 6 443 286 | 3,34 |
| Servier | 38 | 78 | 389 324 | 6 804 922 | 145 051 | 7 339 375 | 3,10 |
| Stadler Rail | 19 | 40 | 249 451 | 3 508 356 | 113 351 | 3 871 198 | 2,11 |
| Vattenfall | 20 | 40 | 252 675 | 3 721 085 | 105 019 | 4 078 819 | 2,05 |
| Verallia | 49 | 100 | 273 977 | 9 306 443 | 124 582 | 9 705 102 | 2,86 |
| voestalpine | 29 | 60 | 253 793 | 5 622 651 | 105 975 | 5 982 479 | 2,26 |

Temps de construction actif : 168 minutes (plafond du cas : 180).

Le tableau par société compte aussi les secondes lectures, d'où des totaux plus hauts que dans le tableau des temps et coûts, qui ne compte que l'agent de recherche. Chaque appel est compté au tarif du modèle qui l'a fait : Sonnet 5.5 pour les agents de recherche et les secondes lectures, Opus 5.5 pour la seconde lecture relancée de Barilla.
