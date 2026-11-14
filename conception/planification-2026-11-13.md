# Planification : le cas pratique en trois heures

Version 2 du 13 novembre 2026. Ce document donne l'ordre des tâches, les durées, les portes de décision, les lignes de coupe et le déroulé de la démo. Les exigences sont dans cahier-des-charges-2026-11-13.md. Les décisions sont dans plan-2026-11-13.md.

Marques du projet. **[P]** page officielle ouverte le 13 novembre 2026. **[L]** lu dans les fichiers d'Oscar ou dans le dépôt. **[N]** constaté ce jour. **[H]** hypothèse à mesurer : un chiffre [H] n'est pas une mesure. **[O]** décision d'Oscar.

## 1. Trois budgets de temps

| Budget | Valeur | Remarque |
|---|---|---|
| Horloge de la construction | 180 minutes à partir de la porte G0 [H] | Le calendrier nominal fait 208 minutes. Les coupes de la section 5 ramènent à 180 ou moins |
| Attention d'Oscar | 90 minutes au plus [H] | Détaillée en section 3, colonne « Qui » |
| Hors décompte, déclaré | Planification, lectures de documentation et sondes de faisabilité du 13 novembre | Le texte « ton outil » le dit en une phrase, avec la durée réelle |

La décision de déclarer la planification à part est celle d'Oscar. Le plafond du cas est de trois heures : le texte écrit le temps passé en deux lignes, construction et vérification d'un côté, préparation de l'autre.

## 2. Les portes

Une porte est un point d'arrêt où l'on décide avant de continuer.

| Porte | Condition pour passer | Qui décide | Si la condition échoue |
|---|---|---|---|
| G0 Prêt | Plan C [O] : `claude auth status` répond connecté, et un appel d'essai `claude -p` réussit avec ses jetons relevés. Poids à vide noté | Oscar | On ne lance aucune société. En attente de `claude auth login` |
| G1 Sonde | Coût par société lu. Au moins 95 % des citations vérifiées sur 2 sociétés [H]. Coût sous 3 $ par société [H] | Claude, Oscar informé | Chemin B ajouté (rapports lus en local), ou lecture ciblée seule |
| G2 Chaîne | 2 sociétés de bout en bout : six contrôles verts, brief d'une page, 2 tableurs | Claude | Pas de run des 12 avant G2 |
| G3 Run | 12 fiches écrites. Coût total sous le plafond. Aucune société sans journal | Claude | Relance des sociétés manquantes, sinon coupe |
| G4 Audit | Justesse de 90 % au moins sur l'échantillon. Au moins 2 erreurs documentées avec correction et relance | Oscar | Corrections par règle, nouvel échantillon de 12 cellules |
| G5 Livrables | PDF de 12 pages, 2 tableurs, 2 textes, dépôt propre (secrets, noms, licences) | Oscar | Pas de dépôt tant que l'analyse n'est pas verte |
| G6 Démo | Répétition sur 3 sociétés hors liste, sans panne | Oscar | Démo en mode société déjà traitée |

## 3. Le découpage

Durées en minutes [H]. « O » est Oscar, « C » est Claude. Les tâches de deux colonnes différentes qui se chevauchent tournent en parallèle.

### Bloc 0 : préparation (0 à 15)

| ID | Tâche | Qui | Durée | Dépend de | Sortie et critère |
|---|---|---|---|---|---|
| T0.1 | Plan C [O] : lancer `claude auth login` et se connecter, une fois | O | 2 | | `claude auth status` répond connecté |
| T0.2 | Facultatif : contact pour Wikimedia (adresse e-mail dédiée ou adresse du dépôt public) dans `PREPA_RDV_CONTACT` | O | 1 | | Wikidata répond 200 à `prepa-rdv resoudre Nokia` |
| T0.3 | Squelette du dépôt `outil/` : structure, licence MIT, `.gitignore`, `.env.example`, README court, `societes.csv`, environnement `uv` aux versions épinglées | C | 5 | | `pytest` se lance, 0 test. `uv sync` passe sur un dossier neuf |
| T0.4 | `schema.py`, `confiance.py`, listes fermées, contrôle de langue | C | 12 | T0.3 | 20 cas de la table de confiance verts |
| T0.5 | Appel d'essai à l'API, lecture des en-têtes de limites, comptage de jetons | C | 3 | T0.1 | Réponse reçue. Limites réelles notées. Adresse effective de l'API relevée. Porte G0 |
| T0.6 | Facultatif, hors décompte : compte Tavily gratuit et clé posée dans le terminal | O | 3 | | Variable `TAVILY_API_KEY` présente, longueur lue sans l'afficher. Sans elle, l'outil cherche avec le fournisseur |

