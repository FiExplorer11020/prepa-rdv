"""La copie publique : liste blanche, nettoyage, retrait des adresses déduites, analyse."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from openpyxl import Workbook

from prepa_rdv import depot

# Les motifs des tests sont assemblés à l'exécution : la source des tests passe elle-même l'analyse.
MAISON = "/" + "Users" + "/alice"
CLE = "sk-" + "ant-" + "a1" * 15
NOM_TU = "Zorg" + "lub"


def _racine(tmp: Path) -> Path:
    r = tmp / "cas-pratique"
    for d in ("outil/prepa_rdv", "outil/.venv/lib", "outil/prepa_rdv/__pycache__", "sorties/livrables",
              "sorties/societes/acme", "sorties/journal", "sorties/cache/lectures", "depot"):
        (r / d).mkdir(parents=True, exist_ok=True)
    (r / "outil/prepa_rdv/depot.py").write_text("# module\n", encoding="utf-8")
    (r / "outil/prepa_rdv/__pycache__/x.pyc").write_bytes(b"\0")
    (r / "outil/.venv/lib/paquet.py").write_text("x = 1\n", encoding="utf-8")
    (r / "outil/.env").write_text("A=1\n", encoding="utf-8")
    (r / "outil/LICENSE").write_text("MIT License\n", encoding="utf-8")
    (r / "sorties/cache/lectures/page.txt").write_text("texte d'un tiers\n", encoding="utf-8")
    (r / "depot/README.md").write_text("# Dépôt\n", encoding="utf-8")
    (r / "depot/gitignore").write_text(".venv/\n", encoding="utf-8")
    (r / "cahier-des-charges-2026-11-13.md").write_text(f"Rien de {NOM_TU} ici.\n", encoding="utf-8")
    (r / "sorties/journal/decisions.md").write_text("ok\n", encoding="utf-8")
    fiche = {"societe": "Acme", "contact": {"generiques": ["ir@acme.example"], "mention": None,
             "suggestion": {"nom": "Jo Bloggs", "adresse": "jo.bloggs@acme.example", "motif": "prenom.nom",
                            "mention": "déduite, non vérifiée"}}}
    (r / "sorties/societes/acme/fiche.json").write_text(json.dumps(fiche), encoding="utf-8")
    (r / "sorties/societes/acme/demande.md").write_text(f"Écris dans {MAISON}/Docs/x/cas-pratique/sorties/societes/acme.\n",
                                                        encoding="utf-8")
    (r / "sorties/societes/acme/journal.jsonl").write_text('{"contact": "jo.bloggs@acme.example"}\n', encoding="utf-8")
    return r


def _prive(tmp: Path) -> Path:
    p = tmp / "prive.json"
    p.write_text(json.dumps({"interdits": [NOM_TU], "remplacements": [[f"Rien de {NOM_TU} ici.", "Rien ici."]]}),
                 encoding="utf-8")
    return p


def test_normaliser_les_chemins_de_la_machine():
    texte, n = depot.normaliser(f"lu dans {MAISON}/Documents/projet/cas-pratique/sorties/x.json et {MAISON}/.claude")
    assert texte == "lu dans <racine>/sorties/x.json et ~/.claude" and n == 2


def test_licence_au_choix_et_gpl():
    assert depot.licence_douteuse("GPL-3.0-only")
    assert depot.licence_douteuse("GNU Affero General Public License v3")
    assert not depot.licence_douteuse("LGPL-2.1-or-later")
    assert not depot.licence_douteuse("MPL-1.1 OR GPL-2.0-only OR LGPL-2.1-or-later")
    assert depot.licence_douteuse("GPL-2.0-only OR AGPL-3.0-only")
    assert not depot.licence_douteuse("MIT")


def test_copie_propre_et_nettoyee(tmp_path):
    r = _racine(tmp_path)
    dest = tmp_path / "public"
    rapport = depot.construire(dest, prive=_prive(tmp_path), recomposer=False, audit=False, racine=r)
    publies = {str(p.relative_to(dest)) for p in dest.rglob("*") if p.is_file()}
    assert "README.md" in publies and ".gitignore" in publies and "LICENSE" in publies
    assert "conception/cahier-des-charges-2026-11-13.md" in publies
    assert not any(".venv" in p or "__pycache__" in p or "cache/" in p or p.endswith(".env") for p in publies)
    assert (dest / "conception/cahier-des-charges-2026-11-13.md").read_text(encoding="utf-8") == "Rien ici.\n"
    assert "<racine>/sorties/societes/acme" in (dest / "sorties/societes/acme/demande.md").read_text(encoding="utf-8")
    fiche = json.loads((dest / "sorties/societes/acme/fiche.json").read_text(encoding="utf-8"))
    assert fiche["contact"]["suggestion"] is None and fiche["contact"]["generiques"] == ["ir@acme.example"]
    assert "jo.bloggs" not in (dest / "sorties/societes/acme/journal.jsonl").read_text(encoding="utf-8")
    assert rapport.adresses_retirees == ["jo.bloggs@acme.example"]
    assert [c for c in rapport.constats if "utilisateur" not in c.motif] == []


def test_l_analyse_trouve_les_fuites(tmp_path):
    dest = tmp_path / "copie"
    (dest / "sorties").mkdir(parents=True)
    (dest / "a.md").write_text(f"chez {NOM_TU}, clé {CLE}, fichier {MAISON}/x\n", encoding="utf-8")
    wb = Workbook()
    wb.active["A1"] = f"Note : {NOM_TU.upper()}"
    wb.save(dest / "t.xlsx")
    rapport = depot.Rapport(dossier=dest)
    depot.analyser(dest, [NOM_TU], ["jo.bloggs@acme.example"], rapport)
    motifs = {(c.fichier, c.motif.split(" «")[0].split(" (")[0]) for c in rapport.constats}
    assert ("a.md", "nom interdit") in motifs and ("a.md", "secret") in motifs
    assert ("a.md", "chemin de la machine") in motifs and ("t.xlsx", "nom interdit") in motifs
    assert not rapport.propre


def test_remplacement_inutilise_bloque(tmp_path):
    r = _racine(tmp_path)
    prive = tmp_path / "p.json"
    prive.write_text(json.dumps({"interdits": [], "remplacements": [["texte disparu", "x"]]}), encoding="utf-8")
    rapport = depot.construire(tmp_path / "public", prive=prive, recomposer=False, audit=False, racine=r)
    assert rapport.remplacements == {"texte disparu": 0} and not rapport.propre


def test_ne_vide_pas_un_dossier_etranger(tmp_path):
    r = _racine(tmp_path)
    autre = tmp_path / "autre"
    autre.mkdir()
    (autre / "important.txt").write_text("à garder", encoding="utf-8")
    with pytest.raises(ValueError):
        depot.vider(autre, r.resolve())
    with pytest.raises(ValueError):
        depot.vider(r / "sorties", r.resolve())
    assert (autre / "important.txt").exists()
