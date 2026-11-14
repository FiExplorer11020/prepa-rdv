# Méthodologie

Ce document décrit comment l'outil travaille, pourquoi il est construit ainsi et ce que ses journaux mesurent.
Chaque chiffre vient d'un fichier du dépôt, cité à côté. Les exigences complètes sont dans
[`conception/cahier-des-charges-2026-11-13.md`](conception/cahier-des-charges-2026-11-13.md), le découpage du travail
et le temps dans [`conception/planification-2026-11-13.md`](conception/planification-2026-11-13.md).

## 1. Le cas

Une filiale d'un groupe bancaire veut rencontrer les directions financières de grandes entreprises européennes pour leur proposer
des services financiers intégrés à leur ERP (scénario fictif). Douze sociétés sont à préparer : SSAB, voestalpine,
Barilla, Stadler Rail, LVMH, Vattenfall, Servier, Fresenius, Nokia, Saint-Gobain, Deutsche Telekom, Verallia.

Pour chacune, quatre informations, chacune avec sa preuve :

1. l'ERP en place ;
2. la plateforme d'achats ;
3. le TMS et la trésorerie ;
4. les produits de financement court terme déjà en place (affacturage, titrisation de créances, supply chain finance,
   escompte dynamique, billets de trésorerie, ligne de crédit renouvelable, crédit documentaire).

S'y ajoutent le directeur financier ou le trésorier nommé par la société et un signal récent sur la finance ou les
systèmes d'information.

Les contraintes du cas :

- sources publiques seulement ;
- trois heures de construction au plus, mesurées par une horloge (`sorties/journal/horloge.jsonl`), la planification
  comptée à part ;
- l'outil fait le travail : aucune cellule livrée n'est écrite à la main ;
- un coût par société.

## 2. Le principe : le modèle cherche, le code juge

Un modèle de langue trouve vite une information plausible et sait la présenter avec assurance. Son assurance n'est pas
une preuve. Une preuve est une phrase de la société, ou d'un tiers qui la nomme, retrouvée dans la page citée. L'outil
est construit sur cette règle, que résume la formule « pas de source, pas d'exploitation ».

Le travail est donc partagé en deux.

- **Le modèle** cherche sur le web, lit les pages et remplit un schéma fermé : une valeur prise dans une liste, une
  citation de 25 mots au plus, l'adresse de la page, sa date.
- **Le code** relit chaque page citée, y retrouve la citation, recalcule le type de source d'après le domaine, contrôle
  la date et la présence de la société, puis fixe le niveau de confiance par une table. Le modèle ne note jamais sa
  propre confiance.

Une erreur ne se corrige pas dans le tableur. Elle se corrige dans une règle du code, une liste ou la consigne du modèle,
puis la société est relancée (section 7).

## 3. La chaîne, en six étapes

| Étape | Qui | Module |
|---|---|---|
| 1. Résoudre la société | Code | `resolveur.py` |
| 2. Chercher | Modèle | `agent.py`, `sous_agents.py` |
| 3. Lire | Modèle, puis code | `lecteur.py` |
| 4. Extraire | Modèle | `schema.py`, `listes.py` |
| 5. Vérifier et noter | Code | `verificateur.py`, `confiance.py`, `relecture.py` |
| 6. Écrire | Code | `fiche.py`, `brief.py`, `tableur.py`, `textes.py`, `rapport.py` |

Les modules sont dans [`outil/prepa_rdv/`](outil/prepa_rdv/). Le déroulé d'une société est dans `run.py`.

### 3.1 Résoudre la société

Le code cherche la société dans Wikidata (étiquette exacte, puis recherche), contrôle son identifiant LEI dans GLEIF et
retient le nom légal, le pays, le statut (coté, privé, public), le site et les domaines. Une table locale prend le
relais si Wikidata refuse le client. Un doute reste marqué comme tel dans la fiche et dans le brief.

Les domaines servent plus loin : une page sur le domaine de la société est une source de la société.

### 3.2 Chercher

L'agent suit un plan de requêtes fixe par champ, en anglais et dans la langue du siège, écrit au journal de la société.
Il ouvre au plus 20 pages par société. La consigne principale (version `6ee5257d0713`) est reproduite dans
[« Ton outil »](sorties/livrables/ton-outil.md) ; la demande propre à chaque société est dans
`sorties/societes/<société>/demande.md`.

### 3.3 Lire

