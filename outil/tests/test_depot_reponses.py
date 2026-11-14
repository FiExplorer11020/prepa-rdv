from pathlib import Path

from prepa_rdv import depot

RACINE = Path(__file__).resolve().parents[2]


def test_reponses_dans_le_readme(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text(f"avant\n{depot.DEBUT_REPONSES}\nancien\n{depot.FIN_REPONSES}\napres\n", encoding="utf-8")
    assert depot.inserer_reponses(readme, RACINE / "sorties", depot._ordre(RACINE))
    texte = readme.read_text(encoding="utf-8")
    assert "ancien" not in texte and texte.startswith("avant") and texte.endswith("apres\n")
    assert texte.count("<details>") == 12
    assert "| ERP |" in texte and "](https://" in texte
    assert texte.index("<b>SSAB</b>") < texte.index("<b>Verallia</b>")
