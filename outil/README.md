# prepa-rdv

Prépare un rendez-vous avec la direction financière d'une grande entreprise, à partir d'informations publiques.
Pour chaque société, l'outil cherche l'ERP, la plateforme d'achats, le TMS et les financements court terme en place.
Chaque information porte sa citation, son adresse, sa date et un niveau de confiance (confirmé, probable, non trouvé).

Le principe : le code juge avant le modèle. Le modèle cherche, lit et remplit un schéma fermé. Le code relit chaque
page citée, vérifie la citation mot pour mot, recalcule le type de source, contrôle la date et la société nommée,
puis fixe le niveau de confiance par une table. Aucune cellule n'est corrigée à la main.

## Les six étapes

1. **Résoudre** la société : Wikidata, puis GLEIF pour contrôler le LEI. Un doute reste marqué « à confirmer ».
2. **Chercher** et 3. **lire** : un agent (recherche web et lecture de pages) suit un plan de requêtes fixe par champ,
   en anglais et dans la langue du siège.
4. **Extraire** : l'agent répond dans un schéma fermé, avec une citation de 25 mots au plus par information.
5. **Vérifier et noter** : le code applique les contrôles de `prepa_rdv/verificateur.py` et la table de `prepa_rdv/confiance.py`.
   Quand la citation du modèle manque à la page, le code relit la page rendue par JavaScript si elle est pauvre, puis garde,
   s'il y en a un, le passage de la page qui porte la valeur (niveau plafonné à « probable », citation d'origine conservée).
6. **Écrire** : fiche JSON, brief d'une page (HTML puis PDF par Chrome), deux tableurs, journaux. Les trois PDF et les deux tableurs
   partagent une mise en page, dans `prepa_rdv/gabarit.py`.

## Installer

```bash
uv sync
uv run pytest            # tests hors ligne, sans réseau ni modèle
```

Python 3.12. Chrome ou Chromium sert au PDF (variable `CHROME_BIN` si besoin). `pdftotext` (poppler), s'il est présent,
accélère la lecture des rapports annuels.

## Accès au modèle

Un des trois suffit.

- **Abonnement Claude Code** (`--acces claude-cli`, par défaut) : lancer une fois `claude auth login`. L'outil appelle
  `claude -p`. Le coût en dollars est estimé au tarif de liste, il n'est pas facturé.
- **Sous-agents d'une session Claude Code** (`--acces sous-agents`) : l'outil écrit une demande par société
  (`prepa-rdv demander`), la session lance un sous-agent par société, qui cherche sur le web et écrit sa réponse dans un
  fichier, puis `prepa-rdv recevoir` la valide contre le schéma fermé. Aucune connexion en plus.
- **Clé de la Console Anthropic** : variable `ANTHROPIC_API_KEY`. Cet accès n'est pas encore branché dans l'outil.

Quel que soit l'accès, le reste est identique : le code relit les pages citées, vérifie, note et écrit.

Variables facultatives : `PREPA_RDV_CONTACT` (identité annoncée aux sites lus : une adresse de contact ou l'adresse
du dépôt), `PREPA_RDV_SORTIES` (dossier des résultats, `sorties` par défaut), `CHROME_BIN`.

## Utiliser

```bash
uv run python -m prepa_rdv essai-modele           # appel à vide : l'accès marche, et son poids de base
uv run python -m prepa_rdv resoudre Nokia         # identité de la société
uv run python -m prepa_rdv societe Nokia          # une société, de bout en bout
uv run python -m prepa_rdv lot societes.csv       # plusieurs sociétés, deux à la fois
uv run python -m prepa_rdv livrables --ordre societes.csv   # PDF des briefs et deux tableurs
uv run python -m prepa_rdv jetons                 # jetons de tout le projet
```

Pour une démo sur une société nouvelle : `uv run python -m prepa_rdv societe "<Société>" --acces claude-cli` après
`claude auth login`, ou, dans une session Claude Code, `demander`, un sous-agent, `recevoir`, puis `societe --acces sous-agents`.

Une relance ne refait que ce qui a changé : l'identité, la sortie du modèle et les pages lues sont gardées au cache.
`--forcer` les ignore. `--sans-contacts` retire le bloc contacts des briefs.

## Audit par un agent

