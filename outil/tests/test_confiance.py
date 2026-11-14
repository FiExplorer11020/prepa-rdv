"""Les cas de la table de confiance (cahier des charges, section 6.4). Date de référence : 13 novembre 2026."""
from datetime import date, datetime, timezone

import pytest

from prepa_rdv.confiance import fenetre_mois, mois_entre, niveau_trouvaille, parse_date, synthese_champ
from prepa_rdv.schema import Champ, Niveau, StatutValeur, TypeSource, Trouvaille, Verifs

AUJOURDHUI = date(2026, 11, 13)
LECTURE = datetime(2026, 11, 13, 12, 0, tzinfo=timezone.utc)


def verifs(**kw) -> Verifs:
    base = dict(citation_trouvee=True, citation_longueur_ok=True, adresse_ok=True, entite="groupe",
                date_page="2026-06-30")
    base.update(kw)
    return Verifs(**base)


def niveau(v: Verifs, type_source=TypeSource.P2, statut=StatutValeur.PRESENT, champ=Champ.ERP, par_champ=False) -> Niveau:
    return niveau_trouvaille(v, type_source, statut, champ, LECTURE, AUJOURDHUI, par_champ)


# --- Dates ---------------------------------------------------------------------------------

@pytest.mark.parametrize("texte, attendu", [
    ("2024", date(2024, 12, 31)),
    ("2024-02", date(2024, 2, 29)),
    ("2026-06-30", date(2026, 6, 30)),
    ("30/06/2026", date(2026, 6, 30)),
    ("30.06.2026", date(2026, 6, 30)),
    ("2026-06-30T10:00:00Z", date(2026, 6, 30)),
    ("March 13, 2019", date(2019, 3, 13)),
    ("15 septembre 2026", date(2026, 9, 15)),
    ("Date: 15 September 2026", date(2026, 9, 15)),
    ("1er mars 2026", date(2026, 3, 1)),
    ("Mai 2025", date(2025, 5, 31)),
    ("12. Dezember 2024", date(2024, 12, 12)),
    ("hier", None),
    ("2026-13", None),
    (None, None),
])
def test_parse_date(texte, attendu):
    assert parse_date(texte) == attendu


def test_mois_entre():
    assert mois_entre(date(2024, 11, 13), AUJOURDHUI) == 24
    assert mois_entre(date(2024, 11, 14), AUJOURDHUI) == 23
    assert mois_entre(date(2022, 2, 15), AUJOURDHUI) == 56


# --- Table de confiance ----------------------------------------------------------------------

def test_p2_dans_la_fenetre_est_confirme():  # Nokia, page de SAP du 30 juin 2026
    assert niveau(verifs()) == Niveau.CONFIRME


def test_p1_dans_la_fenetre_est_confirme():
    assert niveau(verifs(date_page="2025-03-01"), TypeSource.P1) == Niveau.CONFIRME


def test_p1_juste_dans_la_fenetre_de_24_mois():
    assert niveau(verifs(date_page="2024-11-13"), TypeSource.P1) == Niveau.CONFIRME


def test_p1_hors_fenetre_est_probable():  # guide Ariba de Nokia, juillet 2024 : 28 mois
    assert niveau(verifs(date_page="2024-07-15"), TypeSource.P1) == Niveau.PROBABLE


def test_p2_hors_fenetre_est_probable():  # communiqué Kyriba de Barilla, février 2022 : 57 mois
    assert niveau(verifs(date_page="2022-02-15")) == Niveau.PROBABLE


def test_p1_sans_date_prend_la_date_de_lecture():
    v = verifs(date_page=None)
    assert niveau(v, TypeSource.P1) == Niveau.CONFIRME
    assert v.date_retenue == "2026-11-13"


def test_p2_sans_date_est_plafonne_a_probable():  # étude de cas MuleSoft sur Saint-Gobain
    v = verifs(date_page=None)
    assert niveau(v) == Niveau.PROBABLE
    assert v.sans_date is True


