# Cahier des charges : l'outil de briefs pour CA|ES

Version 2 du 13 novembre 2026. Ce document fixe les exigences, les données, les sorties, les tests et les risques. Le plan (plan-2026-11-13.md) garde les décisions et les réponses aux questions d'Oscar. La planification (planification-2026-11-13.md) donne l'ordre et les durées.

Marques du projet. **[P]** page officielle ouverte le 13 novembre 2026. **[S]** relayé par un tiers, à vérifier. **[L]** lu dans les fichiers d'Oscar ou dans le dépôt. **[N]** constaté ou mesuré ce jour. **[H]** hypothèse à mesurer : un chiffre [H] n'est pas une mesure. **[O]** décision d'Oscar le 13 novembre.

## 1. Objet et contexte

**Le cas.** Une filiale du groupe Crédit Agricole veut rencontrer 20 grandes entreprises avec CA|ES, pour des services financiers intégrés aux ERP (scénario fictif). L'outil prépare chaque rendez-vous avec la direction financière à partir d'informations publiques. Il identifie les outils utilisés (ERP, plateforme d'achats, TMS) et les financements court terme déjà en place (affacturage, titrisation de créances, supply chain finance). Il tourne sur 12 sociétés : SSAB, voestalpine, Barilla, Stadler Rail, LVMH, Vattenfall, Servier, Fresenius, Nokia, Saint-Gobain, Deutsche Telekom, Verallia. Huit autres servent à une démo en direct.

**Ce qui est évalué.** La démarche, l'usage de l'IA et ce qui a été automatisé comptent autant que les pages obtenues. Quatre livrables sont demandés. Un PDF de 12 briefs d'une page. Un tableur avec lien de source et niveau de confiance par information. Un texte sur l'outil : étapes, sources, temps et coût par société, prompt principal, au moins deux erreurs détectées. Un texte sur le passage à 200 sociétés. C'est l'outil qui fait le travail. Le plafond est de trois heures.

**Décisions de cadrage d'Oscar [O].**

1. « Gratuit » couvre les sources et les outils. Les jetons du modèle restent payés sur la Console Claude, dans un espace de travail plafonné.
2. Les briefs portent des contacts en suggestion non vérifiée (section 10).
3. Le dépôt de l'outil est public, sous licence MIT.

**Ce que l'outil n'est pas.** Ce n'est pas un outil de prospection. Il n'envoie rien. Il ne lit pas LinkedIn. Il ne constitue pas une base de contacts.

## 2. Lecteurs et usages

| Lecteur | Ce qu'il lit | Ce qu'il attend |
|---|---|---|
| Directeur général de CA|ES | Les 12 briefs | Savoir en 90 secondes [H] ce qu'on sait, quoi proposer, quoi demander |
| Évaluateurs de La Fabrique | Tableur, textes, dépôt, démo | La démarche, les preuves, les erreurs, le coût, ce qui est automatisé |
| Oscar | Briefs, feuille d'audit, textes | Des chiffres opposables et un temps de relecture tenu |
| Public de la démo | Écran partagé | Une société traitée de bout en bout, sans panne |
| Conformité de CA (lecteur futur) | Précautions, journal, licences | Qu'une donnée a une source, qu'aucune donnée privée n'entre |

## 3. Périmètre

**Dans le cas.**

- 12 sociétés nommées et 8 en démo.
- Quatre champs métier : ERP, plateforme d'achats, TMS et trésorerie, financements court terme. Plus l'identité, la direction financière, les signaux des 12 derniers mois et les contacts en suggestion.
- Des sources publiques gratuites.
- Les sorties : 12 briefs en PDF, 2 tableurs, 2 textes, le dépôt, la démo. La vitrine web et la synthèse du panel viennent après.

**Hors du cas.**

- LinkedIn, Apollo, toute base payante, tout contournement de blocage.
- Les lignes directes de téléphone, les sondes SMTP, tout envoi de message.
- Le branchement réel à un CRM.
- Toute information privée : CA|ES, ses clients, les clients d'Oscar.
- Une offre commerciale ou un prix.

## 4. Exigences fonctionnelles

Priorité : **M** nécessaire aux quatre livrables, **S** souhaitable, **C** si le temps reste.

| ID | Exigence | P | Critère d'acceptation |
|---|---|---|---|
| F1 | Entrée : un nom de société, ou un fichier CSV de noms. Sortie : un dossier par société | M | `outil run "Nokia"` crée `fiche.json`, `brief.html`, `journal.jsonl` |
| F2 | Résolution d'entité : nom légal du groupe, pays, statut (coté, privé, public), ISIN, LEI, site de relations investisseurs, périmètre retenu, alias | M | 12 sociétés sur 12 résolues ou marquées « à confirmer » avec la raison. LEI contrôlé par GLEIF |
| F3 | Plan de requêtes fixe par champ, en anglais et dans la langue du siège, écrit au journal | M | Aucun champ « non trouvé » sans que le journal montre le plan complet |
| F4 | Recherche et lecture de pages web par l'agent du fournisseur, avec plafonds d'usage par champ et par société | M | `max_uses` posé sur chaque outil ; le coût d'une société reste sous son budget |
| F5 | Lecture locale des rapports annuels : téléchargement poli, texte, fenêtres autour de mots-clés multilingues, passage au modèle | M | Sur Saint-Gobain, la note sur le financement fournisseur ou l'affacturage est retrouvée si elle existe. Sinon le journal liste les fenêtres examinées |
| F6 | Extraction en schéma fermé : valeur, citation recopiée (25 mots au plus), langue, adresse, date de la source, type de preuve | M | 100 % des trouvailles valident le schéma. Une citation de plus de 25 mots est refusée par le code |
| F7 | Vérification par le code : six contrôles (section 6.5) | M | Tests hors ligne. Une citation inventée est rejetée |
| F8 | Niveau de confiance calculé par la table (section 6.4) | M | Au moins 20 cas de test de la table, tous verts |
| F9 | Brief d'une page selon le gabarit (section 7) | M | 12 PDF d'une page, aucun texte coupé, aucun nombre absent de la fiche, angle marqué « hypothèse » |
| F10 | Tableur en deux fichiers (section 8) | M | Colonnes conformes, ouverture sans erreur, 10 Mo au plus par fichier |
| F11 | Un seul PDF de 12 pages | M | 10 Mo au plus, 12 pages relues une à une |
| F12 | Journal de run : durée, jetons (entrée, sortie, cache lu, cache écrit), recherches, lectures, coût calculé, erreurs | M | La somme des coûts par société égale le coût total. Écart avec l'usage de l'espace de travail de 5 % au plus [H] |
| F13 | Journal d'erreurs (section 9) | M | Au moins 2 erreurs réelles, chacune avec cause, contrôle détecteur, correction et relance |
| F14 | Feuille d'audit : 36 cellules tirées au sort avec une graine fixe | M | Oscar note juste ou faux ; un script calcule la justesse |
| F15 | Témoin naïf : les 12 sociétés en une requête d'une ligne, sans vérification | S | Les erreurs du témoin sont comptées et comparées |
| F16 | Contacts en suggestion non vérifiée (section 10) | M [O] | Seulement pour le directeur financier nommé par la société. Interrupteur `--sans-contacts` |
| F17 | Plafonds de coût : par appel, par société, par lot | M | Un test à plafond bas arrête le run sans perte et reprend |
| F18 | Reprise et cache : une relance ne refait que ce qui a changé ou échoué. Sources brutes gardées avec empreinte | M | Un second run identique ne fait aucun appel réseau pour les étapes en cache |
| F19 | Mode démo : n sociétés avec montée progressive, progression visible par étape, brief qui s'ouvre | M | 8 sociétés d'essai sans panne. Temps relevé |
| F20 | Synthèse du panel : une page | C | Répartition des ERP, plateformes et financements trouvés |
| F21 | Vitrine statique sur Vercel | C | Lien ouvert sans compte, `noindex`, sans clé |
| F22 | Export « CRM » en CSV et JSON, avec le schéma des champs | C | Import à blanc dans un tableur |
| F23 | Mise à jour d'un champ : recalcul ciblé par empreinte de source | C | Une page modifiée ne relance que son champ |
| F26 | Seconde lecture à l'aveugle des pages que le code n'a pas le droit de lire (robots.txt, HTTP 401, 403, 429) : un autre sous-agent reçoit l'adresse et le sujet, sans la citation du premier, et recopie le passage. Le code compare les deux textes | S | Deux lectures indépendantes qui s'accordent à 0,95 valent « probable », jamais « confirmé ». L'accord se cherche dans les deux sens : la citation du premier dans le passage relu, ou le passage relu (6 mots au moins, qui nomment la valeur) dans la citation (D18). Une lecture qui ne concorde pas est rejetée. Le mode de vérification est écrit dans la trouvaille |
| F27 | Bilan d'un lot et journal d'erreurs : niveaux, motifs de rejet, part hors fenêtre, pages refusées, jetons. Le code relève les erreurs que ses contrôles voient, le changement et la relance s'ajoutent après coup | M | `prepa-rdv bilan` et `prepa-rdv erreurs`. Une erreur sans changement n'est pas comptée comme corrigée |
| F28 | Les deux textes (« Ton outil », « Et à 200 sociétés ? ») sont produits depuis les fiches, le bilan, le registre des jetons et le journal d'erreurs | M | `prepa-rdv textes` écrit les sources Markdown et les PDF. Aucun nombre n'est tapé à la main |
| F25 | Accès au modèle par sous-agents d'une session de Claude Code [O] : `prepa-rdv demander` écrit une demande par société (consignes, plan de requêtes, schéma, chemin de la réponse), un sous-agent écrit `agent-sortie.json`, `prepa-rdv recevoir` valide la réponse et enregistre l'agent | M | Une réponse hors schéma est refusée avec sa raison. Les jetons de l'agent se comptent une fois, pour la société et la phase. Une relance ne rappelle pas l'agent |
| F24 | Registre des jetons du projet [O]. Chaque appel au modèle de l'outil écrit une ligne. Elle porte société, phase, modèle, jetons d'entrée et de sortie, jetons du cache, recherches, durée et coût estimé au tarif de liste. Les sessions de développement de Claude Code se comptent à part, d'après leurs transcriptions. Un rapport réunit les deux | M | `prepa-rdv jetons` donne le total du projet par phase (planification, construction, essai, sonde, run, audit, démo) et par société. Le registre est en ajout seul |

## 5. Exigences non fonctionnelles

| Catégorie | Exigence | Mesure |
|---|---|---|
| Coût | Plan C [O] : sans clé de la Console, le modèle passe par `claude -p` sur l'abonnement. La mesure est le jeton, le coût en dollars est estimé au tarif de liste et n'est pas facturé. Avec une clé de la Console : plafond de l'espace de travail à 50 $ au départ [H]. Le poids de base de Claude Code se mesure par un appel à vide | Registre des jetons (F24). Avec une clé : page d'usage et de coût de la Console, ou API d'usage avec une clé d'administration (organisation requise) [P] |
| Temps | Une société en 3 à 6 minutes pour le chemin ciblé [H]. Le décompte des trois heures est écrit dans le texte | Journal de run |
| Qualité | 95 % des citations proposées passent la vérification [H]. 90 % de justesse sur l'échantillon relu [H]. Aucun nombre du brief sans source dans la fiche | Tests, feuille d'audit |
| Reproductibilité | Chaque fiche porte la version de l'outil, le modèle, le prompt (empreinte) et l'empreinte de chaque source. Les dépendances sont épinglées dans un fichier de verrouillage | Champs de la fiche, `uv.lock` |
| Sécurité | Clé dans une variable d'environnement, jamais dans le dépôt ni dans les journaux. Analyse des secrets avant publication. Dépendances épinglées avec empreintes, analysées par `pip-audit` (R17) | Test, outil libre d'analyse |
| Conformité | robots.txt respecté, identité joignable dans l'en-tête, débit par hôte (Wikidata : 5 requêtes parallèles par IP au plus [P : agent]), pas de proxys. Contacts : section 10 | Tests, revue |
| Confidentialité | Aucun nom de client d'Oscar, aucune donnée privée de ses autres travaux dans les entrées, les prompts, les sorties et le dépôt | `grep` des noms avant publication |
| Licences | Dépôt MIT. Dépendances sous licence permissive (MIT, BSD, Apache-2.0). Les projets AGPL ou GPL ne s'importent pas : PyMuPDF, `py-xbrl`, les empreintes de Wappalyzer, Firecrawl. SearXNG, s'il sert, reste un service séparé | Liste des licences au README, contrôle avant publication |
| Maintenabilité | Tests hors ligne, types, README, une commande par action | `pytest` vert, README suivi sur une machine propre |
| Observabilité | Journal JSONL par société, prompts versionnés | Fichiers du dossier de sortie |
| Accessibilité des livrables | PDF au texte sélectionnable, polices embarquées, contraste suffisant | Relecture |
| Langue | Briefs en français. Citations dans la langue de la source, avec traduction française marquée comme telle | Schéma de la trouvaille |
| Disponibilité en démo | Mode dégradé : cache, société déjà traitée à montrer, répétition la veille | Répétition |

## 6. Données

### 6.1 La trouvaille

Une trouvaille est une information sur une société, avec sa preuve. Elle a ces champs.

| Champ | Type | Règle |
|---|---|---|
| `id` | texte | Dérivé de la société, du champ et d'un rang |
| `societe` | texte | Nom du groupe retenu à l'étape 1 |
| `champ` | liste | `identite`, `direction_financiere`, `erp`, `achats`, `tms`, `financement`, `signal` |
| `valeur` | liste fermée ou texte borné | Liste fermée pour `erp`, `achats`, `tms`, `financement` (section 6.2) |
| `statut_valeur` | liste | `present` ou `absence_declaree` |
| `citation` | texte | Recopiée mot pour mot, 25 mots au plus. Le schéma ne sait pas borner une longueur : le code le fait [P] |
| `citation_langue` | code | `en`, `de`, `fr`, `sv`, `fi`, `it` |
| `traduction_fr` | texte, facultatif | Marquée comme traduction |
| `url` | adresse | Page qui porte la citation |
| `type_source` | liste | P1 à P5 (section 6.4) |
| `date_source` | date | Date de la page, relevée sur la page |
| `date_lecture` | date-heure | Au moment de la lecture |
| `empreinte_source` | texte | SHA-256 du texte relu |
| `modele`, `version_outil`, `empreinte_prompt` | texte | Pour rejouer |

Le code ajoute ensuite : `verifs` (citation trouvée, score de similarité, entité conforme, date dans la fenêtre, adresse répondant), puis `niveau`.

Le schéma strict d'un outil du fournisseur n'accepte ni longueur maximale de texte, ni bornes numériques [P]. Les limites de longueur et de date se vérifient donc dans le code.

### 6.2 Listes fermées [H]

Valeurs de départ, tirées de la connaissance du métier, à relire avant la construction.

| Champ | Valeurs |
|---|---|
| ERP | SAP S/4HANA, SAP ECC, Oracle Fusion, Oracle E-Business Suite, Oracle JD Edwards, Microsoft Dynamics 365, Microsoft Dynamics AX ou NAV, Infor, IFS, Workday, Sage, QAD, Epicor, autre |
| Plateforme d'achats | SAP Ariba, Coupa, Jaggaer, Ivalua, Basware, GEP, Zycus, Oracle Procurement, Microsoft Dynamics 365 Supply Chain, autre |
| TMS et trésorerie | Kyriba, SAP Treasury (TRM, Cash Management), GTreasury, FIS (Quantum, Integrity), ION (Reval, Wallstreet Suite), Coupa Treasury, Bellin, Salmon, Allgeier (Trema), autre |
| Financement court terme | Affacturage avec recours, affacturage sans recours, titrisation de créances (ABS, ABCP), affacturage inversé (supply chain finance), escompte dynamique. Billets de trésorerie (NEU CP, ECP, USCP), ligne de crédit renouvelable (RCF), crédit documentaire ou forfaiting, autre |

### 6.3 La fiche

Une fiche regroupe les trouvailles d'une société, le périmètre retenu, les contradictions, les questions et le journal. Le brief et les tableurs ne lisent qu'elle.

### 6.4 Les règles de confiance

Le code applique cette table. Le modèle ne la modifie pas et ne note pas sa propre confiance.

| Type | Définition | Fenêtre [H] |
|---|---|---|
| P1 | Document de la société : rapport, présentation, communiqué, page officielle | 24 mois |
| P2 | Document d'un tiers qui nomme la société : éditeur, intégrateur, association | 36 mois |
| P3 | Presse ou agence de notation | 24 mois |
| P4 | Signal indirect : offre d'emploi, intervention en conférence | 12 mois |
| P5 | Base payante | Second avis seulement |

Une valeur que seules des sources P5 appuient n'entre pas dans le champ du brief. L'identité n'est pas concernée (D19).

- **Confirmé** : citation vérifiée dans une source P1 ou P2 de la fenêtre, entité conforme.
- **Probable** : citation vérifiée dans une source P3 ou P4. Ou une source P1 ou P2 hors fenêtre. Ou deux signaux P4 de sources distinctes. Ou deux sources qui se contredisent.
- **Non trouvé** : pas de citation vérifiée après le plan de requêtes complet, ou citation rejetée à la vérification. Ce n'est pas une absence prouvée.
- **Absence déclarée** : un document de la société dit qu'elle n'a pas le produit. Elle porte sa citation et suit les règles de preuve de « confirmé ».
- **Contradiction** : deux valeurs incompatibles pour un même champ. Les deux restent affichées, au niveau « probable », avec une question.
- **Source sans date lisible** : une page du domaine de la société (type P1) prend la date de lecture. Un autre type sans date est plafonné à « probable » [H].
- **Page vivante** : une page de la société sans année ni mot de document daté dans son adresse (contact, équipe, relations investisseurs) vaut à la date de lecture. La date de ses métadonnées ne compte pas. Un communiqué, un rapport ou un article garde sa date de première publication, pas celle de sa dernière modification [H]. Essai du 13 novembre : la page de contact de Verallia porte une date de 2020 dans ses métadonnées [N].
- **Type de source recalculé** : le code le déduit du domaine et du chemin (société, éditeur ou intégrateur, presse, offre d'emploi). Le modèle le propose, le code décide. Un domaine inconnu vaut P3, au plus « probable » [H].

**Fenêtres par champ.** Les fenêtres du tableau sont des valeurs de départ [H]. Sur les quatre trouvailles relues le 13 novembre, trois tombent hors fenêtre ou sans date. Il s'agit du guide Ariba de Nokia (27 mois), du communiqué Kyriba de Barilla (56 mois) et de l'étude de cas de Saint-Gobain (sans date). La sonde (T1.4) mesure cette part. Si elle dépasse la moitié des trouvailles utiles, les fenêtres passent par champ. Le nom du directeur financier garde 12 mois. L'ERP, le TMS et les achats passent à 60 mois, car ils changent rarement [H]. Le choix s'écrit au journal des décisions.

### 6.5 Les six contrôles du code

1. La citation figure dans le texte relu de la source. Espaces, casse, coupures de mots et ligatures des PDF sont normalisés. Seuil de similarité de 0,95 [H].
2. L'adresse répond, et son domaine correspond au type de source annoncé.
3. La source nomme la société visée ou un alias connu. Une filiale est signalée comme telle.
4. La date de la source tombe dans la fenêtre de son type. Sans date lisible, la règle de la section 6.4 s'applique.
5. Deux valeurs qui se contredisent restent affichées ensemble.
6. Chaque nombre du brief figure dans la fiche.

Le code relit lui-même chaque page citée. Le modèle ne se contrôle pas.

**Réparation de citation (D14).** Quand la page est lisible et que la citation du modèle n'y figure pas (similarité sous 0,95), le code cherche dans la page, titre compris, une phrase de 25 mots au plus qui contient la valeur affirmée et dont le texte se rapproche de la citation (RapidFuzz, `token_set_ratio` d'au moins 0,5). La valeur affirmée se lit ainsi : un alias de la liste fermée du produit, le nom de famille du dirigeant, au moins deux noms propres du signal. Le passage est recopié tel quel dans la page ; les contrôles 2 à 4 s'appliquent à lui. Le niveau est plafonné à « probable » et la fiche garde la citation d'origine (`citation_du_modele`), le score avant réparation et le mode `citation_remplacee`. Le journal des erreurs le relève avec sa correction.

**Rendu JavaScript (D16).** Une page lue directement qui fait moins de 4 000 caractères et ne porte pas la citation est relue rendue par Jina Reader. Le texte rendu ne remplace la lecture directe que s'il rapproche la citation de la page. Le balisage Markdown (images, liens, titres, tableaux, emphases) est retiré du texte avant toute comparaison, des deux côtés. Sur les douze sociétés, dix pages ont été relues rendues [N].

**Rôles des dirigeants (D17).** Pour la direction financière, le code lit le poste dans la valeur et, quand la valeur n'est que le nom, dans la citation. Cinq rôles : directeur financier, directeur désigné, responsable de la trésorerie, adjoint, autre poste. Une contradiction ne vaut qu'entre deux directeurs financiers au même niveau. Le brief montre deux personnes au plus, le directeur financier d'abord.

**Seconde lecture à l'aveugle (D15).** Quand la page est refusée au code (robots.txt, HTTP 401, 403 ou 429), un second sous-agent la rouvre avec ses propres moyens, sans connaître la citation, et recopie un passage qui soutient le sujet. Le code compare les deux textes dans les deux sens, à une similarité d'au moins 0,95 : la citation du premier agent dans le passage relu, ou le passage relu dans la citation (D18). Dans le second cas, le passage compte au moins 6 mots et nomme la valeur, selon les exigences de la réparation ; il remplace la citation, et celle du premier agent reste dans `citation_du_modele`. La trouvaille entre alors au plus à « probable », avec le mode `seconde_lecture`. Le premier test ne cherchait que dans un sens. Un second agent limité à 15 mots recopie un extrait plus court que la citation du premier, si bien que l'accord était manqué par construction (5 lignes sur 18). Avec les deux sens, 15 lignes sur 26 s'accordent sur les douze sociétés [N].

## 7. Le brief

Une page A4, lue en 90 secondes [H], 330 mots au plus [H]. Quatre blocs et un pied.

| Bloc | Contenu | Règle |
|---|---|---|
| En-tête | Société, statut, date de la fiche, nombre de sources | Une ligne |
| Ce qu'on sait | Cinq lignes : direction financière, ERP, plateforme d'achats, TMS, financements. Chacune avec sa valeur, son niveau et un renvoi de source | « Non trouvé » s'écrit tel quel. L'absence déclarée s'écrit comme un fait |
| L'angle pour CA\|ES | Trois phrases | Marqué « hypothèse ». Cite au moins un fait de la fiche. Ne dit rien du produit de CA\|ES au delà de sa description publique |
| Les questions | Trois à cinq | Une par champ non trouvé ou contredit, tirée d'une table de questions types |
| Contact | Une ligne, facultative | Section 10 |
| Pied | Sources numérotées, domaine et année | Les adresses complètes sont dans le tableur |

Règles de langue, contrôlées par le code : pas de tiret cadratin, pas de superlatif, pas de promesse de gain, pas de chiffre sans source, phrases de 30 mots au plus. Un brief qui échoue est réécrit une fois, puis signalé.

L'angle vient d'une table : pile trouvée et financements trouvés donnent une piste. Le modèle écrit la phrase, pas la piste.

| Cas | Piste |
|---|---|
| ERP et plateforme d'achats connus, financement fournisseur absent ou non trouvé | Financer les factures fournisseurs depuis l'outil déjà en place |
| Affacturage ou titrisation déclarés | Étendre ou comparer le programme existant, en l'intégrant à l'ERP |
| Affacturage inversé déclaré | Ouvrir la discussion sur les fournisseurs de rang 2 et sur l'intégration |
| Rien de trouvé sur la pile | Ouvrir la discussion par les questions |

## 8. Les tableurs

Deux fichiers, 10 Mo au plus chacun.

**Fichier 1, large : `cartographie.xlsx`.** Une ligne par société. Feuille « Cartographie » : société, pays, statut, ISIN, LEI, site de relations investisseurs. Puis, pour chacun des champs (direction financière, ERP, plateforme d'achats, TMS, financements, signal récent) trois colonnes : valeur, adresse de la source, niveau. Puis date de la fiche, coût, temps, version. Feuille « Légende » : définitions des niveaux. Feuille « Audit » : les 36 cellules tirées au sort, avec la citation, le lien et une colonne juste ou faux.

**Fichier 2, long : `trouvailles.xlsx`.** Une ligne par trouvaille : les champs de la section 6.1, plus les résultats des six contrôles et le niveau. C'est le fichier qu'on filtre pour auditer.

Chaque lien est cliquable. Aucune cellule n'est corrigée à la main : un contrôle d'empreinte compare le fichier livré à la sortie de l'outil.

## 9. Les journaux

**Journal de run** (`journal.jsonl`) : une ligne par étape et par société. Champs : `run_id`, `societe`, `etape`, début, fin, durée, modèle, jetons (entrée, sortie, cache lu, cache écrit), recherches, lectures, coût calculé, statut, erreur. Le coût se calcule avec la grille ; il n'est pas saisi à la main.

**Journal d'erreurs** (`erreurs.jsonl`), une ligne par erreur : société, champ, ce que l'outil a écrit, ce que dit la source, cause, contrôle qui l'a vue, changement apporté, relance faite. Causes admises : entité, extrapolation, citation reformulée, date, périmètre, source non primaire, traduction, autre. Une erreur sans changement associé n'est pas comptée comme corrigée.

## 10. Les contacts en suggestion non vérifiée [O]

Oscar a choisi d'en porter dans les briefs. Le module est borné pour que cette partie ne coûte pas au reste.

**Ce qui s'affiche.**

- Le nom et la fonction du directeur financier (ou du trésorier), tels qu'un document de la société de moins de 12 mois les publie.
- Les adresses générales publiées par la société : relations investisseurs, presse. Elles ne sont pas des données personnelles quand elles désignent la personne morale [P : page de la CNIL].
- Le standard téléphonique publié.
- Une suggestion d'adresse nominative, marquée « déduite, non vérifiée, à ne pas utiliser sans validation ».

**Quand une suggestion existe.** Quatre conditions réunies.

1. La personne est nommée comme directeur financier ou trésorier par un document de la société.
2. Au moins deux adresses nominatives du même domaine sont publiées par la société (communiqués, pages de contact) et suivent le même modèle.
3. Le domaine a un enregistrement MX (contrôle DNS, sans message envoyé).
4. Le modèle (prénom.nom, p.nom, prénom_nom) se normalise sans ambiguïté : accents, traits d'union, particules.

La suggestion cite les deux adresses qui fondent le modèle. Elle n'entre pas dans l'échelle confirmé, probable, non trouvé, car ce n'est pas un fait sourcé. Elle porte la mention « déduite ».

**Ce que le module ne fait pas.** Pas de sonde SMTP, pas d'envoi, pas de base tierce, pas de ligne directe. Il ne cible que le directeur financier.

**Garde-fous.**

- L'interrupteur `--sans-contacts` retire le bloc du brief et des tableurs sans toucher au reste.
- Les suggestions ne sortent pas dans l'export « CRM ».
- Elles sont effacées après la restitution. Le registre du traitement tient en dix lignes et se génère des données réelles.
- Pour les sociétés allemandes (Fresenius, Deutsche Telekom), le brief ajoute une mention. L'e-mail y demande un consentement préalable, même entre professionnels [P : UWG § 7, alinéa 2, numéro d'alinéa à reconfirmer]. Le téléphone professionnel y reste possible avec un consentement présumé.

**Constats de lecture du 13 novembre.** La page de la CNIL sur la prospection par courriel ne traite pas la collecte d'adresses sur internet [N : agent, à recontrôler]. La page de contact de Verallia publie une adresse générale et un seul contact nommé, celui des relations investisseurs [P]. La condition des deux adresses nominatives n'y est pas remplie : pas de suggestion pour Verallia. Les pages de relations investisseurs de Saint-Gobain et de Nokia ont refusé la lecture (403) [N : agent]. Leurs adresses se prennent ailleurs ou restent « non trouvé ».

**Risque à connaître.** Une adresse nominative déduite reste une donnée personnelle inférée. Des évaluateurs bancaires peuvent y voir un défaut de prudence. L'interrupteur existe pour cela : le PDF peut partir sans ce bloc.

## 11. Pile technique

### 11.1 Sources gratuites retenues

| Source | Sert à | Limites connues | Statut |
|---|---|---|---|
| Wikidata | Entité : ISIN, LEI, site | 5 requêtes parallèles par IP, 60 s de calcul par fenêtre de 60 s, User-Agent descriptif [P : agent] | Retenue : 9 sociétés sur 12 [N] |
| GLEIF | Contrôle d'un LEI connu | Recherche plein texte inutilisable pour un nom [N]. Limite de débit non relue | Retenue pour le contrôle |
| filings.xbrl.org | Rapports annuels ESEF | Pas d'Allemagne ni de Suisse. 429 après dix appels. Dépôt incomplet [P][N] | Retenue, partielle |
| API des entreprises françaises | Identité des sociétés françaises | Page déplacée vers data.gouv.fr, limite non relue [N : agent] | Retenue, à retester |
| SEC EDGAR | Déposants à la SEC | Page de règles en erreur 503 à la lecture. Déposants parmi les 12 : non testé | À tester |
| Sites de relations investisseurs | Rapports annuels, présentations, contacts publiés | Pages qui refusent la lecture (403 : Saint-Gobain, Nokia) [N : agent]. La page des fournisseurs de Nokia refuse aussi l'outil de lecture de cette session (403) [N] | Source principale, avec secours |
| Communiqués et études de cas des éditeurs | ERP, TMS, achats | Parfois anciens (56 mois pour Barilla) ou sans date (étude de cas de MuleSoft sur Saint-Gobain) [P] | Source principale |
| Guides et portails fournisseurs des sociétés | Plateforme d'achats | Lecture seule, sans inscription | Source principale |
| Offres d'emploi publiques | Signal ERP, TMS | Éphémères, conditions des sites à lire | Signal « probable » |
| Jina Reader | Secours de lecture, JavaScript et PDF | 20 requêtes par minute sans clé [P] | Secours |
| Écartées | LinkedIn, Apollo, crt.sh, DNS TXT, Banque de France, theHarvester | Section 14 | |

### 11.2 Ce que le Mac porte déjà [N]

Inventaire du 13 novembre, en lecture seule. Rien n'a été installé. Le code existant est décrit dans le plan de travail, qui n'est pas publié : trois pièces d'un projet antérieur se réemploient, le reste est de l'idée.

| Famille | Présent | Absent | Conséquence |
|---|---|---|---|
| Python principal | 3.12.7 (Anaconda) : `httpx`, `beautifulsoup4`, `lxml`, `pypdf` 6.17, `pdfminer.six`, `pydantic` 2.14, `openpyxl`, `xlsxwriter`, `pandas`, `jinja2`, `reportlab`. SDK Anthropic 1.17.0 | `trafilatura`, `pymupdf`, `pdfplumber`, `docling`, `markitdown`, `unstructured`, `weasyprint`, `tiktoken`, `arelle`, `py-xbrl`, `edgartools`, `instructor`, `litellm`, `langchain`, `llama-index`, `selectolax`, `ddgs` | Un environnement propre à l'outil, aux versions épinglées. Le SDK du Mac a deux versions majeures de retard sur la 2.8.0 |
| Autres environnements | Celui de Scrapling (73 paquets) : `rapidfuzz` 3.14, `playwright` 1.59, `scrapling` 0.4.8. Celui d'un projet antérieur : `httpx`, `lxml`, `pydantic`, `reportlab` | Le SDK Anthropic dans les deux | Les environnements du Mac ne réunissent pas le SDK et `rapidfuzz` |
| Ligne de commande | `node` 22, `npm`, `uv` 0.13, `gh` 2.102 (connecté), `vercel` 59, `pdftotext` (poppler), LibreOffice, Docker, Chrome 156, `jq` | `tesseract`, `pandoc`, `wkhtmltopdf` | Le PDF des briefs passe par Chrome. Pas d'OCR : un PDF image reste « non lisible » |
| Recherche | Exa par `mcporter` (recherche et lecture, sans clé, quota non mesuré). Jina Reader | Clés d'API Anthropic, Firecrawl, Exa, Pappers, Apollo | Secours de recherche, à mesurer avant d'y compter |
| Scrapling 0.4.8 | Licence BSD-3, lecture HTTP, rendu JavaScript par Chromium, serveur MCP | | Dernier recours : 423 Mo d'environnement, 525 Mo de navigateur. Son mode furtif contourne les blocages : écarté |

La variable `ANTHROPIC_BASE_URL` est définie sur l'adresse officielle de l'API, sans chemin : le SDK la lit, elle ne gêne pas. Le test d'appel (T0.5) relève l'adresse effective.

### 11.3 Outils libres et offres gratuites [N]

Lecture du 13 novembre : licence, étoiles et dernier commit relevés par l'API de GitHub, pages de tarifs ouvertes pour les offres. Huit dépôts ont été recontrôlés à la main, avec les mêmes chiffres.

- **Adopté** : entre dans la première version.
- **Option** : écrit au plan de repli, ou ajouté si le besoin se montre.
- **Écarté** : raison donnée.

| Étape | Projet | Licence | Verdict | Raison |
|---|---|---|---|---|
| 1 et 5 | RapidFuzz | MIT | Adopté | Similarité des citations et des noms. Dernier commit le 9 novembre |
| 1 | Splink | MIT | Écarté | Conçu pour des millions de lignes |
| 2 | Tavily (service) | Offre gratuite | Adopté, en option | 1 000 crédits par mois sans carte, 1 crédit par recherche simple [P]. Alimente le chemin B |
| 2 | Serper (service) | Offre gratuite | Secours | 2 500 requêtes gratuites sans carte [S : agent] |
| 2 | SearXNG | AGPL-3.0 | Option, service séparé | Auto-hébergé, moteurs en amont, débit non garanti. Non importé |
| 2 | `ddgs`, Google Programmable Search, Brave | MIT, offres | Écartés | `ddgs` : usage éducatif, moteurs agrégés. Google : fermé aux nouveaux clients, fin au 1er janvier 2027. Brave : plus de plan gratuit [S : agent] |
| 2 à 4 | GPT Researcher, STORM, deep-research, open_deep_research | Apache-2.0, MIT | Écartés | Sortie libre, hors du schéma fermé. Trois sur quatre sont archivés ou sans commit depuis plus de six mois |
| 3, HTML | `trafilatura` | Apache-2.0 | Adopté | Texte principal d'une page. Dernier commit le 13 novembre |
| 3, PDF | `pypdf` | BSD-3 | Adopté | Texte par page. `pdftotext` (poppler) sert d'accélérateur s'il est présent |
| 3, PDF | PyMuPDF, `pymupdf4llm` | AGPL-3.0 | Écartés | Licence incompatible avec un dépôt MIT |
| 3, PDF | Docling, `pdfplumber`, MarkItDown | MIT | Options | Tableaux des rapports. Poids et vitesse non mesurés |
| 3, PDF | Unstructured | Apache-2.0 | Écarté | Exige poppler, tesseract et LibreOffice |
| 3, JavaScript | Scrapling | BSD-3 | Option de dernier recours | Modes furtifs exclus : un 403 est une politique du site (R4) |
| 3, JavaScript | crawl4ai, Crawlee, ScrapeGraphAI, browser-use | Apache-2.0, MIT | Écartés | Crawl entier, extraction par un modèle non déterministe, agent de navigation. Chrome suffit pour le PDF |
| 3, service | Jina Reader | Apache-2.0 | Secours | Service tiers, 20 requêtes par minute sans clé [P] |
| 3, service | Firecrawl | AGPL-3.0 | Écarté | Licence, et règle d'Oscar : pas sans son accord |
| 3, registres | Arelle, `edgartools` | Apache-2.0, MIT | Options | ESEF lourd. SEC : identité en en-tête, 10 requêtes par seconde au plus [S : agent] |
| 3, registres | `py-xbrl` | GPL-3.0 | Écarté | Licence |
| 2 et 3, technologies | Wappalyzer et dérivés, WhatWeb, `wappalyzergo` | GPL-3.0, GPL-2.0, MIT avec empreintes GPL-3.0 | Écartés | Détectent la pile du site web, pas l'ERP, le TMS ni les achats |
| 2 et 3, offres d'emploi | JobSpy | MIT | Écarté | Passe par LinkedIn (exclu) et Indeed, dont les conditions interdisent les robots sans accord écrit [S : agent] |
| 4 | SDK Anthropic, `pydantic` | MIT | Adoptés | Coût relevé au même endroit, outils du fournisseur, schéma strict |
| 4 | `instructor`, `pydantic-ai` | MIT | Écartés de la première version | Couche d'abstraction sans objet tant qu'un seul modèle sert |
| 4 | `litellm` | MIT et dossier commercial [S : agent] | Écarté | Versions 1.82.7 et 1.82.8 piégées le 24 mars 2026 [S : plusieurs comptes rendus de sécurité] |
| 4 et 5 | LangExtract | Apache-2.0 | Idée | Ancre chaque extraction sur les caractères de la source, comme le contrôle 1 |
| 4 | Ollama, `llama.cpp` | MIT | Plan de repli | Filet sans quota. Qualité en suédois et en finnois non vérifiée |
| 5 | `pytest` | MIT | Adopté | Jeu des 12 relus à la main |
| 5 | promptfoo, `inspect_ai` | MIT | Écartés | Node, et propriété d'OpenAI pour l'un [S : agent] ; surdimensionné pour l'autre |
| 6 | `openpyxl`, Chrome sans affichage | MIT, installé | Adoptés | Tableurs et PDF. WeasyPrint (BSD-3, exige Pango 1.44) reste une option |

**Offres gratuites de modèles.** Le modèle du cas reste payé (D3, D11 du plan). Ces offres nourrissent le plan F et le texte « à 200 sociétés ».

| Offre | Limites gratuites | Données | Sortie structurée | Verdict |
|---|---|---|---|---|
| Cloudflare Workers AI | 10 000 neurones par jour, erreur au-delà [P] | Pas de conservation ni d'entraînement dans les sources de la documentation [S : agent] | `json_schema`. Gemma 4, gpt-oss-120b | Plan F |
| Gemini API (AI Studio) | Modèles Flash gratuits. Chiffres par modèle à relire dans AI Studio [S : agent] | Contenu réutilisé par Google et relu par des humains : texte public seulement [S : agent] | JSON Schema | Option, texte public |
| Groq | gpt-oss-120b : 8 000 jetons par minute [S : agent] | Pas de conservation par défaut | Strict sur gpt-oss | Écarté : un rapport dépasse la limite |
| OpenRouter | 50 requêtes par jour sans crédit acheté [S : agent] | Réglage séparé pour les fournisseurs gratuits | Selon le modèle | Écarté |
| Mistral | Pas de chiffre : la documentation et l'aide se contredisent [S : agent] | Non lu | `json_schema` | Écarté, à vérifier en console |
| Hugging Face | Pas de crédit gratuit [S : agent] | Non lu | Non lu | Écarté |

**Ce que cette lecture change.** Le chemin B cherche avec Tavily (ou le fournisseur) et lit avec `httpx`, `trafilatura` et `pypdf`. La qualité en suédois et en finnois n'a pas été vérifiée sur les modèles gratuits : le plan F la mesure sur 3 sociétés avant tout usage. Côté chaîne d'approvisionnement, le dépôt porte un fichier de verrouillage avec empreintes (`uv.lock`) et une analyse `pip-audit` avant publication.

## 12. Critères d'acceptation et tests

| Famille | Contenu | Seuil |
|---|---|---|
| Unitaires, hors ligne | Schéma, table de confiance (20 cas), normalisation des citations, détection de modèle d'adresse, coûts. Sources figées en fixtures | Tous verts |
| Intégration, réseau | Un test par source (Wikidata, GLEIF, ESEF, une page, un PDF), marqué et débrayable | Verts au moment de la construction |
| Qualité | 95 % des citations vérifiées ; 90 % de justesse sur 36 cellules ; zéro nombre sans source dans les briefs | Seuils de la section 5 |
| Non-régression | Les 12 fiches relues forment le jeu de cas, rejoué à chaque changement de consigne ou de modèle | Aucune cellule « confirmé » ne devient fausse |
| Stabilité | Deux sociétés traitées deux fois : les niveaux et les valeurs sont comparés | Écarts listés |
| Charge | Montée à 2, puis 4 sociétés en parallèle, jusqu'à la limite de débit lue sur la Console | Aucune erreur 429 non gérée |
| Coût | Plafond bas posé : arrêt propre, reprise | Test vert |
| Injection | Une page qui contient une consigne : elle est signalée et non suivie | Test vert |
| Dépôt public | Analyse des secrets, `grep` des noms interdits, licences des dépendances | Rien trouvé |
| Démo | Répétition sur 3 sociétés hors liste | Sans panne |

## 13. Risques

| # | Risque | Effet | Parade |
|---|---|---|---|
| R1 | Organisation en niveau d'évaluation, limites de débit plus basses que le tableau standard [P] | Run lent, démo en retard | Lire la page des limites avant de commencer. Parallélisme 2 au départ. Montée progressive |
| R2 | PDF trop lourds : 1 500 à 3 000 jetons par page, 600 pages au plus, 100 sous 1M de contexte [P] | Erreur ou coût élevé | Lecture locale du texte, fenêtres autour des mots-clés |
| R3 | Pages rendues par JavaScript, non lues par l'outil du fournisseur [P] | Champ « non trouvé » à tort | Jina Reader en secours : il rend le JavaScript [P] |
| R4 | robots.txt ou une réponse 403 refuse la lecture [P][N] | Source inaccessible | Respect du refus, sans contournement. Autre source : communiqué, PDF direct |
| R5 | Mauvaise entité : filiale, fondation, homonyme [N] | Fiche fausse | Wikidata puis contrôle du LEI. Périmètre écrit. Question si doute |
| R6 | Citation reformulée ou inventée | Fait faux marqué confirmé | Contrôle 1 par le code |
| R7 | ERP déduit du secteur | Fait faux | Citation obligatoire. Signal d'offre d'emploi plafonné à « probable » |
| R8 | Dépassement des trois heures | Livrable incomplet | Lignes de coupe écrites (planification) |
| R9 | Dérive du coût | Dépassement du plafond | Budget par société, plafond de l'espace de travail. Comptage des jetons avant envoi pour le chemin B seulement [P] |
| R10 | Panne pendant la démo | Perte de crédibilité | Cache, société déjà traitée, répétition, montée progressive |
| R11 | Contacts jugés intrusifs | Image | Marquage, minimisation, interrupteur |
| R12 | Dépôt public : secret, nom de client, licence incompatible | Fuite ou conflit | Analyse des secrets, `grep`, liste des licences |
| R13 | Quotas des services gratuits de recherche et de lecture | Source de secours coupée | Cache, deux secours distincts |
| R14 | API publique en panne ou limitée (429 de l'index ESEF) [N] | Étape bloquée | Reprises espacées, cache, table d'alias locale pour les 12 |
| R15 | Sorties différentes d'un run à l'autre | Résultats non rejouables | Versions figées, test de stabilité, sources brutes gardées |
| R16 | SDK ancien : l'installation principale du Mac porte la version 1.17.0 [N] | Outils `_20260318` absents des types, appel refusé | Environnement propre, version épinglée, test d'appel à T0.5 qui relève l'adresse effective de l'API |
| R17 | Chaîne d'approvisionnement : un paquet libre publié piégé, comme `litellm` le 24 mars 2026 [S] | Vol de clés ou de jetons de connexion | Peu de dépendances, versions épinglées avec empreintes (`uv.lock`), `pip-audit` avant publication, clés hors du dépôt, plafond de dépense quand il existe |
| R18 | Le poids de Claude Code gonfle les jetons de chaque appel (consignes, outils, mémoire) [N] | Jetons par société plus élevés que ceux d'une API directe | Appel à vide mesuré et déclaré. Outils limités à la recherche et à la lecture web. Dossier de travail neutre, sans fichier de consignes |
| R19 | Des sites refusent la relecture par le code (robots.txt, 403), sur plus d'une adresse sur quatre [N] | Citations vraies rejetées, niveaux « confirmé » rares sur les éditeurs | Respect du refus. Seconde lecture par le modèle (Claude-User est souvent autorisé), plafonnée à « probable », à décider après la sonde ; décidée par D15 et D18 |
## 14. Hypothèses vérifiées avant la pile

Statut au 13 novembre 2026. Les trois lectures en cours peuvent ajouter des lignes.

| # | Hypothèse | Statut | Preuve | Effet sur la pile |
|---|---|---|---|---|
| H1 | L'outil de lecture du fournisseur lit les rapports annuels en PDF | **Partiel** | PDF supportés, mais 1 500 à 3 000 jetons par page, 600 pages au plus (100 sous 1M de contexte), `max_content_tokens` ne s'applique pas aux PDF [P] | Lecture locale des rapports annuels, fenêtres autour des mots-clés |
| H2 | Il lit les sites des sociétés | **Partiel** | Pas de pages rendues par JavaScript. Refus par robots.txt. URL déjà vue dans la conversation [P] | Lecteur de secours qui rend la page |
| H3 | Les versions d'outils sont `_20260209` | **Périmé** | `web_search_20260318` et `web_fetch_20260318` existent, avec filtrage dynamique et contrôle de l'inclusion des réponses [P] | Versions `_20260318` |
| H4 | Quatre sociétés en parallèle passent | **À réviser** | Niveau d'évaluation plus bas pour une organisation neuve. Limite de montée : 429 après une hausse brusque [P] | Parallélisme 2 puis montée. Lecture de la page des limites |
| H5 | Un plafond de dépense par espace de travail existe | **Vrai** | Réglable sauf sur l'espace par défaut. À la limite : erreur 400, message « specified workspace API usage limits » [P] | Espace de travail dédié |
| H6 | Sortie par un outil au schéma strict | **Vrai, avec réserve** | Outils stricts et sorties JSON fonctionnent ensemble. Pas de `maxLength` ni de bornes numériques [P] | Longueurs vérifiées par le code |
| H7 | Le choix forcé d'outil est possible | **Faux** | Erreur 400 sur Opus 5.5 et Sonnet 5.5 [P] | Consigne explicite plus outil strict |
| H8 | Le coût d'un rapport lu en entier vaut 0,50 $ | **Faux** | 300 pages font 450 000 à 900 000 jetons, soit 0,90 à 1,80 $ en entrée sur Sonnet 5.5 [P] | Lecture locale pour les rapports |
| H9 | La limite d'un PDF est de 32 Mo | **Périmé** | 128 Mo sur l'API directe [P] | Sans effet pour le cas |
| H10 | Vercel Hobby suffit | **Vrai pour un site statique** | Fonctions limitées à 300 s. Protection par mot de passe réservée à Pro. Authentification Vercel disponible sur Hobby [P] | Site statique. Protection coupée pour un lien ouvert |
| H11 | L'index ESEF couvre les sociétés cotées de l'Union | **Faux pour l'Allemagne** | 0 dépôt allemand, 0 suisse. Le dépôt est incomplet [P][N] | Rapports allemands et suisses lus sur le site de la société |
| H12 | Wikidata résout l'entité | **Partiel** | 9 sociétés sur 12 avec ISIN, LEI et site [N] | Wikidata d'abord, recherche web pour les 3 autres |
| H13 | GLEIF sert à chercher un nom | **Faux** | Recherche plein texte sans la tête de groupe en premier pour 0 société sur 12 [N] | GLEIF contrôle un LEI connu |
| H14 | L'index ESEF accepte des appels rapprochés | **Faux** | HTTP 429 après dix appels enchaînés [N] | Reprises espacées, cache |
| H15 | `claude -p` donne le coût d'un run | **Vrai** | `--output-format json` rend `total_cost_usd` et le détail par modèle, estimation côté client [P] | Non retenu : le modèle est facturé par la Console |
| H16 | LinkedIn interdit les robots | **Vrai** | Page d'aide de LinkedIn, section 8.2 [P] | LinkedIn exclu |
| H17 | Les citations de la recherche web aident la vérification | **Vrai** | Actives à chaque recherche, 150 caractères de texte cité au plus par citation [P] | Preuve supplémentaire pour le contrôle 1 |
| H18 | Le Batch convient à la mise à jour de 200 fiches | **Vrai** | Remise de 50 %. Les outils web y sont facturés comme en direct. Les recherches y sont ralenties par organisation [P] | Chemin de mise à jour des fiches |
| H19 | Le comptage de jetons gratuit couvre les appels avec outils serveur | **Faux** | Erreur 400 avec les outils serveur (recherche web, lecture web, exécution de code). Gratuit, avec des limites de requêtes par minute. PDF en base64 seulement [P] | Comptage avant envoi pour le chemin B. Chemin A : `max_uses` et lecture de `usage` |
| H21 | Un lecteur de secours gratuit existe | **Vrai** | Jina Reader : 20 requêtes par minute sans clé, 500 avec une clé gratuite (la page donne aussi 100), rend le JavaScript, lit les PDF, option robots.txt [P] | Secours de l'étape 3, à tester à la sonde |
| H20 | Les rapports d'usage et de coût de la Console servent à tout compte | **Faux pour un compte individuel** | L'API d'administration exige une organisation. Rapport de coût au pas d'une journée. Données en général sous 5 minutes [P] | Rapprochement par la page Cost de la Console, ou par l'API d'usage (pas d'une heure) avec une clé d'administration |
| H22 | Des sources gratuites donnent l'ERP, les achats et le TMS | **Vrai en partie, sur 3 sociétés essayées** | Relu le 13 novembre [P]. Nokia : page de SAP du 30 juin 2026 (ERP, confirmé) ; guide Ariba de juillet 2024, adresse relevée sans ouverture (achats, probable). Barilla : communiqué de Kyriba du 15 février 2022 (TMS et financement des fournisseurs, probable car hors fenêtre). Saint-Gobain : étude de cas de MuleSoft sans date (ERP, probable). Un seul « confirmé » sur quatre trouvailles | Sources du chemin A : éditeurs, guides fournisseurs, offres. La sonde mesure la part hors fenêtre |
| H23 | Les journaux de certificats et le DNS révèlent la pile | **Faux** | Enregistrements TXT relus le 13 novembre sur saint-gobain.com et barilla.com [N] : outils de marketing et de collaboration (Pardot, Atlassian, Zendesk, Dynamics 365 Marketing), ni ERP, ni outil d'achats, ni TMS. Une clé de Dynamics 365 Marketing pourrait faire conclure à tort à un ERP Dynamics (risque R7). Journaux de certificats : même constat de l'agent, non relu [N : agent] | Écartés |
| H24 | L'Allemagne exige un consentement pour l'e-mail, même entre professionnels | **Vrai** | UWG § 7, alinéa 2 [P : agent]. Téléphone professionnel : consentement présumé | Mention dans les briefs allemands |
| H25 | La Banque de France donne une liste publique d'émetteurs | **Faux** | Le portail redirige vers une connexion [N : agent] | Écartée de la pile |
| H26 | Wikidata se lit sans précaution | **Faux** | 5 requêtes parallèles par IP, 60 s de calcul par fenêtre de 60 s, 30 erreurs par minute, puis 429 et bannissement. User-Agent descriptif exigé [P : agent] | Débit bas, en-tête avec contact |
| H27 | theHarvester sert à trouver des adresses | **Non retenu** | Licence GPL-2.0, sources à clé et bases de fuites, usage réservé aux cibles autorisées [P : agent] | Écarté |
| H28 | Le plan gratuit d'Apollo donne API, export et crédits | **Non établi** | Rien d'officiel pour le plan gratuit. Mobile : 8 crédits [N : agent, docs.apollo.io] | Écarté |
| H29 | Un modèle gratuit peut remplacer le modèle payé | **Non établi** | Cloudflare : 10 000 neurones par jour, erreur au-delà [P]. Qualité en suédois et en finnois non vérifiée. Gemini gratuit : contenu réutilisé par Google [S : agent] | Plan F, non construit (D11 du plan) |
| H30 | Un outil de lecture libre contourne les refus des sites | **À écarter** | Un 403 est une politique du site. Les modes furtifs de Scrapling servent à passer des protections (R4) | Écarté. Autre source, ou « non trouvé » |
| H31 | La recherche gratuite suffit au run | **Vrai pour 12 + 8 sociétés, faux à 200** | Tavily : 1 000 crédits par mois [P]. Environ 550 crédits pour la sonde, le run, la démo et les reprises [H]. 3 000 pour 200 sociétés à 15 recherches [H] | Option au cas. À 200 : environ 16 $ de crédits en plus [H] |
| H32 | Les bibliothèques libres populaires sont sûres | **Faux** | `litellm` : versions 1.82.7 et 1.82.8 piégées le 24 mars 2026, retirées de PyPI [S : plusieurs comptes rendus de sécurité] | Peu de dépendances, fichier de verrouillage avec empreintes, `pip-audit` avant publication |
| H33 | `claude -p` marche sans clé de la Console | **Vrai si Claude Code est connecté, faux sinon** | `claude auth status` répond `loggedIn: false` sur ce Mac, y compris en environnement propre. Le mode `--bare` n'accepte que `ANTHROPIC_API_KEY`. Options relevées : `--output-format json`, `--json-schema`, `--tools`, `--allowedTools`, `--no-session-persistence`, `--max-budget-usd`. Pas d'option `--max-turns` [N] | `claude auth login` par Oscar. Délai d'appel et consignes de l'agent pour borner la boucle |
| H34 | Les jetons d'une session de développement se comptent après coup | **Vrai** | Les transcriptions (`~/.claude/projects/.../*.jsonl`, sous-agents compris) portent `usage.iterations` par message. Un message occupe plusieurs lignes : on garde une ligne par identifiant. Les totaux de tête valent zéro tant que la réponse n'est pas finie [N] | Importeur `jetons_dev.py`, testé sur des transcriptions simulées |
| H35 | Le code peut relire toutes les pages que l'agent a lues | **Faux** | Sur 16 adresses essayées le 13 novembre, 9 sont lisibles, dont 3 coquilles JavaScript de moins de 1 500 caractères. Deux refusent par robots.txt : news.sap.com et sap.com interdisent tout aux clients inconnus, mais autorisent des agents nommés dont Claude-User. Quatre répondent 403 (coupa.com, saint-gobain.com, barillagroup.com, businesswire.com). Une adresse était fausse [N] | Respect du refus (R4). Seconde lecture par le modèle, plafonnée à « probable », à décider après la sonde ; décidée par D15 et D18 |
| H36 | Wikidata accepte un client qui se décrit sans contact | **Faux** | Erreur 403 « robot policy » de Wikimedia pour un client `httpx` sans contact ; réponse 200 avec une adresse de contact dans l'identité [N] | Contact à fournir par Oscar (`PREPA_RDV_CONTACT`). Repli : table locale des 12 sociétés |
| H37 | La date des métadonnées d'une page vaut sa date de publication | **Faux pour les pages vivantes** | Contact de Verallia : 2020 dans les métadonnées, page tenue à jour [N] | Règle de la page vivante (section 6.4) |
## 15. Traçabilité

| Livrable du cas | Exigences |
|---|---|
| PDF de 12 briefs | F9, F11, section 7 |
| Tableur et lien de l'outil | F2, F10, F14, section 8, dépôt public |
| Texte sur l'outil | F12, F13, F15, section 9, prompt principal |
| Texte sur 200 sociétés | Plan section 10, F18, F23, mesures de F12 |
| Démo en direct | F19, section 12 |

## 16. Glossaire

- **Chemin A** : l'agent du fournisseur cherche et lit les pages web.
- **Chemin B** : lecture locale des documents lourds, fenêtres de texte envoyées au modèle.
- **Fenêtre** : passage de texte autour d'un mot-clé.
- **Niveau** : confirmé, probable, non trouvé, ou absence déclarée.
- **Sonde** : essai de 30 minutes sur deux sociétés qui décide de la configuration.
- **Trouvaille** : une information sur une société, avec sa preuve.