L'agent lit les pages avec les outils de recherche et de lecture du fournisseur. Le code relit ensuite lui-même chaque
page citée, avec ces règles :

- `robots.txt` est respecté ; une pause d'une seconde sépare deux requêtes vers le même hôte ; l'identité annoncée
  porte un moyen de contact ; les pages lues sont gardées au cache.
- Un refus (robots, HTTP 401, 403, 429) n'est jamais contourné. La trouvaille reste « non trouvé » tant que le code n'a
  pas relu la page, sauf seconde lecture concordante (section 3.5).
- Le HTML passe par `trafilatura`, le PDF par `pdftotext` s'il est présent, sinon par `pypdf`. Un rapport annuel se
  découpe en fenêtres de texte autour des mots-clés du champ, car un PDF de 300 pages pèserait des centaines de milliers
  de jetons s'il était lu en entier (D2).
- Quand la citation manque et que la page lue directement fait moins de 4 000 caractères, le code relit la page rendue
  par JavaScript (Jina Reader, service gratuit, 20 requêtes par minute). Jamais après un refus (D16).

### 3.4 Extraire

La réponse de l'agent est validée contre un schéma fermé (`pydantic`). Chaque valeur doit appartenir à une liste fermée
(ERP, plateformes d'achats, TMS, produits de financement : `listes.py`), avec ses alias (« S/4 HANA » pour SAP S/4HANA,
par exemple). La citation compte 25 mots au plus. Une réponse hors schéma est refusée à la réception.

### 3.5 Vérifier et noter

Chaque trouvaille passe ces contrôles, dans l'ordre (cahier des charges, section 6.5) :

1. **La page.** Le code relit la page citée. Une page introuvable rejette la trouvaille.
2. **La citation.** Elle doit figurer dans le texte relu, à une similarité de 0,95 au moins (RapidFuzz), après
   normalisation des ligatures, des apostrophes et du balisage Markdown que laisse un lecteur de pages.
3. **La réparation.** Si la citation manque mais que la page porte la valeur (produit, personne, noms propres du
   signal), le code garde le passage de la page le plus proche, de 25 mots au plus, recopié tel quel. Le niveau est alors
   plafonné à « probable », et la fiche garde la citation du modèle et son score (D14).
4. **La société.** Elle doit être nommée à côté de la citation. Nommée plus loin, la trouvaille reste « probable » ;
   absente de la page, elle est rejetée.
5. **La source.** Le code recalcule le type de source d'après le domaine (tableau de la section 5) et remplace celui
   que le modèle a proposé. Sur ce lot, le code a corrigé le type proposé 59 fois sur 185
   (`sorties/journal/bilan-final.json`).
6. **La date.** Elle est lue dans la page ou dans la citation, puis comparée à la fenêtre de fraîcheur de son type de
   source.

Le niveau se fixe ensuite par une table (section 4), puis chaque champ se synthétise :

- deux valeurs incompatibles au même niveau forment une contradiction, et les deux sont affichées ;
- une valeur que seule une base de données commerciale (P5) appuie n'entre pas dans le brief : elle sert de second avis
  (D19) ;
- pour les dirigeants, le code distingue le directeur financier, le directeur désigné, le responsable de la trésorerie,
  l'adjoint et les autres postes. Une contradiction ne vaut qu'entre deux directeurs financiers (D17).

**La seconde lecture à l'aveugle.** Quand le site refuse la lecture au code, un second agent rouvre la page avec ses
propres moyens, sans connaître la citation du premier, et recopie un passage de 15 mots au plus. Les deux lectures
s'accordent quand le plus court des deux textes figure dans l'autre à 0,95, sur au moins six mots qui nomment la
valeur. La trouvaille entre alors, au plus « probable », puisque le code n'a pas lu la page lui-même (D15, D18).

### 3.6 Écrire

- Une fiche JSON par société (`fiche.json`), avec chaque trouvaille, chaque contrôle et sa provenance.
- Un brief d'une page par société : HTML, puis PDF par Chrome sans affichage. La taille du texte diminue jusqu'à ce que
  chaque brief tienne sur une page, et le code vérifie que chaque nombre du brief figure dans la fiche.
- `cartographie.xlsx` : une ligne par société, et une feuille « Audit » de 36 cellules tirées au sort (graine fixe),
  jugées par un agent auditeur (section 10, D20).
- `trouvailles.xlsx` : toutes les trouvailles, retenues ou rejetées, avec les résultats de chaque contrôle.
- Les journaux (section 11) et les deux textes, « Ton outil » et « Et à 200 sociétés ? », écrits par le code depuis les
  journaux (`textes.py`).

