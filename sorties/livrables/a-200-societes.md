# Et à 200 sociétés ? Ce qui casse, et ce que je changerais

## Coût et temps, d'après les 12 sociétés mesurées

- Une société coûte en médiane 5,6 millions de jetons traités, dont 116 mille de sortie, soit 2,34 $ au tarif de liste de l'API. Pour 200 sociétés : environ 470 $. C'est une estimation, car l'accès passe par un abonnement. La remise de moitié du traitement par lots ne s'applique pas telle quelle à un agent qui lit le web en plusieurs tours : je ne la compte pas.
- 93 % des jetons sont de la relecture du contexte à chaque appel de l'agent (cache lu). À 200 sociétés, des boucles plus courtes (moins de pages ouvertes par l'agent, lecture et vérification laissées au code) pèsent donc plus que le prix du jeton.
- Une société prend en médiane 16,6 minutes d'agent. À dix agents en parallèle, comme pour ces douze sociétés, 200 sociétés tiennent en 5,5 heures ; à quatre agents, en 13,8 heures.
- La relecture humaine pèse plus que les jetons : dix minutes par société font 33 heures (hypothèse), contre 470 $ de jetons.

## Sources, gratuites et payantes

- Gratuites et déjà utilisées : pages de la société, communiqués et études de cas des éditeurs, presse, offres d'emploi, Wikidata, GLEIF. Les rapports annuels s'ajoutent à 200, pays par pays (ESEF n'a ni l'Allemagne ni la Suisse).
- Payantes, en second avis seulement : une base de technologies d'entreprise et une base de contacts, sous contrat. Elles ne remplacent pas la citation : un niveau « confirmé » exige toujours un document daté.

## Ce qui casse

| Ce qui casse | Pourquoi | Ce que je change |
|---|---|---|
| La lecture par le code | 15 % des adresses sont refusées ou illisibles pour le code (robots.txt, HTTP 403). Un second agent s'accorde avec la première lecture sur 15 lignes sur 26 (58 %) | Un accord de lecture avec les sites qui comptent, ou un fournisseur de pages sous contrat. La seconde lecture reste plafonnée à « probable » |
| Les pages que le code lit mal | La lecture directe ne garde parfois qu'une fraction du texte d'une page construite par JavaScript (2 418 caractères sur 28 285 pour une page de Barilla). 10 pages ont dû être relues rendues, et 2 citations que le journal avait d'abord mises sur le compte du modèle venaient de là | Le rendu JavaScript quand la lecture est pauvre, déjà en place. À 200, un navigateur sans affichage sous contrôle plutôt qu'un service tiers |
| La citation reformulée par le modèle | Le modèle recopie parfois de mémoire : 3 citations sur 163 gardées ont dû être remplacées par un passage de la page | Le passage de la page qui porte la valeur, plafonné à « probable ». Un modèle moins cher en extraction (Haiku 5.5) se teste sur ce jeu |
| La résolution d'entité | Homonymes, filiales, groupes à périmètre flou. Wikidata exige un contact ; GLEIF ne cherche pas bien par nom | Wikidata d'abord avec un contact déclaré, GLEIF pour contrôler le LEI, validation humaine sous un seuil de score |
| La fraîcheur | 29 % des trouvailles gardées sont hors de leur fenêtre. Une fiche vieillit : un rapport, une offre, un communiqué changent la donnée | Déclencheurs par source, empreinte par page, recalcul du seul champ touché, péremption par type de preuve |
| La relecture humaine | 33 heures (hypothèse) | Échantillon stratifié, rejets automatiques seulement après 30 verdicts et 90 % de concordance sur quatre semaines (hypothèse), relecture complète limitée aux financements avant un rendez-vous |
| Les limites d'usage | Un abonnement a des plafonds, une API des limites de débit. Un garde-fou du fournisseur a arrêté une seconde lecture, passée ensuite avec un autre modèle | Compte dédié, lots de quatre à dix, reprise sur cache, calendrier lissé. Une société arrêtée reprend sans refaire les autres |

## Contrôle qualité

- Sur le lot mesuré, 12 % des trouvailles proposées par le modèle sont rejetées par les contrôles du code. À 200, ce taux se suit par modèle et par version de consigne.
- Relu par une personne, le jeu des 12 sociétés se rejoue à chaque changement de modèle ou de consigne.
- Audit d'un échantillon tiré au sort par un auditeur d'un autre modèle, pour la citation exacte dont la conclusion est fausse ; une personne relit ses écarts. Mesuré ici : 24 justes sur 33 vérifiables au premier tirage, 26 après deux règles d'affichage, 9 sur 9 au second, 0,15 $ estimés par cellule.

## Mise à jour des fiches

Chaque fiche porte la date de lecture, l'empreinte de chaque page et la version du prompt. Une relance ne refait que les champs dont la page a changé ; une preuve hors de sa fenêtre redescend à « probable ».

## Où brancher le résultat, et précautions

- Brancher : fiche jointe au rendez-vous, puis champs du CRM en proposition validée par un commercial (jamais d'écriture directe), puis synthèse du panel pour la feuille de route des branchements d'ERP.
- Précautions : lecture seule, provenance par champ, validation humaine avant écriture, aucune donnée interne envoyée au modèle tant que la conformité n'a pas validé le fournisseur, contacts en suggestion non vérifiée avec interrupteur, registre des jetons et des appels, plafond de dépense par lot.
