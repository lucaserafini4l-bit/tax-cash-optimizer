"""Test su fatturato mensile con crescita e sul consigliere (regime, accantonamento, scadenze, liquidità)."""

import math

import pytest

from taxcash import Profilo, Scenario, calcola_anno, serie_ricavi_mensili, simula
from taxcash.consigliere import Richiesta, anni_forfettario, consiglia, soglia_dipendente

BASE = dict(anno_inizio=2027, mese_inizio=1, anni=3, ricavo_mensile_iniziale=2_500.0)
CONSULENTE = dict(coefficiente=0.78, gestione="separata", **BASE)


# ----------------------------------------------------------------- serie di ricavi e simulazione
def test_serie_ricavi_mensili():
    assert serie_ricavi_mensili(1_000, 0.0, 4) == [1_000] * 4
    s = serie_ricavi_mensili(1_000, 0.10, 3)
    assert s == pytest.approx([1_000, 1_100, 1_210])
    assert serie_ricavi_mensili(1_000, 0.10, 4, tetto_mensile=1_150) == pytest.approx([1_000, 1_100, 1_150, 1_150])


def test_serie_costante_equivale_al_vecchio_scenario_annuo():
    prof = Profilo(regime="forfettario", gestione="separata", coefficiente=0.78, startup=True)
    vecchio = simula(prof, Scenario(anno_inizio=2027, anni=3, ricavi_annui_regime=30_000))
    nuovo = simula(prof, Scenario(anno_inizio=2027, anni=3, ricavi_mensili=[2_500.0] * 36))
    assert nuovo.kpi["carico_totale"] == pytest.approx(vecchio.kpi["carico_totale"])
    assert nuovo.kpi["interessi_netti"] == pytest.approx(vecchio.kpi["interessi_netti"])
    assert list(nuovo.timeline["accantonato"]) == pytest.approx(list(vecchio.timeline["accantonato"]))


def test_ricavi_mensili_con_partenza_a_meta_anno():
    prof = Profilo(regime="forfettario", gestione="separata", coefficiente=0.78)
    sc = Scenario(anno_inizio=2027, mese_inizio=7, anni=2, ricavi_mensili=[1_000.0] * 18)   # 6 + 12 mesi
    ris = simula(prof, sc)
    assert [e.ricavi for e in ris.esiti] == pytest.approx([6_000, 12_000])
    with pytest.raises(ValueError):
        simula(prof, Scenario(anno_inizio=2027, mese_inizio=7, anni=2, ricavi_mensili=[1_000.0] * 24))


def test_accantonamento_segue_i_ricavi_mensili_con_crescita():
    prof = Profilo(regime="forfettario", gestione="separata", coefficiente=0.78, startup=True)
    serie = serie_ricavi_mensili(1_000, 0.02, 24)
    ris = simula(prof, Scenario(anno_inizio=2027, anni=2, ricavi_mensili=serie))
    tl = ris.timeline
    for k, e in enumerate(ris.esiti):
        anno = tl[tl["periodo"].str.startswith(str(2027 + k))]
        assert anno["incassi"].sum() == pytest.approx(e.ricavi)
        assert anno["accantonato"].sum() == pytest.approx(e.ricavi * e.pressione)
    assert tl["incassi"].iloc[1] > tl["incassi"].iloc[0]       # il fatturato cresce mese su mese


# ----------------------------------------------------------------- limiti del forfettario
def test_anni_forfettario_soglie():
    assert anni_forfettario([50_000, 60_000], [12, 12]) == 2
    assert anni_forfettario([50_000, 90_000, 95_000], [12, 12, 12]) == 2     # esce dall'anno dopo
    assert anni_forfettario([50_000, 105_000, 110_000], [12, 12, 12]) == 1   # uscita immediata sopra 100.000
    assert anni_forfettario([50_000], [6]) == 1                              # 100.000 annualizzati: non sopra soglia
    assert anni_forfettario([51_000], [6]) == 0                              # 102.000 annualizzati
    assert anni_forfettario([60_000], [12]) == 1