## 4. Les niveaux de confiance

| Niveau | Condition |
|---|---|
| confirmé | citation vérifiée dans une page de la société (24 mois) ou d'un tiers qui la nomme (36 mois), société nommée à côté |
| probable | citation vérifiée, mais source hors fenêtre, sans date, de presse, d'offre d'emploi, ou société nommée à distance ; ou citation réparée ; ou seconde lecture concordante |
| non trouvé | aucune citation vérifiée après le plan de requêtes. Ce n'est pas une absence prouvée |
| absence déclarée | un document de la société dit qu'elle n'a pas le produit |
| contradiction | deux valeurs incompatibles au même niveau : les deux sont affichées |

## 5. Les sources et leur fraîcheur

| Type | Source | Fenêtre de fraîcheur |
|---|---|---|
| P1 | Document de la société : rapport, présentation, communiqué, page officielle | 24 mois |
| P2 | Document d'un tiers qui nomme la société : éditeur, intégrateur, association | 36 mois |
| P3 | Presse ou agence de notation | 24 mois |
| P4 | Signal indirect : offre d'emploi, intervention en conférence | 12 mois |
| P5 | Base de données commerciale | Second avis seulement |

Les fenêtres sont des valeurs de départ. Sur ce lot, 47 trouvailles retenues sur 163 (29 %) sont hors fenêtre ou sans
date ; elles restent « probables ».

## 6. L'accès au modèle et le compte des jetons

Le cas prévoyait une clé de la Console Anthropic, avec un plafond, pour mesurer le coût au jeton (D3). Faute de clé,
l'outil passe par Claude Code (D12, D13) :

- **par des sous-agents d'une session Claude Code** (`--acces sous-agents`), le chemin du lot des douze :
  `prepa-rdv demander` écrit une demande par société, un sous-agent cherche et écrit `agent-sortie.json`, puis
  `prepa-rdv recevoir` valide la réponse contre le schéma fermé avant que le code reprenne (relecture, contrôles,
  niveau, brief) ;
- **par `claude -p`** sur l'abonnement (`--acces claude-cli`), pour une démonstration sur une société nouvelle.

Les agents de recherche et de seconde lecture ont tourné sur Sonnet 5.5. La seconde lecture de Barilla, arrêtée une
première fois par un garde-fou de l'API, a été relancée sur Opus 5.5. Les agents auditeurs ont tourné sur Opus 5.5, un
autre modèle que celui des cellules qu'ils jugent (D20) : `prepa-rdv demander-audit` écrit une demande par lot,
`prepa-rdv recevoir-audit` valide les verdicts.

Chaque jeton du projet est compté : les appels de l'outil dans un registre en ajout seul, les sessions de
développement dans leurs transcriptions (`jetons_dev.py`), par phase (planification, construction, sonde, run, audit) et par
modèle. Le coût en dollars est une estimation au tarif de liste de chaque modèle, car l'accès passe par un abonnement.
Les totaux sont dans [« Ton outil »](sorties/livrables/ton-outil.md), section « Jetons de tout le projet ».

## 7. Comment une erreur se corrige

Chaque erreur vue par un contrôle s'écrit dans `sorties/journal/erreurs.jsonl`, avec sa cause. Elle ne compte comme
corrigée que si un changement du code ou de la consigne lui est associé, suivi d'une relance qui en montre l'effet.

Sur ce lot, 14 erreurs relevées : 5 citations inventées, 3 erreurs d'entité, 2 pages lues incomplètes, 2 citations
reformulées, 2 autres. Cinq sont corrigées. Les neuf autres sont écartées sans réparation possible : la trouvaille reste
« non trouvé » et n'atteint ni le brief ni la cartographie. Quatre exemples, avec le changement et la relance, sont dans
[« Ton outil »](sorties/livrables/ton-outil.md).

Deux erreurs que le journal avait d'abord mises au compte du modèle venaient du lecteur de l'outil : la phrase citée
manquait à la lecture directe et figurait dans la page rendue par JavaScript (2 418 caractères lus sur 28 285 pour
Barilla, 898 sur 18 842 pour Saint-Gobain). D'où la relecture rendue (D16).