def test_la_date_de_la_page_prime_sur_celle_du_modele():
    v = verifs(date_page="2022-01-01", date_retenue="2026-01-01")
    assert niveau(v) == Niveau.PROBABLE


def test_date_partielle_est_la_fin_de_la_periode():
    assert niveau(verifs(date_page="2024"), TypeSource.P1) == Niveau.CONFIRME


@pytest.mark.parametrize("type_source", [TypeSource.P3, TypeSource.P4, TypeSource.P5])
def test_p3_p4_p5_au_mieux_probable(type_source):
    assert niveau(verifs(), type_source) == Niveau.PROBABLE


def test_citation_introuvable_est_rejetee():
    assert niveau(verifs(citation_trouvee=False)) == Niveau.NON_TROUVE


def test_citation_trop_longue_est_rejetee():
    assert niveau(verifs(citation_longueur_ok=False)) == Niveau.NON_TROUVE


def test_adresse_qui_ne_repond_pas_est_rejetee():
    assert niveau(verifs(adresse_ok=False)) == Niveau.NON_TROUVE


def test_entite_absente_est_rejetee():
    assert niveau(verifs(entite="absente")) == Niveau.NON_TROUVE


def test_filiale_plafonne_a_probable():
    assert niveau(verifs(entite="filiale")) == Niveau.PROBABLE


def test_absence_declaree_dans_la_fenetre():
    assert niveau(verifs(), TypeSource.P1, StatutValeur.ABSENCE_DECLAREE) == Niveau.ABSENCE_DECLAREE


def test_absence_declaree_hors_fenetre_est_probable():
    v = verifs(date_page="2019-01-01")
    assert niveau(v, TypeSource.P1, StatutValeur.ABSENCE_DECLAREE) == Niveau.PROBABLE


def test_fenetres_par_champ_allongent_la_pile():
    v = lambda: verifs(date_page="2022-08-01")  # 51 mois
    assert niveau(v(), TypeSource.P2) == Niveau.PROBABLE
    assert niveau(v(), TypeSource.P2, par_champ=True) == Niveau.CONFIRME


def test_fenetres_par_champ_raccourcissent_la_direction_financiere():
    v = lambda: verifs(date_page="2025-05-01")  # 18 mois
    assert niveau(v(), TypeSource.P1, champ=Champ.DIRECTION_FINANCIERE) == Niveau.CONFIRME
    assert niveau(v(), TypeSource.P1, champ=Champ.DIRECTION_FINANCIERE, par_champ=True) == Niveau.PROBABLE


def test_p5_n_a_pas_de_fenetre():
    assert fenetre_mois(TypeSource.P5, Champ.ERP) is None


# --- Synthèse d'un champ ---------------------------------------------------------------------

def trouvaille(champ, valeur, niv, statut=StatutValeur.PRESENT, precision=None, id="t", type_source=TypeSource.P2):
    from prepa_rdv.listes import normaliser_valeur
    norm_val = normaliser_valeur(champ, valeur, precision)[0] if champ != Champ.DIRECTION_FINANCIERE else valeur
    return Trouvaille(
        champ=champ, valeur=valeur, precision=precision, statut_valeur=statut, citation="x", citation_langue="en",
        traduction_fr=None, url="https://exemple.test/p", entite_nommee="Test", type_source=type_source, date_source=None,
        id=id, societe="Test", valeur_normalisee=norm_val, date_lecture=LECTURE, modele="m", version_outil="0",
        empreinte_prompt="p", niveau=niv)


def test_champ_sans_trouvaille_est_non_trouve():
    assert synthese_champ(Champ.ERP, []).niveau == Niveau.NON_TROUVE


def test_une_base_de_donnees_seule_ne_fait_pas_le_champ():
    """P5, second avis seulement. Cas Barilla : l'ERP n'est nommé que par une base de technologies."""
    s = synthese_champ(Champ.ERP, [trouvaille(Champ.ERP, "SAP S/4HANA", Niveau.PROBABLE, type_source=TypeSource.P5)])
    assert s.niveau == Niveau.NON_TROUVE and not s.valeurs


