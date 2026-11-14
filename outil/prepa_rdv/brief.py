"""Le brief d'une page par société, en HTML puis en PDF par Chrome sans affichage.

Une page A4, 330 mots au plus, quatre blocs et un pied. Les contrôles de langue et le contrôle des nombres
(« chaque nombre du brief figure dans la fiche ») sont faits par le code avant le rendu.
"""
from __future__ import annotations

import html
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from pypdf import PdfReader

from . import affichage, contacts
from .listes import nom_court, norm, personne_courte
from .schema import CHAMPS_BRIEF, LIBELLES_CHAMP, Champ, Niveau

MAX_MOTS = 330
MAX_MOTS_PHRASE = 30

# Contrôles de langue : sous-ensemble de la charte éditoriale, cherché mécaniquement.
INTERDITS = (
    "meilleur", "le plus", "le mieux", "incontournable", "révolutionnaire", "puissant", "robuste", "incroyable", "exceptionnel",
    "parfait", "ultime", "leader", "expert", "véritable", "vraiment", "très", "extrêmement", "particulièrement", "absolument",
    "littéralement", "clairement", "évidemment", "exactement", "jamais", "toujours", "systématiquement", "transformer", "booster",
    "optimiser", "passer à l'échelle", "gagner en efficacité", "gain de productivité", "llm", "hallucination",
)

COULEURS = {
    Niveau.CONFIRME: ("#14532d", "#dcfce7"), Niveau.PROBABLE: ("#7c2d12", "#ffedd5"), Niveau.NON_TROUVE: ("#374151", "#e5e7eb"),
    Niveau.ABSENCE_DECLAREE: ("#1e3a8a", "#dbeafe"), Niveau.CONTRADICTION: ("#7f1d1d", "#fee2e2"),
}


def controle_langue(texte: str) -> list[str]:
    """Problèmes de langue dans un texte écrit par le code : cadratin, mots interdits, phrases de plus de 30 mots."""
    problemes = []
    if "—" in texte or "–" in texte:
        problemes.append("tiret cadratin ou demi-cadratin")
    bas = texte.casefold()
    for mot in INTERDITS:
        if re.search(rf"(?<![a-zà-ÿ]){re.escape(mot)}(?![a-zà-ÿ])", bas):
            problemes.append(f"mot interdit : {mot}")
    for phrase in re.split(r"(?<=[.!?])\s+|\n+", texte):  # un saut de ligne finit une phrase : cellules, puces
        if len(phrase.split()) > MAX_MOTS_PHRASE:
            problemes.append(f"phrase de {len(phrase.split())} mots : {phrase[:50]}...")
    return problemes


def _annee(t: dict) -> str:
    d = t["verifs"].get("date_retenue") or ""
    return d[:4] if d else "date non lue"


CHAMPS_AFFICHES = (*CHAMPS_BRIEF, Champ.SIGNAL)


def _sources(fiche: dict) -> tuple[list[dict], dict[str, int]]:
    """Sources citées dans le brief, numérotées dans l'ordre d'apparition des champs."""
    par_id = {t["id"]: t for t in fiche["trouvailles"]}
    ordre: list[dict] = []
    numero: dict[str, int] = {}
    for champ in CHAMPS_AFFICHES:
        for v in fiche["synthese"][champ.value]["valeurs"]:
            for i in v["ids"][:1]:
                t = par_id.get(i)
                if t and t["url"] not in numero:
                    numero[t["url"]] = len(ordre) + 1
                    ordre.append(t)
    return ordre, numero


def _poste_depuis_la_citation(nom: str, citation: str) -> str:
    """Poste d'une personne dont la valeur n'est que le nom : les mots qui suivent son nom de famille dans la citation."""
    mots = nom.split()
    if not mots:
        return ""
    m = re.search(rf"{re.escape(mots[-1])}\W*(?:est |is )?([^.;:]+)", citation, flags=re.I)
    poste = re.sub(r"^[\s,()–-]+", "", m.group(1)) if m else ""
    return " ".join(poste.split()[:9])