Le contrôle lui-même s'est trompé une fois. Il cherchait la citation du premier agent (25 mots au plus) dans le passage
du second (15 mots au plus), si bien que l'accord était manqué dès que la citation était la plus longue des deux. Il
cherche désormais le plus court des deux textes dans l'autre. Sur les 18 lignes relues avant la correction, l'accord
passe de 5 à 11 (D18).

## 8. Les décisions

Elles viennent du plan de travail, qui n'est pas publié. Chaque décision est datée dans le journal
`sorties/journal/decisions.md`.

| | Décision | Pourquoi |
|---|---|---|
| D1 | Six étapes. Le modèle remplit un schéma fermé ; le code vérifie les citations, recalcule les nombres et fixe le niveau. | « Pas de source, pas d'exploitation. » Le contrôle se montre en direct. |
| D2 | Deux chemins de lecture. A : l'agent lit les pages web avec les outils du fournisseur. B : les rapports annuels se lisent en local, en fenêtres autour des mots-clés. | D'après la documentation de l'API, une page de PDF pèse 1 500 à 3 000 jetons : un rapport de 300 pages lu en entier coûte trop. L'outil de lecture du fournisseur ne rend pas les pages JavaScript. |
| D3 | Mesurer le coût à la facturation de l'API, avec une clé dédiée et un plafond. Remplacée par D12. | Le cas demande un coût par société. |
| D4 | Ni LinkedIn ni base de contacts. Les contacts entrent en suggestion non vérifiée : directeur financier nommé par la société, adresses générales publiées. Pas de ligne directe, pas de sonde SMTP ; l'option `--sans-contacts` retire le bloc. | Le cahier des charges (section 10) borne le module pour limiter le risque juridique et d'image. |
| D5 | Une vitrine statique, construite après les livrables ; la démonstration tourne en local. Non construite. | Pas de clé sur un site public. Le cas ne demande pas de site. |
| D6 | Le dépôt est public, sous licence MIT, et neuf : aucun fichier d'un autre projet n'y entre. | Le cas ne porte que sur cet outil. |
| D7 | Aucun nom de client ni de travail privé dans les livrables ou le dépôt. La commande `depot` le vérifie avant publication. | Confidentialité. |
| D8 | Départ sur Sonnet 5.5. On garde le modèle le moins cher qui passe le seuil de vérification. | Sonnet 5.5 coûte la moitié d'Opus 5.5 au tarif de liste. |
| D9 | Une erreur se corrige dans une règle, une consigne ou une liste, puis on relance le champ. Les cellules livrées sont celles que l'outil a écrites. | Le cas demande que l'outil fasse le travail. |
| D10 | Les outils libres se choisissent à la licence, à la maintenance et à l'utilité : `trafilatura`, `pypdf`, `RapidFuzz`, `httpx`, `pydantic`, `openpyxl`. Ni couche d'abstraction du modèle, ni framework d'agent. Dépendances épinglées avec leurs empreintes (`uv.lock`). | Chaque dépendance est du code qu'on ne contrôle pas : `litellm` a publié des versions piégées le 24 mars 2026. Un framework d'agent contredit le schéma fermé. |
| D11 | Un modèle gratuit n'est pas le chemin du cas ; il reste un plan de repli décrit, non construit. | Choix « sources gratuites, modèle payé ». La qualité d'extraction en suédois et en finnois n'est pas vérifiée sur les modèles gratuits. |
| D12 | Le modèle passe par Claude Code, sans clé de la Console. L'outil garde les deux accès. Tous les jetons du projet sont comptés. | Pas de clé disponible. Le coût en dollars devient une estimation au tarif de liste ; la mesure est le jeton. |
| D13 | Accès par des sous-agents de la session : une demande par société, une réponse validée contre le schéma, puis le code reprend. | Les sous-agents utilisent l'authentification de l'application. Les jetons de chaque agent se lisent dans sa transcription. |
| D14 | Réparation de citation : si la page porte la valeur mais pas la phrase du modèle, le code garde le passage le plus proche, recopié tel quel, au plus « probable ». | La sonde a montré deux cas sur 33 trouvailles : une phrase traduite par le modèle, une phrase d'un communiqué prêtée à une page de presse. La page portait bien l'information. |
| D15 | La seconde lecture à l'aveugle est un garde-fou, pas une source de preuves : au plus « probable ». Amendée par D18. | Sur une page refusée au code, seul un autre lecteur, qui ne connaît pas la citation, peut la recouper. |
| D16 | Rendu JavaScript à la demande, quand la page lue fait moins de 4 000 caractères et que la citation manque. Jamais après un refus. | Deux erreurs venaient de la lecture directe, pas du modèle. Dix pages ont été relues rendues sur les douze sociétés. |
| D17 | Les rôles des dirigeants se lisent dans la valeur et, à défaut, dans la citation. Une contradiction ne vaut qu'entre deux directeurs financiers. | Un trésorier et un directeur financier ne se contredisent pas : les afficher en contradiction aurait trompé le lecteur du brief. |
| D18 | Les deux lectures s'accordent quand le plus court des deux textes figure dans l'autre à 0,95, sur au moins six mots qui nomment la valeur. Le niveau reste plafonné à « probable ». | Le premier test ne cherchait que dans un sens et manquait l'accord par construction (section 7). |
| D19 | Une base de données commerciale (P5) ne fait pas seule un champ du brief. L'identité n'est pas concernée. | La règle était écrite au cahier des charges et le code ne l'appliquait pas. Deux trouvailles concernées, toutes deux chez Barilla. |
| D20 | Les 36 cellules de l'audit sont jugées par des sous-agents auditeurs d'un autre modèle que les agents de recherche (Opus 5.5), en trois lots de douze. L'auditeur reçoit ce qu'une personne voit dans la feuille (société, champ, valeur, citation, lien), sans le niveau ni les contrôles du code. Quatre verdicts : juste, partiel, faux, invérifiable ; pour partiel et faux, un écart pris dans une liste fermée. Le code refuse une réponse qui oublie une cellule, en juge une deux fois ou se contredit. | Le cas veut un outil qui fait le travail, sans geste à la main. Un modèle qui en juge un autre ne vaut pas une personne : les livrables le disent, et les verdicts partiels et faux sont les premiers à relire. |
| D21 | Deux règles d'affichage, après l'audit (`affichage.py`). La cellule dit l'entité que la page nomme quand ce n'est pas la société (filiale, division, pays). Pour un ERP, une plateforme d'achats ou un TMS, elle dit « migration prévue ou en cours » quand le commentaire du modèle le dit. Les deux règles valent au brief, à la cartographie et à l'audit. Les cellules en écart sont rejugées telles qu'elles s'affichent, et un second tirage de 12 cellules nouvelles (graine 2027) mesure la porte G4. | Sur les 9 écarts du premier tirage, 8 tenaient à l'affichage. Le modèle avait noté l'entité et le projet, et la cellule les taisait. Corriger la règle plutôt que la cellule garde l'outil sans geste à la main. Le niveau reste le même, la preuve aussi. Mesuré ensuite : la règle du projet rend justes les 2 cellules fausses, celle de l'entité ne change aucun des 6 verdicts « filiale ou division ». |

