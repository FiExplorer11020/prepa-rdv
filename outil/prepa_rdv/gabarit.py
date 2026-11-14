"""Mise en page commune des PDF et des tableurs : bandeau, titre, intertitres, tableaux zébrés, pied de page numéroté (D23).

Le squelette vient de documents de travail fournis par Oscar le 14 novembre 2026 : la mise en page et la structure
seulement, sans leur contenu. Bandeau plein de 9 mm, titre en vert, intertitres et en-têtes de tableau en bleu-vert,
lignes zébrées, police Inter, mention et numéro de page en pied. Le bandeau porte le nom de l'outil.
"""
from __future__ import annotations

import re

BLEU_VERT = "#009597"
BLEU_VERT_CLAIR = "#e6f4f4"
FILET = "#cfe5e5"
VERT = "#006b45"
GRIS = "#5f6b68"
GRIS_PIED = "#777777"
POLICE = "Inter, 'Helvetica Neue', Arial, sans-serif"
MARQUE = "prepa-rdv"
PIED = "Informations publiques, citées et datées. Cas pratique, outil prepa-rdv."


def _chaine_css(texte: str) -> str:
    return '"' + texte.replace("\\", "\\\\").replace('"', '\\"') + '"'


def titre_court(titre: str) -> str:
    """Le titre du bandeau : ce qui précède le premier « : », ou la question jusqu'à son point d'interrogation."""
    return re.split(r" : |(?<=\?) ", titre, maxsplit=1)[0]


def css_page(titre: str) -> str:
    """La règle @page d'un document qui coule sur plusieurs pages : bandeau en tête, mention et numéro en pied."""
    bande = f"background: linear-gradient({BLEU_VERT} 0, {BLEU_VERT} 9mm, transparent 9mm);"
    pied = f"font: 400 6.5pt {POLICE}; color: {GRIS_PIED}; vertical-align: top; padding-top: 7mm;"
    return (
        "@page { size: A4; margin: 21mm 17mm 17mm;"
        f" @top-left-corner {{ content: ''; {bande} }}"
        f" @top-left {{ content: {_chaine_css(MARQUE)}; font: 700 9pt {POLICE}; color: #fff; vertical-align: top;"
        f" padding-top: 2.7mm; {bande} }}"
        f" @top-center {{ content: ''; {bande} }}"
        f" @top-right {{ content: {_chaine_css(titre_court(titre))}; font: 400 7.5pt {POLICE}; color: #fff; vertical-align: top;"
        f" padding-top: 3.1mm; text-align: right; {bande} }}"
        f" @top-right-corner {{ content: ''; {bande} }}"
        f" @bottom-left {{ content: {_chaine_css(PIED)}; {pied} }}"
        f" @bottom-right {{ content: counter(page); text-align: right; {pied} }} }}"
    )


CSS_TABLEAU = (
    f"table {{ border-collapse: collapse; width: 100%; border: 0.25mm solid {FILET}; }}"
    f"th {{ background: {BLEU_VERT}; color: #fff; font-weight: 700; text-align: left; }}"
    f"td {{ border-top: 0.25mm solid {FILET}; vertical-align: top; }}"
    f"tr:nth-child(odd) td {{ background: {BLEU_VERT_CLAIR}; }}"
)