def _valeur_affichee(v: dict, champ: Champ | None = None, trouvaille: dict | None = None) -> str:
    """Valeur pour le brief : le nom seul (le commentaire du modèle reste dans les tableurs)."""
    if champ == Champ.DIRECTION_FINANCIERE:
        base = personne_courte(v["valeur"])
        if "," not in v["valeur"] and "(" not in v["valeur"] and trouvaille:  # nom sans titre : le poste vient de la citation
            poste = _poste_depuis_la_citation(v["valeur"], trouvaille["citation"])
            base = personne_courte(f"{v['valeur']}, {poste}") if poste else base
    elif champ == Champ.SIGNAL:
        base = v["valeur"]
    else:
        base = v["valeur"] if v["valeur"] != "autre" else nom_court(v["precision"] or "autre")
    return base + (" : absence déclarée" if v["statut"] == "absence_declaree" else "")


def signal_retenu(fiche: dict) -> dict:
    """Synthèse du signal pour le brief : le plus récent des signaux retenus, s'il passe le contrôle de langue.

    Le texte d'un signal est écrit par le modèle. Un signal qui ne passe pas le contrôle reste dans les tableurs, pas dans le brief.
    """
    par_id = {t["id"]: t for t in fiche["trouvailles"]}
    rang = {Niveau.CONFIRME.value: 3, Niveau.PROBABLE.value: 2}
    # Un signal est récent : la page doit tomber dans la fenêtre de son type. Une page datée de 2001 par ses métadonnées n'en est pas un.
    candidats = [v for v in fiche["synthese"][Champ.SIGNAL.value]["valeurs"]
                 if v["statut"] == "present" and v["niveau"] in rang and v["ids"] and v["ids"][0] in par_id
                 and par_id[v["ids"][0]]["verifs"].get("dans_fenetre")]
    candidats.sort(key=lambda v: (par_id[v["ids"][0]]["verifs"].get("date_retenue") or "", rang[v["niveau"]]), reverse=True)
    for v in candidats:
        if not controle_langue(_valeur_affichee(v, Champ.SIGNAL)):
            return {"niveau": v["niveau"], "contradiction": False, "valeurs": [v]}
    return {"niveau": Niveau.NON_TROUVE.value, "contradiction": False, "valeurs": []}


def composer(fiche: dict, contact: str | None = None) -> dict[str, Any]:
    """Contenu du brief sous forme structurée, avant tout rendu."""
    if contact is None:
        contact = contacts.ligne(fiche.get("contact"))
    par_id = {t["id"]: t for t in fiche["trouvailles"]}
    synthese = {**fiche["synthese"], Champ.SIGNAL.value: signal_retenu(fiche)}
    sources, numero = _sources({**fiche, "synthese": synthese})
    lignes = []
    for champ in CHAMPS_AFFICHES:
        s = synthese[champ.value]
        niveau = Niveau(s["niveau"])
        if champ == Champ.SIGNAL and niveau == Niveau.NON_TROUVE:
            continue  # pas de ligne vide pour un signal : il n'est pas attendu à chaque rendez-vous
        valeurs = []
        for v in s["valeurs"][:2 if champ == Champ.DIRECTION_FINANCIERE else 3]:
            t = par_id.get(v["ids"][0]) if v["ids"] else None
            ref = f" [{numero[t['url']]}]" if t and t["url"] in numero else ""
            marques = affichage.marques(t, fiche["entite"])
            if t and t["verifs"].get("mode_verification") == "seconde_lecture":
                marques += " (seconde lecture)"
            if champ == Champ.SIGNAL and t and _annee(t) != "date non lue" and _annee(t) not in _valeur_affichee(v, champ):
                marques += f" ({_annee(t)})"
            valeurs.append(_valeur_affichee(v, champ, t) + marques + ref)
        texte = "Non trouvé" if niveau == Niveau.NON_TROUVE else " ; ".join(valeurs)
        lignes.append({"champ": LIBELLES_CHAMP[champ], "valeur": texte, "niveau": niveau})
    e = fiche["entite"]
    entete = " · ".join(x for x in (e.get("pays"), e.get("statut"), f"fiche du {fiche['date_fiche']}",
                                    f"{fiche['nombre_sources']} source{'s' if fiche['nombre_sources'] > 1 else ''}") if x)
    return {
        "societe": fiche["societe"], "entete": entete, "lignes": lignes, "angle": fiche["angle"],
        "questions": fiche["questions"], "contact": contact,
        "sources": [{"n": numero[t["url"]], "domaine": urlparse(t["url"]).hostname.removeprefix("www.") if urlparse(t["url"]).hostname else t["url"],
                     "annee": _annee(t), "url": t["url"]} for t in sources],
    }


