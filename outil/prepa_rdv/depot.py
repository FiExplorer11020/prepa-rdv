"""La copie publique du cas : code, livrables, journaux et méthode, nettoyés puis analysés.

`prepa-rdv depot DOSSIER` construit le dossier du dépôt public depuis le dossier de travail :

1. Liste blanche de ce qui part (le cache des pages lues reste sur la machine).
2. Chemins absolus de la machine remplacés par `<racine>`.
3. Remplacements exacts lus dans un fichier privé, qui ne part jamais : le code publié ne
   contient ni les noms à taire ni leur liste.
4. Adresses nominatives déduites retirées des fiches, puis briefs et tableurs recomposés
   depuis les fiches nettoyées.
5. Analyse de chaque fichier, PDF et tableurs compris : noms interdits, secrets, chemins de
   la machine, adresses retirées, taille. Liste des licences des dépendances, `pip-audit`.

La copie n'est publiable que si l'analyse ne trouve rien ; `--publier` fait alors le commit
et le push, et refuse sinon.
"""
from __future__ import annotations

import getpass
import html
import json
import re
import shutil
import subprocess
import sys
import zipfile
from dataclasses import dataclass, field
from importlib import metadata
from pathlib import Path
from typing import Any

# Ce qui part, relatif à la racine du cas (le dossier qui porte outil/ et sorties/).
FICHIERS = {
    "depot/README.md": "README.md",
    "depot/METHODOLOGIE.md": "METHODOLOGIE.md",
    "depot/gitignore": ".gitignore",
    "outil/LICENSE": "LICENSE",
    "cahier-des-charges-2026-11-13.md": "conception/cahier-des-charges-2026-11-13.md",
    "planification-2026-11-13.md": "conception/planification-2026-11-13.md",
}
DOSSIERS = {
    "outil": "outil",
    "sorties/livrables": "sorties/livrables",
    "sorties/societes": "sorties/societes",
    "sorties/journal": "sorties/journal",
}
NOMS_EXCLUS = {".venv", "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", ".DS_Store", ".git"}
SUFFIXES_EXCLUS = {".pyc", ".pyo"}
SUFFIXES_TEXTE = {".md", ".json", ".jsonl", ".html", ".csv", ".py", ".toml", ".txt", ".lock", ".cfg", ".ini", ".yaml", ".yml", ""}
TAILLE_MAX = 10_000_000
FICHIER_PRIVE = "depot-prive.json"

# Un chemin de la machine qui mène au dossier du cas, puis tout autre chemin personnel.
_CHEMIN_CAS = re.compile(r"/(?:Users|home)/[^\s\"'<>]*?/cas-pratique(?=[/\"'\s<>]|$)")
_CHEMIN_PERSO = re.compile(r"/(?:Users|home)/[A-Za-z0-9._-]+")
_DOSSIER_PROJET = re.compile(r"-(?:Users|home)-[A-Za-z0-9._]+-")
SECRETS = {
    "clé Anthropic": re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"),
    "jeton GitHub": re.compile(r"(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}"),
    "clé AWS": re.compile(r"AKIA[0-9A-Z]{16}"),
    "jeton Slack": re.compile(r"xox[abprs]-[A-Za-z0-9-]{10,}"),
    "clé privée": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "secret en clair": re.compile(r"(?i)(?:api[_-]?key|secret|password|passwd|token)[\"']?\s*[:=]\s*[\"'][A-Za-z0-9_\-+/]{16,}[\"']"),
}


@dataclass
class Constat:
    fichier: str
    motif: str
    extrait: str


@dataclass
class Rapport:
    dossier: Path
    copies: int = 0
    chemins_remplaces: int = 0
    remplacements: dict[str, int] = field(default_factory=dict)
    adresses_retirees: list[str] = field(default_factory=list)
    livrables: dict[str, Any] | None = None
    livrables_ok: bool | None = None
    constats: list[Constat] = field(default_factory=list)
    non_lus: list[str] = field(default_factory=list)
    licences_douteuses: list[str] = field(default_factory=list)
    audit: dict[str, Any] | None = None

    @property
    def propre(self) -> bool:
        audit_ok = self.audit is None or self.audit.get("ok", False)
        return (not self.constats and not self.licences_douteuses and audit_ok and self.livrables_ok is not False
                and all(self.remplacements.values()))

    def resume(self) -> dict[str, Any]:
        return {
            "dossier": str(self.dossier), "fichiers_copies": self.copies, "chemins_remplaces": self.chemins_remplaces,
            "remplacements": self.remplacements, "adresses_nominatives_retirees": len(self.adresses_retirees),
            "livrables_recomposes": self.livrables_ok, "constats": [c.__dict__ for c in self.constats[:50]],
            "nombre_de_constats": len(self.constats), "fichiers_non_lus": self.non_lus,
            "licences_douteuses": self.licences_douteuses, "audit": self.audit, "propre": self.propre,
        }


