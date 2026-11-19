"""Test su scadenzario, accantonamento e rendimento del conto deposito."""

import pytest

from taxcash import Profilo, Scenario, simula
from taxcash.deposito import (
    interessi_periodo,
    miglior_prodotto,
    rendimento_netto_annuo,
    tasso_pareggio,
)

PROF_GS = Profilo(regime="forfettario", gestione="separata", coefficiente=0.78, startup=True)


def test_deposito_formule_base():
    # 10.000 euro al 4% per 12 mesi: 400 lordi, 104 di imposta, 20 di bollo -> 276 netti
    i = interessi_periodo(10_000, 12, 0.04)
    assert i.lordi == pytest.approx(400)
    assert i.imposta == pytest.approx(104)
    assert i.bollo == pytest.approx(20)
    assert i.netti == pytest.approx(276)
    assert rendimento_netto_annuo(0.04) == pytest.approx(0.0276)
    assert tasso_pareggio() == pytest.approx(0.002 / 0.74)


def test_miglior_prodotto_rispetta_il_vincolo():
    prodotti = {0: 0.025, 12: 0.04, 24: 0.0475}
    assert miglior_prodotto(prodotti, 5) == (0, 0.025)
    assert miglior_prodotto(prodotti, 12) == (12, 0.04)
    assert miglior_prodotto(prodotti, 30) == (24, 0.0475)


def test_primo_anno_nessun_versamento_di_imposte():
    r = simula(PROF_GS, Scenario(anno_inizio=2027, anni=3, ricavi_annui_regime=30_000))
    primo_anno = [pg for pg in r.pagamenti if pg.anno == 2027]
    assert primo_anno == []  # Gestione Separata: niente rate fisse, niente acconti


def test_doppio_carico_nel_secondo_anno():
    r = simula(PROF_GS, Scenario(anno_inizio=2027, anni=3, ricavi_annui_regime=30_000))
    giugno = {(pg.categoria): 0.0 for pg in r.pagamenti}
    for pg in r.pagamenti:
        if pg.periodo == "2028-06":
            giugno[pg.categoria] += pg.importo
    # imposta: saldo anno 1 (864,98) + 1° acconto anno 2 (432,49)
    assert giugno["imposta"] == pytest.approx(864.98 + 432.49, abs=0.02)
    # INPS: saldo anno 1 (6.100,38) + 1° acconto (40% x 6.100,38 = 2.440,15)
    assert giugno["inps"] == pytest.approx(6_100.38 + 2_440.15, abs=0.02)


def test_versamenti_totali_uguali_al_carico_degli_anni_simulati():
    r = simula(PROF_GS, Scenario(anni=3, ricavi_annui_regime=30_000))
    carico = sum(e.carico_totale for e in r.esiti)
    assert r.kpi["versamenti_nell_orizzonte"] == pytest.approx(carico, abs=0.05)
    assert r.kpi["carico_totale"] == pytest.approx(20_896.08, abs=0.05)


def test_riserva_fine_primo_anno_uguale_al_carico_del_primo_anno():
    r = simula(PROF_GS, Scenario(anni=3, ricavi_annui_regime=30_000))
    assert r.kpi["riserva_fine_primo_anno"] == pytest.approx(r.esiti[0].carico_totale, abs=0.05)


def test_accantonamento_automatico_non_genera_scoperti():
    for prof in (
        PROF_GS,
        Profilo(regime="forfettario", gestione="commercianti", coefficiente=0.40),
        Profilo(regime="ordinario", gestione="commercianti", costi_pct=0.2),
    ):
        r = simula(prof, Scenario(anni=4, ricavi_annui_regime=40_000, crescita_annua=0.1))
        assert r.kpi["scoperto_totale"] == pytest.approx(0, abs=0.01), prof
        assert r.timeline["riserva"].min() > -0.01


def test_accantonamento_troppo_basso_segnala_scoperto():
    r = simula(PROF_GS, Scenario(anni=3, ricavi_annui_regime=30_000, accantonamento_pct=0.05))
    assert r.kpi["scoperto_totale"] > 0
    assert any("insufficiente" in a for a in r.avvisi)


def test_commerciante_paga_rate_fisse_gia_nel_primo_anno():
    prof = Profilo(regime="forfettario", gestione="commercianti", coefficiente=0.40)
    r = simula(prof, Scenario(anno_inizio=2027, anni=2, ricavi_annui_regime=30_000))
    rate = [pg for pg in r.pagamenti if pg.voce.startswith("Rata fissa") and "anno 1" in pg.voce]
    assert [pg.periodo for pg in rate] == ["2027-05", "2027-08", "2027-11", "2028-02"]
    assert sum(pg.importo for pg in rate) == pytest.approx(4_611.64, abs=0.01)