### Bloc 1 : composants et sonde (15 à 65)

| ID | Tâche | Qui | Durée | Dépend de | Sortie et critère |
|---|---|---|---|---|---|
| T1.1 | Résolveur d'entité : Wikidata par étiquette exacte, contrôle GLEIF par LEI, recherche web pour les cas manquants (voestalpine, Fresenius, Verallia) | C | 8 | T0.4 | 12 sociétés résolues ou marquées « à confirmer ». Tests sur fixtures |
| T1.2 | Lecteur de documents : lecture polie (identité, robots.txt, cache), PDF par `pypdf` et HTML par `trafilatura`, fenêtres multilingues, recherche Tavily facultative (une fonction) | C | 12 | T0.4 | Fenêtres rendues sur un PDF d'essai. Tests sur fixtures |
| T1.3 | Agent web (chemin A) : recherche et lecture du fournisseur, plafonds d'usage, reprise après pause, outil de sortie strict | C | 12 | T0.5 | Une société donne des trouvailles valides. Usage relevé |
| T1.4 | Sonde sur Saint-Gobain et Barilla : chemin A, lecture locale du rapport, Sonnet 5.5 puis Opus 5.5 à effort bas sur Saint-Gobain | C | 18 | T1.1, T1.2, T1.3 | Tableau coût, temps, qualité, part des trouvailles hors fenêtre |
| T1.5 | Lire les deux fiches brutes et noter 10 cellules juste ou faux | O | 10 | T1.4 | Premier chiffre de justesse. Porte G1 |

### Bloc 2 : la chaîne complète (65 à 95)

| ID | Tâche | Qui | Durée | Dépend de | Sortie et critère |
|---|---|---|---|---|---|
| T2.1 | Vérificateur : six contrôles, niveaux, contradictions, absence déclarée | C | 10 | G1 | Tests hors ligne verts. Une citation inventée est rejetée |
| T2.2 | Brief : gabarit, table d'angle et de questions, contrôle de langue, contrôle des nombres, PDF par Chrome sans affichage | C | 10 | T2.1 | Un PDF d'une page lisible, rien de coupé |
| T2.3 | Tableurs en deux fichiers, feuille d'audit tirée au sort, journal de run agrégé | C | 6 | T2.1 | Fichiers qui s'ouvrent. Graine fixe |
| T2.4 | Module contacts : modèle d'adresse, contrôle MX, interrupteur | C | 4 | T2.1 | Bloc marqué « déduite, non vérifiée ». Interrupteur testé. Porte G2 |

### Bloc 3 : le run des 12 (95 à 125)

| ID | Tâche | Qui | Durée | Dépend de | Sortie et critère |
|---|---|---|---|---|---|
| T3.1 | Run des 12 : 2 sociétés en parallèle, puis 4 si les limites le permettent. Témoin naïf en même temps. Surveillance du coût | C | 25 | G2 | 12 fiches. Journal de run |
| T3.2 | Contrôle global : fiches présentes, coût total, anomalies. Porte G3 | C | 5 | T3.1 | Rapport d'une page |

### Bloc 4 : audit et corrections (125 à 165)

| ID | Tâche | Qui | Durée | Dépend de | Sortie et critère |
|---|---|---|---|---|---|
| T4.1 | Audit de 36 cellules dans la feuille | O | 36 | G3 | Juste ou faux pour chaque cellule |
| T4.2 | Classement des erreurs, corrections par règle, consigne ou liste, relance des champs touchés | C | 30 | G3, en parallèle de T4.1 | Journal d'erreurs. Relances faites |
| T4.3 | Justesse recalculée. Test de non-régression sur le jeu de cas. Porte G4 | C | 8 | T4.1, T4.2 | Seuil de 90 % tenu, au moins 2 erreurs documentées |

### Bloc 5 : livrables (165 à 208)