def racine_du_cas() -> Path:
    """Le dossier qui porte outil/ et sorties/ : deux crans au-dessus de ce module."""
    return Path(__file__).resolve().parents[2]


def lire_prive(chemin: Path | None) -> dict[str, Any]:
    if chemin is None or not chemin.exists():
        return {"interdits": [], "remplacements": []}
    d = json.loads(chemin.read_text(encoding="utf-8"))
    return {"interdits": list(d.get("interdits", [])), "remplacements": [tuple(p) for p in d.get("remplacements", [])]}


def vider(dest: Path, racine: Path) -> None:
    """Vide le dossier de la copie, sauf .git. Refuse un dossier qui n'est pas une copie précédente."""
    dest = dest.resolve()
    if dest == racine or racine in dest.parents or dest in racine.parents:
        raise ValueError(f"{dest} touche le dossier de travail : la copie doit vivre à côté")
    if not dest.exists():
        dest.mkdir(parents=True)
        return
    contenu = [p for p in dest.iterdir() if p.name != ".git"]
    if contenu and not (dest / "outil" / "prepa_rdv" / "depot.py").exists():
        raise ValueError(f"{dest} n'est pas vide et ne ressemble pas à une copie précédente : rien n'est effacé")
    for p in contenu:
        if p.is_dir() and not p.is_symlink():
            shutil.rmtree(p)
        else:
            p.unlink()


def _exclu(p: Path) -> bool:
    return (any(part in NOMS_EXCLUS for part in p.parts) or p.suffix in SUFFIXES_EXCLUS
            or p.name == FICHIER_PRIVE or p.name == ".env" or p.name.startswith(".env."))


def copier(racine: Path, dest: Path) -> int:
    n = 0
    for src, cible in FICHIERS.items():
        if (racine / src).exists():
            (dest / cible).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(racine / src, dest / cible)
            n += 1
    for src, cible in DOSSIERS.items():
        for f in sorted((racine / src).rglob("*")):
            rel = f.relative_to(racine / src)
            if f.is_dir() or _exclu(rel):
                continue
            (dest / cible / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dest / cible / rel)
            n += 1
    return n


def normaliser(texte: str) -> tuple[str, int]:
    """Chemins absolus de la machine remplacés : celui du cas par <racine>, tout autre chemin personnel par ~."""
    texte, a = _CHEMIN_CAS.subn("<racine>", texte)
    texte, b = _CHEMIN_PERSO.subn("~", texte)
    texte, c = _DOSSIER_PROJET.subn("-~-", texte)
    return texte, a + b + c