```bash
uv run python -m prepa_rdv demander-audit             # 36 cellules tirées au sort, trois demandes de douze
uv run python -m prepa_rdv recevoir-audit 1 --agent-id <id>   # verdicts du lot 1 validés, agent compté en phase audit
uv run python -m prepa_rdv demander-audit --second    # cellules en écart rejugées telles qu'elles s'affichent, 12 cellules neuves
uv run python -m prepa_rdv livrables --ordre societes.csv     # la feuille « Audit » reprend les verdicts
```

Entre les deux commandes, la session lance un sous-agent auditeur par lot, d'un autre modèle que les agents de recherche.
Il lit `sorties/audit/demande-N.md`, ouvre chaque lien et écrit `sortie-N.json` : juste, partiel, faux ou invérifiable,
avec l'écart, une raison et le passage de la page. Il ne voit ni le niveau ni les contrôles du code. `recevoir-audit`
refuse une réponse qui oublie une cellule, en juge une deux fois ou se contredit.

Après un premier audit, `--second` écrit deux lots de plus : les cellules partielles ou fausses, rejugées telles que les
règles d'affichage les montrent (`affichage.py`), et 12 cellules jamais tirées (graine 2027), qui mesurent la porte G4.
La feuille « Audit » ajoute le verdict après correction, et la feuille « Audit, second tirage » le second échantillon.

## Copie publique

```bash
uv run python -m prepa_rdv depot ../../prepa-rdv --lien-outil https://github.com/FiExplorer11020/prepa-rdv --publier
```

`depot` construit la copie publique du cas à côté du dossier de travail : liste blanche (le cache des pages lues ne part
pas), chemins de la machine remplacés, remplacements lus dans un fichier privé qui ne part jamais (`depot-prive.json`),
adresses nominatives déduites retirées puis briefs et tableurs recomposés, liste des licences, `pip-audit`. Elle analyse
ensuite chaque fichier, PDF et tableurs compris, et ne fait le commit et le push (`--publier`) que si l'analyse ne
trouve rien.

## Niveaux de confiance

| Niveau | Condition |
|---|---|
| confirmé | citation vérifiée dans une page de la société (24 mois) ou d'un tiers qui la nomme (36 mois), société nommée à côté |
| probable | citation vérifiée, mais source hors fenêtre, sans date, de presse, d'offre d'emploi, ou société nommée à distance |
| non trouvé | aucune citation vérifiée après le plan de requêtes. Ce n'est pas une absence prouvée |
| absence déclarée | un document de la société dit qu'elle n'a pas le produit |
| contradiction | deux valeurs incompatibles au même niveau : les deux sont affichées |

Les fenêtres de fraîcheur sont des valeurs de départ. Le type de source (société, éditeur ou intégrateur, presse,
offre d'emploi) se recalcule d'après le domaine : le modèle le propose, le code décide.

## Politesse et limites

- `robots.txt` est respecté. Un refus (robots, HTTP 401, 403, 429) n'est jamais contourné : la citation reste « non trouvé »
  tant que le code n'a pas pu relire la page. Une seconde lecture à l'aveugle peut la confirmer, au plus « probable » : un autre
  agent rouvre la page avec ses propres moyens, sans connaître la citation, et recopie un passage de 15 mots au plus. Le code ne
  retient la trouvaille que si l'un des deux textes figure dans l'autre à 0,95, sur au moins 6 mots qui nomment la valeur.
  Sur les douze sociétés, 15 lignes relues sur 26 s'accordent.
- Une base de données commerciale (P5) ne fait jamais seule un champ du brief : elle sert de second avis.
- Une page lisible dont la citation manque et qui fait moins de 4 000 caractères est relue une fois rendue par JavaScript
  (Jina Reader, 20 requêtes par minute sans clé). Jamais après un refus.
- Une pause d'une seconde sépare deux requêtes vers le même hôte. L'identité annoncée porte un moyen de contact.
- Les contacts sont des suggestions non vérifiées : adresses générales publiées, et une adresse nominative déduite
  seulement si le dirigeant est nommé par la société et si deux adresses du même domaine suivent le même motif.
  Pas de sonde SMTP, pas d'envoi, pas de base tierce.
- Les jetons de chaque appel sont écrits dans `sorties/journal/jetons.jsonl`, en ajout seul.

## Licence

MIT. Voir `LICENSE`.