def test_soglia_dipendente():
    assert soglia_dipendente(2026) == 35_000
    assert soglia_dipendente(2027) == 30_000


# ----------------------------------------------------------------- il consiglio
def test_consulente_conviene_il_forfettario_e_i_numeri_tornano():
    c = consiglia(Richiesta(**CONSULENTE))
    assert c.regime == "forfettario" and c.forfettario_disponibile and c.anni_confronto == 3
    # Controllo indipendente: 30.000 euro l'anno, GS 26,07%, aliquota 5% (anno 1).
    esito = calcola_anno(Profilo(regime="forfettario", gestione="separata", coefficiente=0.78), 30_000)
    assert esito.inps_totale == pytest.approx(30_000 * 0.78 * 0.2607)
    assert esito.imposta == pytest.approx((30_000 * 0.78 - esito.inps_totale) * 0.05)
    assert c.accantonamento_pct[0] == pytest.approx(esito.pressione)
    assert c.accantonamento_mensile[0] == pytest.approx(2_500 * esito.pressione)
    assert c.carico_forfettario == pytest.approx(3 * esito.carico_totale)
    assert c.risparmio == pytest.approx(
        (c.carico_ordinario + c.gestione_ordinario) - (c.carico_forfettario + c.gestione_forfettario)
    )


def test_primo_anno_senza_imposte_e_doppio_carico_a_giugno():
    c = consiglia(Richiesta(**CONSULENTE))
    assert c.prima_scadenza_imposte.anno == 2028 and c.prima_scadenza_imposte.mese == 6
    primo = c.calendario.iloc[0]
    assert primo["periodo"] == "2028-06"                      # Gestione Separata: nessun versamento nel 2027
    assert "Saldo" in primo["voci"] and "1° acconto" in primo["voci"]
    esito = calcola_anno(Profilo(regime="forfettario", gestione="separata", coefficiente=0.78), 30_000)
    # giugno 2028 = saldo anno 1 (imposta + INPS, senza acconti) + primo acconto anno 2 (100% imposta, 80% INPS /2)
    atteso = esito.imposta + esito.inps_variabili + esito.imposta / 2 + esito.inps_variabili * 0.8 / 2
    assert primo["importo"] == pytest.approx(atteso)


def test_commercianti_pagano_le_rate_fisse_gia_nel_primo_anno():
    c = consiglia(Richiesta(coefficiente=0.40, gestione="commercianti", **BASE))
    assert c.prima_scadenza.anno == 2027 and c.prima_scadenza.mese == 5
    assert c.calendario.iloc[0]["voci"].startswith("Rata fissa")


def test_dipendente_sopra_soglia_non_accede_al_forfettario():
    c = consiglia(Richiesta(situazione="dipendente", reddito_altro=40_000, **CONSULENTE))
    assert not c.forfettario_disponibile and c.regime == "ordinario" and c.ris_alternativa is None
    assert any("dipendente" in a for a in c.avvisi)
    sotto = consiglia(Richiesta(situazione="dipendente", reddito_altro=20_000, **CONSULENTE))
    assert sotto.forfettario_disponibile


def test_dipendente_usa_aliquota_gestione_separata_24():
    unica = consiglia(Richiesta(**CONSULENTE))
    dip = consiglia(Richiesta(situazione="dipendente", reddito_altro=20_000, **CONSULENTE))
    assert dip.ris.esiti[0].inps_totale == pytest.approx(30_000 * 0.78 * 0.24)
    assert dip.ris.esiti[0].inps_totale < unica.ris.esiti[0].inps_totale


def test_crescita_oltre_85mila_limita_il_forfettario():
    c = consiglia(Richiesta(**{**CONSULENTE, "anni": 4, "ricavo_mensile_iniziale": 5_000.0}, crescita_mensile=0.03))
    assert 0 < c.anni_forfettario < 4 and c.anni_confronto == c.anni_forfettario
    assert any("85.000" in a for a in c.avvisi)