def test_une_base_de_donnees_appuie_une_autre_source():
    s = synthese_champ(Champ.ERP, [
        trouvaille(Champ.ERP, "SAP S/4HANA", Niveau.PROBABLE, type_source=TypeSource.P5, id="a"),
        trouvaille(Champ.ERP, "SAP S/4HANA", Niveau.PROBABLE, type_source=TypeSource.P3, id="b"),
    ])
    assert s.niveau == Niveau.PROBABLE and s.valeurs[0].ids == ["a", "b"]


def test_champ_ignore_les_trouvailles_rejetees():
    s = synthese_champ(Champ.ERP, [trouvaille(Champ.ERP, "SAP S/4HANA", Niveau.NON_TROUVE)])
    assert s.niveau == Niveau.NON_TROUVE


def test_plusieurs_produits_ne_se_contredisent_pas():
    s = synthese_champ(Champ.ERP, [
        trouvaille(Champ.ERP, "SAP S/4HANA", Niveau.CONFIRME, id="a"),
        trouvaille(Champ.ERP, "Oracle Fusion", Niveau.PROBABLE, id="b"),
    ])
    assert s.niveau == Niveau.CONFIRME and not s.contradiction
    assert [v.valeur for v in s.valeurs] == ["SAP S/4HANA", "Oracle Fusion"]


def test_deux_personnes_au_meme_niveau_se_contredisent():
    s = synthese_champ(Champ.DIRECTION_FINANCIERE, [
        trouvaille(Champ.DIRECTION_FINANCIERE, "Jeanne Martin, directrice financière", Niveau.CONFIRME, id="a"),
        trouvaille(Champ.DIRECTION_FINANCIERE, "Paul Durand, directeur financier", Niveau.CONFIRME, id="b"),
    ])
    assert s.niveau == Niveau.CONTRADICTION and s.contradiction
    assert len(s.valeurs) == 2


def test_la_personne_la_mieux_prouvee_l_emporte():
    s = synthese_champ(Champ.DIRECTION_FINANCIERE, [
        trouvaille(Champ.DIRECTION_FINANCIERE, "Jeanne Martin, directrice financière", Niveau.CONFIRME, id="a"),
        trouvaille(Champ.DIRECTION_FINANCIERE, "Paul Durand, directeur financier", Niveau.PROBABLE, id="b"),
    ])
    assert s.niveau == Niveau.CONFIRME and not s.contradiction
    assert s.valeurs[0].valeur.startswith("Jeanne")


def test_presence_et_absence_du_meme_produit_se_contredisent():
    s = synthese_champ(Champ.FINANCEMENT, [
        trouvaille(Champ.FINANCEMENT, "reverse factoring", Niveau.CONFIRME, id="a"),
        trouvaille(Champ.FINANCEMENT, "reverse factoring", Niveau.CONFIRME, StatutValeur.ABSENCE_DECLAREE, id="b"),
    ])
    assert s.niveau == Niveau.CONTRADICTION


def test_valeur_autre_garde_sa_precision():
    s = synthese_champ(Champ.ERP, [trouvaille(Champ.ERP, "Maison X", Niveau.PROBABLE, precision="Maison X 12")])
    assert s.valeurs[0].valeur == "autre" and s.valeurs[0].precision == "Maison X 12"


def test_le_directeur_financier_et_son_adjoint_ne_se_contredisent_pas():
    s = synthese_champ(Champ.DIRECTION_FINANCIERE, [
        trouvaille(Champ.DIRECTION_FINANCIERE, "Maud Thuaudet, Chief Financial Officer", Niveau.PROBABLE, id="a"),
        trouvaille(Champ.DIRECTION_FINANCIERE, "Daniel Biarneix, Deputy Chief Financial Officer", Niveau.PROBABLE, id="b"),
    ])
    assert s.niveau == Niveau.PROBABLE and not s.contradiction
    assert [v.role for v in s.valeurs] == ["directeur", "adjoint"]  # le directeur d'abord