## 9. Ce que les journaux mesurent

D'après `sorties/journal/bilan-final.json` et [« Ton outil »](sorties/livrables/ton-outil.md) :

| Mesure | Valeur |
|---|---|
| Trouvailles | 185 |
| Retenues | 163 : 55 confirmées, 107 probables, une absence déclarée |
| Rejetées | 22 : citation introuvable (14), société non nommée (6), page introuvable (2) |
| Retenues hors fenêtre ou sans date | 47 sur 163 (29 %) |
| Pages relues par le code | 98 ; 17 refusées ou illisibles pour lui |
| Citations retrouvées mot pour mot | 134 sur les 141 trouvailles dont la page est lisible ; 3 réparées, 4 écartées |
| Secondes lectures | 26 lignes relues, 15 concordantes |
| Pages relues rendues par JavaScript | 10 |
| Type de source corrigé par le code | 59 sur 185 |
| Temps d'agent par société | 16,4 minutes en moyenne |
| Jetons par société | 5,7 millions traités en moyenne, 2,39 $ estimés |
| Audit, premier tirage | 36 cellules (graine 2026), jugées par des auditeurs Opus 5.5 : 24 justes sur 33 vérifiables (73 %), 7 partielles, 2 fausses, 3 invérifiables |
| Audit, cellules rejugées | Les 9 cellules en écart, rejugées telles qu'elles s'affichent après D21 : 2 justes (les deux « projet ou évaluation »), 7 partielles. Premier tirage corrigé : 26 sur 33 vérifiables (79 %) |
| Audit, second tirage | 12 cellules neuves (graine 2027), après les règles d'affichage (D21) : 9 justes sur 9 vérifiables, 3 invérifiables |

Le temps de construction, mesuré par l'horloge, et les jetons de tout le projet sont dans « Ton outil ».