| ID | Tâche | Qui | Durée | Dépend de | Sortie et critère |
|---|---|---|---|---|---|
| T5.1 | PDF des 12 briefs, tableurs finaux, contrôle d'empreinte | C | 8 | G4 | 3 fichiers. PDF de 10 Mo au plus |
| T5.2 | Textes « ton outil » et « 200 sociétés » depuis les journaux, relus pour les cinq tics | C | 12 | T5.1 | 2 textes. Temps et coût par société dans un tableau |
| T5.3 | Lire les 12 briefs puis les 2 textes | O | 25 | T5.1, T5.2 | Corrections d'Oscar reportées dans les règles, pas dans les fichiers |
| T5.4 | Analyse des secrets, `grep` des noms interdits, licences, `pip-audit` sur le fichier de verrouillage | C | 5 | T5.1 | Rien trouvé |
| T5.5 | Publier : dépôt public MIT, dossier de partage, lien de l'outil. Porte G5 | O | 10 | T5.3, T5.4 | Liens ouverts sans compte, vérifiés depuis une fenêtre privée |

### Bloc 6 : après les livrables

| ID | Tâche | Qui | Durée | Dépend de | Sortie et critère |
|---|---|---|---|---|---|
| T6.1 | Synthèse du panel (une page) | C | 10 | G5 | Répartitions et champs les moins couverts |
| T6.2 | Vitrine statique sur Vercel | C | 25 | G5 | Lien ouvert sans compte, `noindex`, sans clé |
| T6.3 | Répétition de la démo sur 3 sociétés hors liste. Porte G6 | O et C | 20 | G5 | Sans panne, temps relevé |

## 4. Le chemin critique

Le chemin critique suit cet ordre : T0.1, T0.5, T1.3, T1.4, la porte G1, T2.1, T2.2, T3.1, T4.1, puis T5.1 à T5.5.

Trois points peuvent le rallonger sans faute du code. La clé qui tarde. Des limites de débit basses sur une organisation neuve [P]. La disponibilité d'Oscar pour l'audit de 36 minutes.

## 5. Les lignes de coupe

Le calendrier nominal fait 208 minutes. Pour tenir 180, on coupe dans cet ordre.

| Ordre | Coupe | Gain | Ce qu'on perd |
|---|---|---|---|
| 1 | Bloc 6 en entier, reporté après les livrables | 0 (déjà hors horloge) | La vitrine, la synthèse, la répétition |
| 2 | T1.5, la lecture de 10 cellules avant la porte G1 | 10 | Un premier chiffre de justesse. Il revient avec l'audit |
| 3 | Audit réduit de 36 à 24 cellules | 12 | Précision de l'estimation de justesse |
| 4 | Témoin naïf supprimé | 4 $, aucune minute | La comparaison avec une recherche sans vérification |
| 5 | Bloc contacts retiré du PDF, gardé dans le tableur | 4 | La ligne de suggestion dans les briefs |
| 6 | Chemin B non construit si la sonde passe | 0 | Rien, si G1 est vert |

Les coupes 2, 3 et 5 donnent 26 minutes : 208 devient 182. Lire les briefs à une minute chacune (T5.3 en 20 minutes) donne 177. Ne se coupent pas : les six contrôles du code, le journal d'erreurs, les deux erreurs documentées, le contrôle des nombres.

## 6. Liste de vérification avant G0

**Pour Oscar.**

- La Console : espace de travail, clé, limite mensuelle, page des limites lue.
- Facultatif : un compte Tavily gratuit et sa clé (T0.6).
- Un compte GitHub prêt pour un dépôt public. Un dossier de partage prêt, lien ouvert.
- Pour la vitrine seulement : un compte Vercel connecté, protection de déploiement coupée pour le projet.

**Pour Claude.**