def test_avvio_a_meta_anno_riduce_rate_e_ricavi():
    prof = Profilo(regime="forfettario", gestione="commercianti", coefficiente=0.40)
    r = simula(prof, Scenario(anno_inizio=2027, mese_inizio=7, anni=2, ricavi_annui_regime=24_000))
    assert r.esiti[0].ricavi == pytest.approx(12_000)       # 6 mesi su 12
    rate = [pg.periodo for pg in r.pagamenti if pg.voce.startswith("Rata fissa") and "anno 1" in pg.voce]
    assert rate == ["2027-08", "2027-11", "2028-02"]


def test_conservazione_importi_tra_accantonamenti_e_versamenti():
    r = simula(PROF_GS, Scenario(anni=3, ricavi_annui_regime=30_000, crescita_annua=0.05))
    accantonato = r.timeline["accantonato"].sum()
    versato = r.kpi["versamenti_nell_orizzonte"]
    residuo = r.timeline["riserva"].iloc[-1]
    assert accantonato - versato == pytest.approx(residuo, abs=0.01)
    assert r.allocazioni["importo"].sum() == pytest.approx(accantonato, abs=0.01)


def test_beneficio_positivo_con_tassi_di_mercato_e_nullo_a_tasso_zero():
    r = simula(PROF_GS, Scenario(anni=3, ricavi_annui_regime=30_000))
    assert r.kpi["beneficio_vs_conto_corrente"] > 0
    assert r.kpi["interessi_netti"] == pytest.approx(
        r.kpi["interessi_lordi"] - r.kpi["imposta_sugli_interessi"] - r.kpi["bollo_deposito"]
    )
    zero = simula(PROF_GS, Scenario(anni=3, ricavi_annui_regime=30_000, prodotti={0: 0.0}))
    assert zero.kpi["interessi_lordi"] == 0
    assert zero.kpi["beneficio_vs_conto_corrente"] < 0   # solo bollo: il deposito a tasso zero costa


def test_ricavi_in_calo_non_producono_versamenti_negativi():
    r = simula(PROF_GS, Scenario(anni=4, ricavi_annui_regime=40_000, crescita_annua=-0.4))
    assert all(pg.importo > 0 for pg in r.pagamenti)


def test_caso_minimo_calcolato_a_mano():
    """Un solo mese di incassi (dicembre 2027), un solo versamento (giugno 2028).

    ricavi 1.000 -> reddito 780 -> INPS 26,07% = 203,35 -> imponibile 576,65 -> imposta 5% = 28,83
    carico 232,18 versato a giugno 2028 (6 mesi dopo), prodotto libero al 2,5%:
    lordi 232,18 x 2,5% x 6/12 = 2,90 ; imposta 26% = 0,75 ; bollo 0,20% x 232,18 x 6/12 = 0,23 ; netti 1,92
    """
    r = simula(
        PROF_GS,
        Scenario(anno_inizio=2027, mese_inizio=12, anni=1, ricavi_annui_regime=12_000,
                 prodotti={0: 0.025}),
    )
    assert r.esiti[0].ricavi == pytest.approx(1_000)
    assert r.esiti[0].carico_totale == pytest.approx(232.18, abs=0.01)
    assert {pg.periodo for pg in r.pagamenti} == {"2028-06"}
    assert sum(pg.importo for pg in r.pagamenti) == pytest.approx(232.18, abs=0.01)
    assert r.kpi["interessi_lordi"] == pytest.approx(2.90, abs=0.01)
    assert r.kpi["imposta_sugli_interessi"] == pytest.approx(0.75, abs=0.01)
    assert r.kpi["bollo_deposito"] == pytest.approx(0.23, abs=0.01)
    assert r.kpi["interessi_netti"] == pytest.approx(1.92, abs=0.01)


def test_beneficio_coerente_con_formula_chiusa_su_prodotto_unico():
    tasso = 0.04
    r = simula(PROF_GS, Scenario(anni=3, ricavi_annui_regime=30_000, prodotti={0: tasso}))
    mesi_euro = (r.allocazioni["importo"] * r.allocazioni["mesi_fermi"]).sum()
    atteso = mesi_euro / 12 * (tasso * 0.74 - 0.002)
    assert r.kpi["interessi_netti"] == pytest.approx(atteso, rel=1e-9)
