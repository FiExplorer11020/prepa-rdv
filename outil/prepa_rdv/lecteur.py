"""Lecture polie des pages publiques.

- identité annoncée dans l'en-tête, avec un moyen de contact ;
- robots.txt respecté (RFC 9309) ; un refus (robots, 401, 403) n'est pas contourné ;
- une pause entre deux requêtes vers le même hôte ;
- cache disque : une relecture ne refait aucun appel réseau ;
- HTML en texte par `trafilatura`, PDF en texte par `pdftotext` s'il est présent, sinon `pypdf`.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx
import trafilatura
from pypdf import PdfReader
from trafilatura.settings import set_date_params

from . import __version__
from .jetons import dossier_sorties

TEXTE_MINIMAL = 400  # en dessous, une page HTML est probablement une coquille JavaScript


@dataclass
class Page:
    url: str
    url_finale: str = ""
    statut: int | None = None
    type_contenu: str = ""
    texte: str = ""
    pages: list[str] = field(default_factory=list)  # PDF : texte par page
    date_page: str | None = None
    titre: str | None = None
    empreinte: str | None = None
    octets: int = 0
    depuis_cache: bool = False
    via: str = "direct"
    erreur: str | None = None

    @property
    def ok(self) -> bool:
        return self.erreur is None and self.statut is not None and 200 <= self.statut < 300 and bool(self.texte.strip())

    @property
    def domaine(self) -> str:
        return (urlparse(self.url_finale or self.url).hostname or "").lower()


def en_ascii(texte: str) -> str:
    """Les valeurs d'en-tête HTTP sont en ASCII : on retire les accents."""
    import unicodedata
    return unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode("ascii")


def domaine_de(url: str) -> str:
    return (urlparse(url).hostname or "").lower().removeprefix("www.")


def domaine_racine(hote: str) -> str:
    """Les deux derniers segments, ou trois pour un suffixe à deux niveaux (co.uk, com.au...)."""
    parts = hote.lower().removeprefix("www.").split(".")
    if len(parts) >= 3 and parts[-2] in ("co", "com", "org", "gov", "ac") and len(parts[-1]) == 2:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:]) if len(parts) >= 2 else hote