def texte_visible(c: dict) -> str:
    morceaux = [c["societe"], c["entete"], *[f"{l['champ']} {l['valeur']} {l['niveau'].value}" for l in c["lignes"]], *c["angle"], *c["questions"]]
    if c["contact"]:
        morceaux.append(c["contact"])
    morceaux += [f"[{s['n']}] {s['domaine']}, {s['annee']}" for s in c["sources"]]
    return "\n".join(morceaux)


def verifier_brief(c: dict, fiche: dict) -> list[str]:
    """Contrôles : langue, longueur, nombres."""
    problemes = [f"langue : {p}" for p in controle_langue("\n".join([*c["angle"], *c["questions"], *[l["valeur"] for l in c["lignes"]],
                                                                       *([c["contact"]] if c["contact"] else [])]))]
    mots = len(texte_visible(c).split())
    if mots > MAX_MOTS:
        problemes.append(f"{mots} mots, au plus {MAX_MOTS}")
    # Un nombre est un groupe de chiffres isolé : les chiffres collés à des lettres (empreintes, « S/4HANA ») n'en sont pas.
    # Seuls comptent les champs qui portent du contenu : ni durées, ni coûts, ni horodatages techniques.
    nombre = re.compile(r"(?<![A-Za-z0-9])\d+(?![A-Za-z0-9])")
    e = fiche["entite"]
    sources_du_contenu = [fiche["date_fiche"], str(fiche["nombre_sources"]), e.get("nom_retenu") or "", e.get("pays") or "", e.get("statut") or "",
                          contacts.ligne(fiche.get("contact")) or ""]
    for t in fiche["trouvailles"]:
        v = t["verifs"]
        sources_du_contenu += [t["valeur"], t.get("precision") or "", t["citation"], t.get("traduction_fr") or "", t.get("date_source") or "",
                               v.get("date_page") or "", v.get("date_retenue") or ""]
    connus = set(nombre.findall("\n".join(sources_du_contenu)))
    visible = re.sub(r"\[\d+\]", "", texte_visible(c))
    for n in sorted(set(nombre.findall(visible)) - connus):
        problemes.append(f"nombre absent de la fiche : {n}")
    return problemes


CSS = """
@page { size: A4; margin: 0; }
* { box-sizing: border-box; }
body { margin: 0; font-family: -apple-system, 'Helvetica Neue', Arial, sans-serif; color: #111827; }
.brief { width: 210mm; height: 297mm; padding: 15mm 16mm 12mm; page-break-after: always; overflow: hidden; font-size: %(taille)spt; line-height: 1.38; display: flex; flex-direction: column; }
.brief:last-child { page-break-after: auto; }
h1 { font-size: 21pt; margin: 0 0 1mm; }
.meta { margin: 0 0 5mm; color: #4b5563; font-size: 0.92em; border-bottom: 0.4mm solid #d1d5db; padding-bottom: 2.5mm; }
h2 { font-size: 11.5pt; margin: 5mm 0 1.8mm; text-transform: none; }
h2 .hyp { font-size: 0.75em; font-weight: 600; background: #fef3c7; color: #78350f; padding: 0.3mm 1.6mm; border-radius: 1mm; margin-left: 2mm; }
table { width: 100%%; border-collapse: collapse; }
td { padding: 1.8mm 2mm; border-bottom: 0.25mm solid #e5e7eb; vertical-align: top; }
td.champ { width: 33mm; font-weight: 600; }
td.niveau { width: 26mm; text-align: right; white-space: nowrap; }
.badge { display: inline-block; padding: 0.4mm 2mm; border-radius: 1mm; font-size: 0.85em; font-weight: 600; }
p { margin: 0 0 1.6mm; }
ol { margin: 0; padding-left: 5mm; } li { margin: 0 0 1.4mm; }
.contact { margin-top: 3mm; color: #374151; }
footer { margin-top: auto; border-top: 0.3mm solid #d1d5db; padding-top: 2mm; font-size: 0.82em; color: #4b5563; }
footer a { color: #1d4ed8; text-decoration: none; }
"""