- Python 3.12 et un environnement `uv` dans `outil/`, versions et empreintes figées dans `uv.lock`. Dépendances à licence permissive (pas d'AGPL ni de GPL), listées au README.
- Chrome présent pour le PDF. Un navigateur sans affichage se lance.
- La variable `ANTHROPIC_API_KEY` présente, sans l'afficher ni l'écrire dans un journal.
- Les sources de secours de lecture répondent (Jina par Agent Reach). Les sources à débit limité (ESEF, Wikidata) ont une identité joignable et un cache.

## 7. Le déroulé de la démo en direct

| Moment | Geste | Si ça tourne mal |
|---|---|---|
| La veille | Répétition G6 sur 3 sociétés hors liste. Cache chaud pour ces 3 | Refaire avec 2 sociétés en parallèle seulement |
| 30 minutes avant | Une société d'échauffement pour monter le débit sans à-coup [P] | Attendre une minute entre deux lancements |
| Début | Les noms donnés en séance entrent dans la file. Parallélisme 3, puis 4 si les limites le permettent | Le journal affiche le 429 et la reprise : on le commente |
| Pendant | L'écran montre les six étapes par société. Commentaire en cinq temps : un nom, les étapes, le brief et ses niveaux, un clic sur une source, le coût et le temps | Au delà de 6 minutes [H] pour une société, on montre une société déjà traitée |
| Fin | Le texte « où il s'est trompé » : deux erreurs réelles et leur correction | |

## 8. Les plans de repli

| Plan | Quand | Contenu |
|---|---|---|
| B | La sonde montre un coût de lecture élevé ou des erreurs de taille de PDF | Lecture locale des rapports (fenêtres) avec `pypdf`, recherche Tavily ou celle du fournisseur, l'agent ne lit que les pages web |
| C | **Retenu le 13 novembre au soir [O]** : pas de clé de la Console | Le modèle passe par `claude -p` sur l'abonnement. La sortie JSON donne les jetons par modèle et un coût déclaré. Le coût en dollars est estimé au tarif de liste. Écart déclaré dans le texte « ton outil » |
| D | L'index ESEF ou Wikidata est en panne | Table d'alias locale pour les 12, rapports lus sur les sites des sociétés |
| E | La démo est impossible en direct | Société déjà traitée, journal rejoué, tableur ouvert |
| F | Plafond de dépense atteint ou clé refusée, et Oscar accepte un modèle gratuit | Même schéma, mêmes contrôles, sur le texte déjà lu et cherché. Modèle de Cloudflare Workers AI (`json_schema`, 10 000 neurones par jour [P]). Qualité mesurée sur 3 sociétés avant tout usage, écart déclaré dans le texte |

Les plans C et F changent le sens de « coût par société » ou de « qualité ». Ils ne servent que si Oscar les accepte, et le texte le dit.

## 9. Définition de fini

| Livrable | Fini quand |
|---|---|
| PDF des 12 briefs | 12 pages, 10 Mo au plus, relues une à une par Oscar, aucune cellule corrigée à la main |
| Tableur | Deux fichiers, liens cliquables, empreinte identique à la sortie de l'outil, feuille d'audit remplie |
| Lien de l'outil | Dépôt public MIT, README qui lance une société en une commande sur une machine propre, analyse des secrets verte |
| Texte « ton outil » | Étapes, sources, tableau de temps et coût par société, prompt principal, au moins 2 erreurs avec leur cause, leur détection et leur correction |
| Texte « 200 sociétés » | Tableau « ce qui casse, ce que je change », où brancher, précautions, rôle de la relecture humaine |
| Démo | Porte G6 passée |

## 10. Le journal de décisions

À chaque porte, une ligne dans `decisions.md` du dépôt : date, porte, décision, raison, chiffre qui l'appuie. Ce journal sert au texte « ton outil » : il montre la démarche, pas seulement le résultat.

## Où on en est (14 novembre 2026, 17 h 40)

Construction, run des douze sociétés et dépôt public faits en 130 minutes de travail actif, sur 180 permises, dont 22 pour la relance de la seconde lecture de Barilla et ses suites et 19 pour le dépôt public. L'audit par agents, demandé ensuite par Oscar, porte le total à 163 minutes : 33 pour l'audit, après une coupure réseau de 24 minutes déclarée en pause. L'écriture du choix d'Oscar sur le périmètre des filiales (D22) ajoute 6 minutes, soit 168 au total. Le gabarit commun des PDF (D23) en ajoute 6, soit 174. Les deux tableurs, alignés ensuite sur ce gabarit, en ajoutent 5, soit 179. La planification (plan, cahier des charges, ce document) est comptée à part.

| Porte | État | Mesure |
|---|---|---|
| G1 Sonde | Passée | 2 sociétés lues. Coût de 2,6 $ par société au tarif de liste, sous 3 $. Citations retrouvées mot pour mot sur les pages que le code sait lire (constats d'identité exclus) : 95,0 % (134 sur 141), 97 % avec les 3 réparations |
| G2 Chaîne | Passée | Six contrôles, brief d'une page, deux tableurs, sur deux sociétés puis sur douze |
| G3 Run | Passée | 12 fiches écrites, 185 trouvailles, 163 gardées, dont 43 hors fenêtre et 4 sans date (29 %, sous la moitié : fenêtres de départ conservées). 26 lignes relues par un second agent, 15 accords. Chaque société a son journal |
| G4 Audit | Passée, mesurée sur le second tirage (choix d'Oscar, D22) | Trois auditeurs Opus 5.5, d'un autre modèle que les agents de recherche, ont jugé les 36 cellules du premier tirage (graine 2026) : 24 justes sur 33 vérifiables (73 %), sous le seuil. Repli prévu appliqué : deux règles d'affichage (D21), les 9 cellules en écart rejugées telles qu'elles s'affichent (2 justes, 7 partielles : la règle du projet corrige les 2 fausses, celle de l'entité ne change aucun des 6 verdicts « filiale ou division »), soit 26 sur 33 (79 %) pour le premier tirage corrigé, et un second tirage de 12 cellules neuves (graine 2027) : 9 justes sur 9 vérifiables (100 %), 3 invérifiables. Neuf cellules vérifiables font un petit échantillon. Oscar retient le 14 novembre qu'une cellule tirée d'une page sur une filiale reste dans la fiche, la filiale signalée, et que la porte se mesure sur le second tirage, que les règles n'ont pas vu (D22). Erreurs documentées avec correction et relance : 5 (2 de la sonde, 3 réparées par le code), plus les écarts d'affichage relevés par l'audit. Une erreur du contrôle lui-même, dans le test d'accord des secondes lectures, corrigée et testée (D18) |
| G5 Livrables | Passée | `briefs.pdf` (12 pages, 0,3 Mo), `cartographie.xlsx`, `trouvailles.xlsx`, `ton-outil.pdf` (6 pages), `a-200-societes.pdf` (2 pages). Dépôt public sous licence MIT, https://github.com/FiExplorer11020/prepa-rdv, construit, analysé et publié par `prepa-rdv depot` : aucun constat (noms, secrets, chemins, adresse retirée, licences), `pip-audit` sans vulnérabilité sur 58 paquets. Vérifié sans compte : clone neuf, tests verts, analyse refaite sur le clone. Lien de l'outil dans `cartographie.xlsx` et dans « Ton outil » |
| G6 Démo | À répéter | Mode `claude-cli` après `claude auth login`, ou sous-agents dans une session Claude Code. Pas encore répétée |

Ce qui a été appris à la mesure, et qui change l'outil par rapport au plan : le lecteur du code perd des phrases sur les pages construites par JavaScript (D16) ; le premier test d'accord des secondes lectures ne cherchait que dans un sens et manquait l'accord par construction, un second agent limité à 15 mots recopiant un extrait plus court que la citation du premier (D18) ; une base de données commerciale ne fait pas seule un champ, règle écrite mais appliquée seulement depuis la relance de Barilla (D19) ; un modèle recopie parfois de mémoire, d'où la réparation de citation (D14) ; les rôles des dirigeants se lisent dans la citation quand la valeur n'est que le nom (D17).

Hors horloge, la vitrine prévue en T6.2 est en ligne depuis le 14 novembre à 19 h 18, sur https://outil-fiexplorer11020s-projects.vercel.app/ (D24). Elle s'ouvre sans compte, porte `noindex` et ne contient aucune clé.

Ce qui reste, et qui ne tient plus qu'à Oscar : ouvrir les six liens que les auditeurs n'ont pas pu lire (feuilles « Audit » et « Audit, second tirage » de `cartographie.xlsx`), et répéter la démo. Oscar a vu les cellules partielles le 14 novembre à 18 h 16 et laisse celle de Servier sur Edgewise telle quelle, signalée par l'audit. Elle se précise à l'oral si Servier passe en démo. D'après la page citée, telle que les deux auditeurs l'ont lue, l'opération porte sur l'activité dystrophie musculaire d'Edgewise, pour 1,55 Md$ versés d'emblée. Aucune clé de la Console n'a été nécessaire.