class Lecteur:
    def __init__(self, dossier_cache: Path | None = None, contact: str | None = None, pause_s: float = 1.0,
                 delai_s: float = 30.0, max_octets: int = 80_000_000, jina: bool = True):
        contact = contact or os.environ.get("PREPA_RDV_CONTACT") or "contact : voir le dépôt du projet"
        self.ua = en_ascii(f"prepa-rdv/{__version__} (outil d'étude, lecture de pages publiques ; {contact})")
        self.cache = Path(dossier_cache) if dossier_cache else dossier_sorties() / "cache" / "lectures"
        self.cache.mkdir(parents=True, exist_ok=True)
        self.pause_s = pause_s
        self.max_octets = max_octets
        self.jina = jina
        self.client = httpx.Client(
            headers={"User-Agent": self.ua, "Accept-Language": "en,fr;q=0.8,de;q=0.6,sv;q=0.4",
                     "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.9,*/*;q=0.5"},
            follow_redirects=True, timeout=delai_s)
        self._robots: dict[str, RobotFileParser | None] = {}
        self._dernier: dict[str, float] = {}

    # -- politesse -----------------------------------------------------------------------------

    def _attendre(self, hote: str, pause: float | None = None) -> None:
        pause = self.pause_s if pause is None else pause
        reste = self._dernier.get(hote, 0.0) + pause - time.monotonic()
        if reste > 0:
            time.sleep(reste)
        self._dernier[hote] = time.monotonic()

    def autorise(self, url: str) -> bool:
        u = urlparse(url)
        hote = f"{u.scheme}://{u.netloc}"
        if hote not in self._robots:
            rp: RobotFileParser | None = RobotFileParser()
            try:
                self._attendre(u.netloc)
                r = self.client.get(f"{hote}/robots.txt", timeout=10)
                if 200 <= r.status_code < 300:
                    rp.parse(r.text.splitlines())
                elif r.status_code >= 500:
                    rp.parse(["User-agent: *", "Disallow: /"])  # RFC 9309 : serveur en panne, on s'abstient
                else:
                    rp = None  # 4xx : pas de règles publiées
            except httpx.HTTPError:
                rp = None
            self._robots[hote] = rp
        rp = self._robots[hote]
        return True if rp is None else rp.can_fetch(self.ua, url) or rp.can_fetch("*", url)

    # -- cache ---------------------------------------------------------------------------------

    def _chemin(self, url: str) -> Path:
        return self.cache / (hashlib.sha256(url.encode()).hexdigest()[:24] + ".json")

    def _lire_cache(self, url: str) -> Page | None:
        c = self._chemin(url)
        if not c.exists():
            return None
        p = Page(**json.loads(c.read_text(encoding="utf-8")))
        p.depuis_cache = True
        return p

    def _ecrire_cache(self, page: Page) -> None:
        self._chemin(page.url).write_text(json.dumps(asdict(page), ensure_ascii=False), encoding="utf-8")

    # -- lecture -------------------------------------------------------------------------------

    def lire(self, url: str, forcer: bool = False) -> Page:
        if not forcer and (cache := self._lire_cache(url)) is not None:
            return cache
        page = self._lire_reseau(url)
        if page.statut is not None:  # une erreur réseau n'entre pas au cache : on la retente plus tard
            self._ecrire_cache(page)
        return page

    def lire_rendu(self, url: str) -> Page | None:
        """La même page rendue par JavaScript (Jina Reader), quand la lecture directe est lisible mais pauvre et que la citation manque.

        Jamais après un refus : cette page a déjà répondu au code, il ne manque que le contenu que le navigateur construit.
        Rend None si le rendu n'ajoute rien ou n'est pas disponible. Le résultat entre au cache sous une clé à part.
        """
        cle = self._chemin(url + "#rendu")
        if cle.exists():
            rendu = Page(**json.loads(cle.read_text(encoding="utf-8")))
            rendu.depuis_cache = True
            return rendu if rendu.via == "jina" else None
        base = self.lire(url)
        if not self.jina or not base.ok or base.pages or "html" not in base.type_contenu:
            return None
        rendu = Page(url=url, url_finale=base.url_finale, statut=base.statut, type_contenu=base.type_contenu, titre=base.titre,
                     date_page=base.date_page, octets=base.octets)
        self._secours_jina(url, rendu)
        if rendu.via != "jina":
            rendu = Page(url=url, via="direct")  # trace d'un rendu sans apport : on ne le redemande pas
        else:
            rendu.empreinte = hashlib.sha256(rendu.texte.encode("utf-8")).hexdigest()
        cle.write_text(json.dumps(asdict(rendu), ensure_ascii=False), encoding="utf-8")
        return rendu if rendu.via == "jina" else None

    def _lire_reseau(self, url: str) -> Page:
        page = Page(url=url)
        if urlparse(url).scheme not in ("http", "https"):
            page.erreur = "adresse non web"
            return page
        if not self.autorise(url):
            page.erreur = "refusé par robots.txt"
            return page
        try:
            self._attendre(urlparse(url).netloc)
            r = self.client.get(url)
        except httpx.HTTPError as e:
            page.erreur = f"réseau : {type(e).__name__}"
            return page
        page.statut, page.url_finale = r.status_code, str(r.url)
        page.type_contenu = r.headers.get("content-type", "").split(";")[0].strip().lower()
        if r.status_code in (401, 403, 429) or r.status_code >= 400:
            page.erreur = f"HTTP {r.status_code}"
            return page
        contenu = r.content
        page.octets = len(contenu)
        if page.octets > self.max_octets:
            page.erreur = "document trop gros"
            return page
        if page.type_contenu == "application/pdf" or contenu[:5] == b"%PDF-":
            self._lire_pdf(contenu, page)
        else:
            self._lire_html(r.text, page)
            if self.jina and len(page.texte) < TEXTE_MINIMAL:
                self._secours_jina(url, page)
        page.empreinte = hashlib.sha256(page.texte.encode("utf-8")).hexdigest() if page.texte else None
        return page

    @staticmethod
    def _lire_html(html: str, page: Page) -> None:
        texte = trafilatura.extract(html, include_tables=True, include_comments=False, favor_recall=True) or ""
        # Date de première publication, pas de dernière modification : une page retouchée ne se rafraîchit pas.
        reglage = set_date_params(extensive=True)
        reglage["original_date"] = True
        meta = trafilatura.extract_metadata(html, date_config=reglage)
        if meta is not None:
            page.titre = meta.title
            page.date_page = meta.date
        page.texte = texte.strip()

    def _lire_pdf(self, contenu: bytes, page: Page) -> None:
        try:
            lecteur = PdfReader(io.BytesIO(contenu))
            meta = lecteur.metadata
            if meta is not None:
                page.titre = meta.title
                cree = meta.creation_date
                page.date_page = cree.date().isoformat() if cree else None
        except Exception:  # noqa: BLE001 : un PDF abîmé reste lisible par pdftotext
            lecteur = None
        pages: list[str] = []
        if shutil.which("pdftotext"):
            with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
                f.write(contenu)
                f.flush()
                p = subprocess.run(["pdftotext", "-layout", f.name, "-"], capture_output=True, timeout=300)
            if p.returncode == 0:
                pages = p.stdout.decode("utf-8", "replace").split("\f")
                if pages and not pages[-1].strip():
                    pages.pop()
        if not pages and lecteur is not None:
            for pg in lecteur.pages:
                try:
                    pages.append(pg.extract_text() or "")
                except Exception:  # noqa: BLE001
                    pages.append("")
        page.pages = pages
        page.texte = "\n\f".join(pages).strip()

    def _secours_jina(self, url: str, page: Page) -> None:
        """Page vide parce que rendue par JavaScript : Jina Reader la rend (20 requêtes par minute sans clé).

        Jamais après un refus : un 403 ou robots.txt ne se contourne pas.
        """
        try:
            self._attendre("r.jina.ai", 3.2)
            r = self.client.get(f"https://r.jina.ai/{url}", headers={"Accept": "text/plain"}, timeout=60)
        except httpx.HTTPError:
            return
        if r.status_code == 200 and len(r.text.strip()) > len(page.texte):
            page.texte, page.via = r.text.strip(), "jina"