def _fichiers(dest: Path) -> list[Path]:
    """Les fichiers que la publication emporterait : pour un dépôt git, ceux que `git add -A` prendrait ;
    sinon tout le dossier, hors environnements et caches locaux."""
    if (dest / ".git").exists():
        r = subprocess.run(["git", "-C", str(dest), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                           capture_output=True, text=True)
        if r.returncode == 0:
            return sorted({dest / x for x in r.stdout.split("\0") if x and (dest / x).is_file()})
    return sorted(p for p in dest.rglob("*") if p.is_file() and not any(
        part in NOMS_EXCLUS for part in p.relative_to(dest).parts))


def nettoyer_textes(dest: Path, remplacements: list[tuple[str, str]], rapport: Rapport) -> None:
    rapport.remplacements = {src: 0 for src, _ in remplacements}
    for f in _fichiers(dest):
        if f.suffix not in SUFFIXES_TEXTE:
            continue
        texte = f.read_text(encoding="utf-8", errors="strict")
        neuf, n = normaliser(texte)
        rapport.chemins_remplaces += n
        for src, pub in remplacements:
            if src in neuf:
                rapport.remplacements[src] += neuf.count(src)
                neuf = neuf.replace(src, pub)
        if neuf != texte:
            f.write_text(neuf, encoding="utf-8")


def caviarder_fiches(sorties: Path) -> list[str]:
    """Retire des fiches l'adresse nominative déduite (prénom.nom), jamais publiée par la société."""
    adresses = []
    for chemin in sorted((sorties / "societes").glob("*/fiche.json")):
        fiche = json.loads(chemin.read_text(encoding="utf-8"))
        contact = fiche.get("contact") or {}
        s = contact.get("suggestion")
        if not s:
            continue
        adresses.append(s["adresse"])
        contact["suggestion"] = None
        contact["retrait_public"] = "Adresse nominative déduite retirée de la copie publique."
        chemin.write_text(json.dumps(fiche, ensure_ascii=False, indent=1), encoding="utf-8")
    return adresses


def derniere_passe(dest: Path, adresses: list[str], rapport: Rapport) -> None:
    """Après la recomposition : chemins normalisés encore une fois, adresses retirées de tous les textes."""
    for f in _fichiers(dest):
        if f.suffix not in SUFFIXES_TEXTE:
            continue
        texte = f.read_text(encoding="utf-8")
        neuf, n = normaliser(texte)
        rapport.chemins_remplaces += n
        for a in adresses:
            neuf = re.sub(re.escape(a), "[adresse retirée]", neuf, flags=re.IGNORECASE)
        if neuf != texte:
            f.write_text(neuf, encoding="utf-8")


def recomposer_livrables(sorties: Path, lien_outil: str, ordre: list[str] | None) -> tuple[dict[str, Any], bool]:
    """Les briefs de chaque société, le PDF du lot et les tableurs, depuis les fiches de la copie."""
    from . import brief, run
    for chemin in sorted((sorties / "societes").glob("*/fiche.json")):
        fiche = json.loads(chemin.read_text(encoding="utf-8"))
        (chemin.parent / "brief.html").write_text(brief.html_document([brief.composer(fiche)]), encoding="utf-8")
    return run.livrables(sorties, ordre, lien_outil)


def texte_de(f: Path) -> str | None:
    """Le texte lisible d'un fichier de la copie ; None si son format n'est pas lu."""
    if f.suffix in SUFFIXES_TEXTE:
        return f.read_text(encoding="utf-8", errors="replace")
    if f.suffix == ".pdf":
        if shutil.which("pdftotext"):
            r = subprocess.run(["pdftotext", "-q", "-enc", "UTF-8", str(f), "-"], capture_output=True)
            if r.returncode == 0:
                return r.stdout.decode("utf-8", errors="replace")
        from pypdf import PdfReader
        return "\n".join(p.extract_text() or "" for p in PdfReader(str(f)).pages)
    if f.suffix in {".xlsx", ".docx", ".pptx"}:
        morceaux = []
        with zipfile.ZipFile(f) as z:
            for n in z.namelist():
                if n.endswith(".xml") or n.endswith(".rels"):
                    xml = z.read(n).decode("utf-8", errors="replace")
                    morceaux.append(html.unescape(re.sub(r"<[^>]+>", " ", xml)))
        return "\n".join(morceaux)
    return None


def _motif_nom(nom: str) -> re.Pattern[str]:
    return re.compile(r"(?<![A-Za-z0-9])" + re.escape(nom) + r"(?![A-Za-z0-9])", re.IGNORECASE)


def analyser(dest: Path, interdits: list[str], adresses: list[str], rapport: Rapport) -> None:
    motifs = {f"nom interdit « {n} »": _motif_nom(n) for n in interdits}
    utilisateur = getpass.getuser()
    if len(utilisateur) >= 4:
        motifs["nom d'utilisateur de la machine"] = _motif_nom(utilisateur)
    motifs |= {f"adresse retirée « {a} »": re.compile(re.escape(a), re.IGNORECASE) for a in adresses}
    motifs |= {"chemin de la machine": re.compile(r"/(?:Users|home)/[A-Za-z0-9._-]+"),
               "dossier de projet de la machine": re.compile(r"-(?:Users|home)-[A-Za-z0-9._]+-")}
    motifs |= {f"secret ({k})": v for k, v in SECRETS.items()}
    for f in _fichiers(dest):
        rel = str(f.relative_to(dest))
        if f.stat().st_size > TAILLE_MAX:
            rapport.constats.append(Constat(rel, "fichier de plus de 10 Mo", f"{f.stat().st_size} octets"))
        if f.name == FICHIER_PRIVE or f.name == ".env" or f.name.startswith(".env."):
            rapport.constats.append(Constat(rel, "fichier privé dans la copie", f.name))
        texte = texte_de(f)
        if texte is None:
            rapport.non_lus.append(rel)
            texte = ""
        for motif, rx in motifs.items():
            for cible in (rel, texte):
                m = rx.search(cible)
                if m:
                    debut = max(0, m.start() - 40)
                    rapport.constats.append(Constat(rel, motif, cible[debut:m.end() + 40].replace("\n", " ")))
                    break


def licence_douteuse(texte: str) -> bool:
    """GPL ou AGPL : contaminantes pour un dépôt MIT. La LGPL et la MPL n'en font pas partie. Une licence au
    choix (« A OR B ») n'est douteuse que si chacune de ses branches l'est."""
    branches = re.split(r"\s+OR\s+", texte.strip("() "), flags=re.IGNORECASE)
    if len(branches) > 1:
        return all(licence_douteuse(b) for b in branches)
    t = texte.upper()
    if "AFFERO" in t or "AGPL" in t:
        return True
    if re.search(r"(?<!L)GPL", t):
        return True
    return "GENERAL PUBLIC LICENSE" in t and "LESSER" not in t and "LIBRARY" not in t


def licences() -> tuple[str, list[str]]:
    """La liste des paquets de l'environnement de l'outil, avec leur licence déclarée."""
    lignes, douteuses = [], []
    vus = set()
    for d in sorted(metadata.distributions(), key=lambda d: (d.metadata["Name"] or "").lower()):
        nom = d.metadata["Name"]
        if not nom or nom.lower() in vus:
            continue
        vus.add(nom.lower())
        expression = d.metadata.get("License-Expression") or ""
        declaree = d.metadata.get("License") or ""
        classes = [c.split(" :: ")[-1] for c in (d.metadata.get_all("Classifier") or []) if c.startswith("License ::")]
        if expression:
            lic = expression
        elif declaree and len(declaree) <= 60 and "\n" not in declaree:
            lic = declaree
        elif classes:
            lic = ", ".join(classes)
        else:
            lic = "non déclarée dans les métadonnées"
        if licence_douteuse(lic):
            douteuses.append(nom)
        lignes.append(f"| {nom} | {d.version} | {lic} |")
    entete = ("# Licences des dépendances\n\n"
              "Paquets installés par `uv sync --frozen` dans l'environnement de l'outil (outils de test compris), "
              "avec la licence que chacun déclare dans ses métadonnées. Liste écrite par `prepa-rdv depot`, "
              "qui refuse de publier si un paquet est sous GPL ou AGPL.\n\n"
              "| Paquet | Version | Licence déclarée |\n|---|---|---|\n")
    return entete + "\n".join(lignes) + "\n", douteuses


def auditer() -> dict[str, Any]:
    """`pip-audit` sur l'environnement de l'outil : les vulnérabilités connues des versions verrouillées."""
    try:
        r = subprocess.run([sys.executable, "-m", "pip_audit", "--progress-spinner", "off", "-f", "json"],
                           capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"ok": False, "erreur": str(e)}
    try:
        d = json.loads(r.stdout or "{}")
    except json.JSONDecodeError:
        return {"ok": False, "erreur": (r.stderr or r.stdout)[-400:]}
    vulnerables = {x["name"]: [v["id"] for v in x.get("vulns", [])] for x in d.get("dependencies", []) if x.get("vulns")}
    return {"ok": not vulnerables, "paquets": len(d.get("dependencies", [])), "vulnerables": vulnerables}


def _ordre(racine: Path) -> list[str] | None:
    chemin = racine / "outil" / "societes.csv"
    if not chemin.exists():
        return None
    lignes = chemin.read_text(encoding="utf-8").splitlines()
    return [x.strip() for x in lignes[1:] if x.strip()]


def construire(dest: Path, prive: Path | None = None, lien_outil: str = "", recomposer: bool = True,
               audit: bool = True, racine: Path | None = None) -> Rapport:
    racine = (racine or racine_du_cas()).resolve()
    prive = prive or racine / FICHIER_PRIVE
    regles = lire_prive(prive)
    vider(dest, racine)
    rapport = Rapport(dossier=dest.resolve())
    rapport.copies = copier(racine, dest)
    nettoyer_textes(dest, regles["remplacements"], rapport)
    rapport.adresses_retirees = caviarder_fiches(dest / "sorties")
    if recomposer:
        rapport.livrables, rapport.livrables_ok = recomposer_livrables(dest / "sorties", lien_outil, _ordre(racine))
    derniere_passe(dest, rapport.adresses_retirees, rapport)
    texte, rapport.licences_douteuses = licences()
    (dest / "LICENCES-TIERS.md").write_text(texte, encoding="utf-8")
    if audit:
        rapport.audit = auditer()
    analyser(dest, regles["interdits"], rapport.adresses_retirees, rapport)
    return rapport


def publier(dest: Path, message: str) -> str:
    """Commit et push de la copie. N'est appelé qu'après une analyse verte."""
    git = ["git", "-C", str(dest)]
    subprocess.run(git + ["add", "-A"], check=True)
    if subprocess.run(git + ["diff", "--cached", "--quiet"]).returncode == 0:
        return "Rien de neuf à publier."
    subprocess.run(git + ["commit", "-q", "-m", message], check=True)
    subprocess.run(git + ["push", "-q", "-u", "origin", "HEAD"], check=True)
    return subprocess.run(git + ["log", "-1", "--format=%h %s"], capture_output=True, text=True).stdout.strip()