def test_costi_di_pareggio_sono_il_punto_in_cui_i_regimi_si_equivalgono():
    req = Richiesta(**CONSULENTE)
    c = consiglia(req)
    assert 0 < c.costi_pareggio < 0.95
    # Con costi poco sopra il pareggio l'ordinario vince, poco sotto vince il forfettario.
    soglia = c.costi_pareggio
    sotto = consiglia(Richiesta(**{**CONSULENTE, "costi_pct": soglia - 0.03}))
    sopra = consiglia(Richiesta(**{**CONSULENTE, "costi_pct": soglia + 0.03}))
    assert sotto.regime == "forfettario" and sopra.regime == "ordinario"


def test_il_costo_del_commercialista_puo_cambiare_il_verdetto():
    # E-commerce a 2.000 euro al mese: con redditi bassi l'IRPEF ordinaria si azzera per le detrazioni da lavoro
    # autonomo e l'ordinario costa poche decine di euro in meno di imposta, ma il commercialista pesa di più.
    base = dict(coefficiente=0.40, gestione="commercianti", anno_inizio=2027, mese_inizio=1, anni=3,
                ricavo_mensile_iniziale=2_000.0)
    senza = consiglia(Richiesta(costo_gestione_forfettario=0, costo_gestione_ordinario=0, **base))
    con = consiglia(Richiesta(**base))
    assert senza.regime == "ordinario"
    assert con.regime == "forfettario"


def test_destinazioni_coprono_tutto_l_accantonato():
    c = consiglia(Richiesta(**CONSULENTE))
    accantonato = c.ris.timeline["accantonato"].sum()
    assert c.destinazioni["importo"].sum() == pytest.approx(accantonato)
    assert c.destinazioni["interessi_netti"].sum() == pytest.approx(c.ris.kpi["interessi_netti"])


def test_vincolo_massimo_limita_i_prodotti():
    libero = consiglia(Richiesta(max_vincolo_mesi=0, **CONSULENTE))
    assert list(libero.destinazioni["dove"]) == ["libero"]
    a_12 = consiglia(Richiesta(max_vincolo_mesi=12, **CONSULENTE))
    assert a_12.ris.kpi["interessi_netti"] > libero.ris.kpi["interessi_netti"]


def test_suggerimento_riduzione_inps_35_calcolato():
    req = Richiesta(coefficiente=0.40, gestione="commercianti", **BASE)
    c = consiglia(req)
    assert c.regime == "forfettario"
    testo = next(s for s in c.suggerimenti if "35%" in s)
    con = consiglia(Richiesta(coefficiente=0.40, gestione="commercianti", riduzione_inps_35=True, **BASE))
    atteso = (sum(e.carico_totale for e in c.ris.esiti) - sum(e.carico_totale for e in con.ris.esiti)) / 3
    assert f"{atteso:,.0f}".replace(",", ".") in testo
    assert not any("35%" in s for s in con.suggerimenti)


def test_attivita_non_nuova_suggerisce_aliquota_5():
    c = consiglia(Richiesta(nuova_attivita=False, **CONSULENTE))
    assert c.ris.esiti[0].aliquota_forfettaria == pytest.approx(0.15)
    assert any("5%" in s for s in c.suggerimenti)


def test_situazione_non_valida():
    with pytest.raises(ValueError):
        consiglia(Richiesta(situazione="altro", **CONSULENTE))


def test_costi_pareggio_casi_limite():
    # Commercialista ordinario carissimo: l'ordinario non conviene nemmeno con costi del 95% -> infinito.
    sempre_forf = consiglia(Richiesta(costo_gestione_ordinario=50_000.0, **CONSULENTE))
    assert sempre_forf.regime == "forfettario" and math.isinf(sempre_forf.costi_pareggio)
    # Commercialista forfettario carissimo: l'ordinario conviene già senza costi -> 0.
    sempre_ord = consiglia(Richiesta(costo_gestione_forfettario=50_000.0, **CONSULENTE))
    assert sempre_ord.regime == "ordinario" and sempre_ord.costi_pareggio == 0.0