def html_section(c: dict) -> str:
    e = html.escape
    lignes = "".join(
        f"<tr><td class='champ'>{e(l['champ'])}</td><td>{e(l['valeur'])}</td>"
        f"<td class='niveau'><span class='badge' style='color:{COULEURS[l['niveau']][0]};background:{COULEURS[l['niveau']][1]}'>{e(l['niveau'].value)}</span></td></tr>"
        for l in c["lignes"])
    angle = "".join(f"<p>{e(p)}</p>" for p in c["angle"])
    questions = "".join(f"<li>{e(q)}</li>" for q in c["questions"])
    contact = f"<p class='contact'>{e(c['contact'])}</p>" if c["contact"] else ""
    sources = " · ".join(f"[{s['n']}] <a href='{e(s['url'])}'>{e(s['domaine'])}</a>, {e(s['annee'])}" for s in c["sources"]) or "Aucune source retenue."
    return (f"<section class='brief'><h1>{e(c['societe'])}</h1><p class='meta'>{e(c['entete'])}</p>"
            f"<h2>Ce qu'on sait</h2><table>{lignes}</table>"
            f"<h2>L'angle pour CA|ES <span class='hyp'>hypothèse</span></h2>{angle}"
            f"<h2>Questions pour le rendez-vous</h2><ol>{questions}</ol>{contact}"
            f"<footer>Sources : {sources}. Adresses complètes dans le tableur.</footer></section>")


def html_document(contenus: list[dict], taille: float = 10.0) -> str:
    return ("<!doctype html><html lang='fr'><head><meta charset='utf-8'><title>Briefs</title><style>"
            + CSS % {"taille": taille} + "</style></head><body>" + "".join(html_section(c) for c in contenus) + "</body></html>")


def trouver_chrome() -> str | None:
    for c in (os.environ.get("CHROME_BIN"), "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              shutil.which("google-chrome"), shutil.which("chromium"), shutil.which("chromium-browser")):
        if c and Path(c).exists():
            return c
    return None


def rendre_pdf(html_texte: str, pdf: Path) -> int:
    """HTML en PDF par Chrome sans affichage. Renvoie le nombre de pages."""
    chrome = trouver_chrome()
    if chrome is None:
        raise RuntimeError("Chrome ou Chromium introuvable (variable CHROME_BIN)")
    pdf.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="prepa-rdv-pdf-") as d:
        src = Path(d) / "brief.html"
        src.write_text(html_texte, encoding="utf-8")
        subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--user-data-dir={d}/profil",
                        f"--print-to-pdf={pdf}", src.as_uri()], capture_output=True, timeout=120, check=True)
    return len(PdfReader(str(pdf)).pages)


def rendre_lot(contenus: list[dict], pdf: Path, tailles: tuple[float, ...] = (10.0, 9.5, 9.0, 8.5)) -> dict[str, Any]:
    """Un PDF pour tout le lot, une page par société. La police réduit tant qu'une page déborde."""
    for taille in tailles:
        pages = rendre_pdf(html_document(contenus, taille), pdf)
        if pages == len(contenus):
            return {"pages": pages, "taille_police": taille, "octets": pdf.stat().st_size, "ok": True}
    return {"pages": pages, "taille_police": tailles[-1], "octets": pdf.stat().st_size, "ok": False}
