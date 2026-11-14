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

- **Le plan de travail.** Il porte des notes personnelles. Ses décisions, de D1 à D19, sont reprises avec leurs raisons
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
recompose les briefs et les tableurs depuis les fiches nettoyées. Elle analyse ensuite chaque fichier, PDF et tableurs
compris, à la recherche de noms à taire, de secrets, de chemins de la machine et des adresses retirées. Elle écrit la
liste des licences et lance `pip-audit`. Elle ne publie que si l'analyse ne trouve rien.

## Licence

MIT, voir [LICENSE](LICENSE). Licences des dépendances : [LICENCES-TIERS.md](LICENCES-TIERS.md).