## 10. Ce que l'outil ne voit pas

- **L'extrapolation.** Une citation exacte peut ne pas dire ce que le modèle en conclut. Aucun contrôle du code ne le
  voit. Des auditeurs d'un autre modèle la cherchent sur un échantillon tiré au sort (D20). Au premier tirage, 9 cellules
  sur 33 vérifiables étaient partielles ou fausses. La règle du projet (D21) rend justes les 2 fausses. Les 6 cellules
  d'une filiale restent partielles pour l'auditeur, même avec l'entité affichée : une page sur une filiale ne dit pas
  le système du groupe, et c'est une question de périmètre que le code ne tranche pas.
  Ce sont des modèles qui en jugent un autre : leurs verdicts partiels, faux et invérifiables restent à relire par une
  personne, dans la feuille « Audit » de la cartographie.
- **L'absence.** « Non trouvé » veut dire que le plan de requêtes n'a rien donné de vérifiable. Ce n'est pas la preuve
  que la société n'a pas le produit.
- **Les pages fermées.** Sur un site qui refuse la lecture au code, la trouvaille dépend de la seconde lecture, qui ne
  dépasse jamais « probable ».
- **La fraîcheur.** 29 % des trouvailles retenues sont hors fenêtre ou sans date. Les fenêtres sont des valeurs de
  départ, pas encore réglées par champ.
- **La recherche.** Elle est faite par l'agent avec les outils du fournisseur. Une relance peut trouver d'autres pages ;
  le cache garde celles qui ont été lues.
- **Les contacts.** Ce sont des suggestions non vérifiées. Aucune adresse n'est testée, aucun message n'est envoyé.
- **Le coût.** C'est une estimation au tarif de liste, pas une facture. L'accès par une clé d'API n'est pas branché.

## 11. Plan du dépôt

```text
README.md                  ce qu'est le dépôt, les livrables, comment reproduire
METHODOLOGIE.md            ce document
LICENSE                    MIT
LICENCES-TIERS.md          licence de chaque dépendance, écrite par la commande depot
conception/
  cahier-des-charges-2026-11-13.md   exigences, règles de confiance, contrôles, critères d'acceptation
  planification-2026-11-13.md        lots, portes de contrôle, temps prévu et mesuré
outil/
  README.md                installer, accès au modèle, commandes
  pyproject.toml, uv.lock  dépendances épinglées avec leurs empreintes
  societes.csv             les douze sociétés, dans l'ordre des briefs
  prepa_rdv/               le code (un module par étape, section 3)
  tests/                   tests hors ligne
sorties/
  livrables/               briefs.pdf, cartographie.xlsx, trouvailles.xlsx, ton-outil, a-200-societes, controles.json
  societes/<société>/      demande.md et demande.json (la demande à l'agent), agent-sortie.json (sa réponse brute),
                           agent.json, fiche.json (trouvailles vérifiées), brief.html, journal.jsonl (chaque étape),
                           relecture-demande.md et relecture-sortie.json (seconde lecture)
  audit/                   demande-N.md et demande-N.json (un lot de cellules pour un auditeur), sortie-N.json (sa
                           réponse brute), verdicts.json (les verdicts validés de tous les lots)
  journal/
    horloge.jsonl          début, pauses, reprises et fin de la construction
    decisions.md           les décisions et les relances, datées
    erreurs.jsonl          chaque erreur vue par un contrôle, sa cause, son changement, sa relance
    bilan-final.json       les mesures du lot des douze
    agents-outil.jsonl     chaque agent de l'outil, rattaché à sa société ou à l'audit
    jetons-dev.json        les jetons des sessions de développement
    bilan-*.json           les bilans intermédiaires : sonde, lot, avant la correction de l'accord
```

## 12. Reproduire

```bash
cd outil
uv sync --frozen
uv run pytest -q                                                              # tests hors ligne
PREPA_RDV_SORTIES=../sorties uv run python -m prepa_rdv livrables --ordre societes.csv   # briefs et tableurs
uv run python -m prepa_rdv societe "Nom de la société" --acces claude-cli    # une société nouvelle
```

La commande `livrables` recompose les briefs et les tableurs depuis les fiches de `sorties/societes/` sans appeler le
modèle. La commande `societe` refait une société de bout en bout ; elle demande un abonnement Claude Code
(`claude auth login`). Une relance ne refait que ce qui a changé ; `--forcer` ignore le cache.
