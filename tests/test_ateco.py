"""Test sulla classificazione ATECO -> coefficiente di redditività e gestione INPS."""

import pytest

from taxcash.ateco import (
    ATTIVITA,
    GRUPPI,
    _DIVISIONE_GRUPPO,
    classifica,
    classifica_attivita,
    classifica_gruppo,
    costi_impliciti,
)
from taxcash.params import COEFFICIENTI_FORFETTARIO


@pytest.mark.parametrize(
    "codice, coefficiente",
    [
        ("10.71", 0.40), ("11.07", 0.40),                     # industrie alimentari e bevande
        ("45.20", 0.40), ("46.21", 0.40), ("47.11", 0.40),    # commercio
        ("47.71.10", 0.40), ("47.91.10", 0.40),               # dettaglio e online
        ("47.81", 0.40), ("47.82", 0.54), ("47.89", 0.54),    # ambulanti
        ("46.1", 0.62), ("46.18.99", 0.62),                   # intermediari
        ("55.20", 0.40), ("56.10", 0.40),                     # alloggio e ristorazione
        ("41.20", 0.86), ("43.21", 0.86), ("68.31", 0.86),    # costruzioni e immobiliare
        ("70.22", 0.78), ("73.11", 0.78), ("74.10", 0.78),    # professioni
        ("85.59", 0.78), ("87.30", 0.78),
        ("62.01", 0.67), ("63.11", 0.67), ("58.11", 0.67),    # software e media: gruppo «altre»
        ("96.02", 0.67), ("49.41", 0.67), ("31.09", 0.67), ("35.11", 0.67),
    ],
)
def test_coefficiente_per_codice(codice, coefficiente):
    cl = classifica(codice, scelta="no")
    assert cl.errore is None and cl.fuori_ambito is None
    assert cl.coefficiente == pytest.approx(coefficiente)


@pytest.mark.parametrize("forma", ["62.01.00", "620100", "62.01", "62 01", "62"])
def test_formati_del_codice_equivalenti(forma):
    assert classifica(forma).coefficiente == pytest.approx(0.67)
    assert classifica(forma).gestione == "separata"


def test_chiarimenti_su_commercio_ambulante_e_intermediari():
    assert classifica("47").serve == "ambulante"
    assert classifica("47.8").serve == "ambulante"
    assert classifica("47", "no").coefficiente == pytest.approx(0.40)
    assert classifica("47", "alimentari").coefficiente == pytest.approx(0.40)
    assert classifica("47", "altri").coefficiente == pytest.approx(0.54)
    assert classifica("46").serve == "intermediario"
    assert classifica("46", "si").coefficiente == pytest.approx(0.62)
    assert classifica("46", "no").coefficiente == pytest.approx(0.40)


def test_professioni_con_cassa_sono_fuori_ambito():
    for codice in ("69.10", "69.20", "71.11", "75.00", "86.21", "86.90"):
        assert classifica(codice).serve == "cassa"
        cl = classifica(codice, "si")
        assert cl.fuori_ambito and cl.gestione is None
        no = classifica(codice, "no")
        assert no.fuori_ambito is None and no.gestione == "separata" and no.coefficiente == pytest.approx(0.78)


@pytest.mark.parametrize("codice", ["01.11", "02.10", "03.11", "64.19", "65.12", "66.22", "84.11"])
def test_divisioni_non_modellate(codice):
    cl = classifica(codice)
    assert cl.fuori_ambito and cl.completa


@pytest.mark.parametrize("codice", ["", "x", "6", "04", "44.1", "99999"[:1]])
def test_codici_non_validi(codice):
    assert classifica(codice).errore


def test_gestione_di_partenza():
    assert classifica("47.91").gestione == "commercianti"
    assert classifica("43.21").gestione == "artigiani"
    assert classifica("10.71").gestione == "artigiani"
    assert classifica("62.01").gestione == "separata"
    assert classifica("96.02").gestione == "artigiani"


def test_tabella_coerente_con_i_parametri():
    # I coefficienti usati dalla tabella ATECO sono gli stessi dei gruppi nei parametri.
    assert {g.coefficiente for g in GRUPPI.values()} == set(COEFFICIENTI_FORFETTARIO.values())
    assert set(_DIVISIONE_GRUPPO.values()) <= set(GRUPPI)


def test_elenco_attivita_classificabile_senza_domande():
    for att in ATTIVITA:
        cl = classifica_attivita(att)
        assert cl.errore is None, att.nome
        assert cl.serve is None, att.nome
        assert cl.completa, att.nome
        assert cl.fuori_ambito or (cl.coefficiente and cl.gestione), att.nome


def test_override_gestione_e_settori():
    meccanico = next(a for a in ATTIVITA if a.ateco == "45.20")
    assert classifica_attivita(meccanico).gestione == "artigiani"
    assert classifica_attivita(meccanico).coefficiente == pytest.approx(0.40)
    for chiave, g in GRUPPI.items():
        cl = classifica_gruppo(chiave)
        assert cl.coefficiente == g.coefficiente and cl.gestione in {"separata", "commercianti", "artigiani"}


def test_costi_impliciti():
    assert costi_impliciti(0.78) == pytest.approx(0.22)
    assert costi_impliciti(0.40) == pytest.approx(0.60)