def test_un_adjoint_en_charge_de_la_tresorerie_est_le_responsable_de_la_tresorerie():
    from prepa_rdv.confiance import role_dirigeant
    t = trouvaille(Champ.DIRECTION_FINANCIERE, "Daniel Biarneix, Deputy Chief Financial Officer", Niveau.PROBABLE)
    t.citation = "in charge of treasury and financing, relations with rating agencies and insurance"
    assert role_dirigeant(t) == "tresorerie"
    assert role_dirigeant(trouvaille(Champ.DIRECTION_FINANCIERE, "Jan Berg, Group Treasurer", Niveau.PROBABLE)) == "tresorerie"
    assert role_dirigeant(trouvaille(Champ.DIRECTION_FINANCIERE, "Jan Berg, Finanzvorstand", Niveau.PROBABLE)) == "directeur"


def test_plusieurs_personnes_de_la_tresorerie_ne_se_contredisent_pas():
    """Cas Nokia : le responsable du cash management et le trésorier du groupe tiennent deux postes. Seul le directeur financier est unique."""
    s = synthese_champ(Champ.DIRECTION_FINANCIERE, [
        trouvaille(Champ.DIRECTION_FINANCIERE, "Jan Berg, Group Treasurer", Niveau.CONFIRME, id="a"),
        trouvaille(Champ.DIRECTION_FINANCIERE, "Lise Moen, Head of Cash Management", Niveau.CONFIRME, id="b"),
    ])
    assert not s.contradiction and [v.role for v in s.valeurs] == ["tresorerie", "tresorerie"]


def test_le_poste_se_lit_dans_la_citation_quand_la_valeur_n_est_que_le_nom():
    from prepa_rdv.confiance import role_dirigeant
    cfo = trouvaille(Champ.DIRECTION_FINANCIERE, "Gerald Mayer", Niveau.CONFIRME)
    cfo.citation = "Mag. Gerald Mayer Chief Financial Officer (CFO)"
    assert role_dirigeant(cfo) == "directeur"
    tresorier = trouvaille(Champ.DIRECTION_FINANCIERE, "Cédric DONDAIN", Niveau.PROBABLE)
    tresorier.citation = "Cédric DONDAIN, trésorier international en charge de la gestion de crédit du groupe Servier"
    assert role_dirigeant(tresorier) == "tresorerie"
    evp = trouvaille(Champ.DIRECTION_FINANCIERE, "Pascal Lemaire", Niveau.CONFIRME)
    evp.citation = "Pascal Lemaire Executive Vice President Finance"
    assert role_dirigeant(evp) == "autre"  # un poste de la finance qui n'est pas celui du directeur financier : jamais en contradiction avec lui


def test_deux_directeurs_financiers_au_meme_niveau_se_contredisent_toujours():
    s = synthese_champ(Champ.DIRECTION_FINANCIERE, [
        trouvaille(Champ.DIRECTION_FINANCIERE, "Jeanne Martin, CFO", Niveau.CONFIRME, id="a"),
        trouvaille(Champ.DIRECTION_FINANCIERE, "Paul Durand, directeur financier", Niveau.CONFIRME, id="b"),
        trouvaille(Champ.DIRECTION_FINANCIERE, "Eva Roth, Senior Vice President Finance", Niveau.CONFIRME, id="c"),
    ])
    assert s.contradiction and s.niveau == Niveau.CONTRADICTION


def test_un_directeur_financier_designe_ne_contredit_pas_le_sortant():
    s = synthese_champ(Champ.DIRECTION_FINANCIERE, [
        trouvaille(Champ.DIRECTION_FINANCIERE, "Christian P. Illek, directeur financier", Niveau.CONFIRME, id="a"),
        trouvaille(Champ.DIRECTION_FINANCIERE, "Dhananjay Mirchandani, directeur financier désigné (CFO)", Niveau.CONFIRME, id="b"),
    ])
    assert s.niveau == Niveau.CONFIRME and not s.contradiction
    assert [v.role for v in s.valeurs] == ["directeur", "designe"]
