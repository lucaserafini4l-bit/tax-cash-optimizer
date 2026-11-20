"""Test su IRPEF, detrazioni, forfettario e ordinario. Valori attesi calcolati a mano."""

from dataclasses import replace

import pytest

from taxcash import Profilo, calcola_anno, confronta_regimi
from taxcash.inps import calcola_contributi
from taxcash.tasse import detrazione_autonomo, irpef_lorda


def test_irpef_scaglioni_2026():
    assert irpef_lorda(0) == 0
    assert irpef_lorda(28_000) == pytest.approx(6_440.0)          # 28.000 x 23%
    assert irpef_lorda(50_000) == pytest.approx(13_700.0)         # + 22.000 x 33%
    assert irpef_lorda(55_000) == pytest.approx(15_850.0)         # + 5.000 x 43%


@pytest.mark.parametrize(
    "reddito, atteso",
    [
        (5_000, 1_265.0),
        (5_500, 1_265.0),
        (16_750, 500 + 765 * 0.5),    # 882,5
        (28_000, 500.0),
        (39_000, 250.0),              # 500 x 11.000 / 22.000
        (50_000, 0.0),
        (60_000, 0.0),
    ],
)
def test_detrazione_lavoro_autonomo(reddito, atteso):
    assert detrazione_autonomo(reddito) == pytest.approx(atteso)


def test_forfettario_professionista_startup_gestione_separata():
    # 30.000 x 78% = 23.400 ; INPS 26,07% = 6.100,38 ; imponibile 17.299,62 ; 5% = 864,98
    e = calcola_anno(Profilo(regime="forfettario", gestione="separata", coefficiente=0.78), 30_000)
    assert e.reddito == pytest.approx(23_400.0)
    assert e.inps_totale == pytest.approx(6_100.38, abs=0.01)
    assert e.imponibile == pytest.approx(17_299.62, abs=0.01)
    assert e.aliquota_forfettaria == 0.05
    assert e.imposta == pytest.approx(864.98, abs=0.01)


def test_forfettario_aliquota_15_dopo_5_anni_o_senza_startup():
    base = Profilo(regime="forfettario", gestione="separata", coefficiente=0.78)
    assert calcola_anno(base, 30_000, anno_attivita=5).aliquota_forfettaria == 0.05
    sesto = calcola_anno(base, 30_000, anno_attivita=6)
    assert sesto.aliquota_forfettaria == 0.15
    assert sesto.imposta == pytest.approx(17_299.62 * 0.15, abs=0.01)
    no_startup = calcola_anno(replace(base, startup=False), 30_000, anno_attivita=1)
    assert no_startup.aliquota_forfettaria == 0.15


def test_ecommerce_commerciante_sotto_minimale():
    # 30.000 x 40% = 12.000 < minimale 18.808 -> contributi fissi 4.611,64
    e = calcola_anno(
        Profilo(regime="forfettario", gestione="commercianti", coefficiente=0.40), 30_000
    )
    assert e.inps_fissi == pytest.approx(4_611.64, abs=0.01)
    assert e.inps_variabili == 0
    assert e.imponibile == pytest.approx(12_000 - 4_611.64, abs=0.01)
    assert e.imposta == pytest.approx((12_000 - 4_611.64) * 0.05, abs=0.01)


def test_contributi_minimali_2026():
    assert calcola_contributi(10_000, "commercianti").fissi == pytest.approx(4_611.64, abs=0.01)
    assert calcola_contributi(10_000, "artigiani").fissi == pytest.approx(4_521.36, abs=0.01)


def test_riduzione_35_su_contributi():
    # quota IVS 18.808 x 24,48% = 4.604,20 ridotta del 35% = 2.992,73 ; maternità 7,44 non ridotta
    c = calcola_contributi(10_000, "commercianti", riduzione_35=True)
    assert c.fissi == pytest.approx(2_992.73 + 7.44, abs=0.01)


def test_contributi_oltre_minimale():
    # 40.000 commercianti: fissi 4.611,64 + (40.000 - 18.808) x 24,48% = 5.187,80
    c = calcola_contributi(40_000, "commercianti")
    assert c.totale == pytest.approx(9_799.44, abs=0.01)


def test_contributi_proporzionali_ai_mesi_di_attivita():
    c = calcola_contributi(5_000, "commercianti", mesi_attivita=6)
    assert c.fissi == pytest.approx(4_611.6384 / 2, abs=0.01)


def test_ordinario_commerciante():
    profilo = Profilo(
        regime="ordinario",
        gestione="commercianti",
        costi_pct=0.20,
        addizionale_regionale=0.0,
        addizionale_comunale=0.0,
    )
    e = calcola_anno(profilo, 50_000)
    # reddito 40.000 ; INPS 9.799,44 ; base 30.200,56
    # IRPEF lorda 6.440 + 2.200,56 x 33% = 7.166,18 ; detrazione 500 x 19.799,44 / 22.000 = 449,99
    assert e.reddito == pytest.approx(40_000)
    assert e.imponibile == pytest.approx(30_200.56, abs=0.01)
    assert e.imposta == pytest.approx(7_166.18 - 449.99, abs=0.02)


def test_ordinario_con_altri_redditi_somma_agli_scaglioni():
    senza = Profilo(regime="ordinario", gestione="separata", costi_pct=0.0,
                    addizionale_regionale=0, addizionale_comunale=0)
    con = replace(senza, altri_redditi=30_000)
    assert calcola_anno(con, 20_000).imposta > calcola_anno(senza, 20_000).imposta


def test_avviso_soglie_forfettario():
    prof = Profilo(regime="forfettario", gestione="separata", coefficiente=0.78)
    assert any("85.000" in n for n in calcola_anno(prof, 90_000).note)
    assert any("100.000" in n for n in calcola_anno(prof, 120_000).note)
    assert calcola_anno(prof, 50_000).note == ()


def test_confronto_regimi_forfettario_conviene_su_redditi_bassi():
    prof = Profilo(gestione="separata", coefficiente=0.78, costi_pct=0.10,
                   addizionale_regionale=0.015, addizionale_comunale=0.005)
    esiti = confronta_regimi(30_000, prof, anno_attivita=1)
    assert esiti["forfettario"].imposta < esiti["ordinario"].imposta
    assert esiti["forfettario"].regime == "forfettario"
    assert esiti["ordinario"].regime == "ordinario"


def test_netto_confronto_sottrae_i_costi_reali_in_entrambi_i_regimi():
    prof = Profilo(gestione="separata", coefficiente=0.78,
                   addizionale_regionale=0.0, addizionale_comunale=0.0)
    esiti = confronta_regimi(30_000, prof, costi_pct_ordinario=0.30)
    for e in esiti.values():
        assert e.costi_reali == pytest.approx(9_000)
        assert e.netto_dopo_carico == pytest.approx(30_000 - 9_000 - e.carico_totale)
    # il forfettario non deduce i costi: l'imposta non cambia al variare dei costi reali
    assert (confronta_regimi(30_000, prof, costi_pct_ordinario=0.10)["forfettario"].imposta
            == pytest.approx(esiti["forfettario"].imposta))