# -- fenêtres autour des mots-clés (chemin B) ----------------------------------------------------

@dataclass
class Fenetre:
    page: int | None
    debut: int
    texte: str
    mots: list[str]


def fenetres(pages: list[str], mots_cles: tuple[str, ...], largeur: int = 450, maximum: int = 14) -> list[Fenetre]:
    """Passages d'un document autour de mots-clés, les plus riches en premier. Sert à ne pas lire 300 pages."""
    motifs = [(m, re.compile(rf"(?<![A-Za-zÀ-ÿ0-9]){re.escape(m)}(?![A-Za-zÀ-ÿ0-9])", re.I)) for m in mots_cles]
    trouvees: list[Fenetre] = []
    for numero, texte in enumerate(pages, start=1):
        if not texte.strip():
            continue
        brutes: list[tuple[int, int, set[str]]] = []
        for mot, motif in motifs:
            for m in motif.finditer(texte):
                brutes.append((max(0, m.start() - largeur), min(len(texte), m.end() + largeur), {mot}))
        brutes.sort()
        fusion: list[list] = []
        for d, f, mots in brutes:
            if fusion and d <= fusion[-1][1]:
                fusion[-1][1] = max(fusion[-1][1], f)
                fusion[-1][2] |= mots
            else:
                fusion.append([d, f, set(mots)])
        for d, f, mots in fusion:
            trouvees.append(Fenetre(numero, d, re.sub(r"[ \t]+", " ", texte[d:f]).strip(), sorted(mots)))
    trouvees.sort(key=lambda w: (-len(w.mots), w.page or 0))
    return trouvees[:maximum]
