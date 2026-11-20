"""Test dell'interfaccia Streamlit (modalità semplice e avanzata) con il framework AppTest."""

from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest

RADICE = Path(__file__).resolve().parent.parent
APP = str(RADICE / "app.py")


def _widget(elementi, etichetta):
    return next(e for e in elementi if e.label == etichetta)


def _avvia() -> AppTest:
    return AppTest.from_file(APP, default_timeout=60).run()


def _testi(elementi) -> str:
    return " ".join(e.value for e in elementi)


def test_senza_attivita_chiede_di_scegliere():
    at = _avvia()
    assert not at.exception
    assert "Scegli la tua attività" in _testi(at.info)
    assert len(at.metric) == 0


def test_sviluppatore_software_ottiene_la_risposta_completa():
    at = _avvia()
    _widget(at.selectbox, "Attività").select("Sviluppatore software / programmatore").run()
    assert not at.exception
    assert "Coefficiente di redditività: 67%" in _testi(at.markdown)
    assert "Ti conviene il regime forfettario" in _testi(at.markdown)
    etichette = [m.label for m in at.metric]
    assert etichette == ["Da mettere da parte", "Primo versamento", "Interessi netti stimati"]
    assert all(m.value for m in at.metric)
    assert "%" in at.metric[0].value


def test_professione_con_cassa_blocca_con_avviso():
    at = _avvia()
    _widget(at.selectbox, "Attività").select("Avvocato").run()
    assert not at.exception
    assert "non è coperto" in _testi(at.warning)
    assert len(at.metric) == 0


def test_codice_ateco_con_chiarimento_su_commercio_ambulante():
    at = _avvia()
    _widget(at.radio, "Come vuoi indicarla").set_value("Ho il codice ATECO").run()
    _widget(at.text_input, "Codice ATECO (bastano le prime 2-4 cifre)").input("47").run()
    domanda = _widget(at.radio, "Vendi in forma ambulante (mercati, fiere)?")
    domanda.set_value("Sì: altri prodotti").run()
    assert not at.exception
    assert "Coefficiente di redditività: 54%" in _testi(at.markdown)


def test_codice_ateco_non_valido_mostra_errore():
    at = _avvia()
    _widget(at.radio, "Come vuoi indicarla").set_value("Ho il codice ATECO").run()
    _widget(at.text_input, "Codice ATECO (bastano le prime 2-4 cifre)").input("04").run()
    assert not at.exception and at.error and len(at.metric) == 0


def test_dipendente_sopra_soglia_va_in_ordinario():
    at = _avvia()
    _widget(at.selectbox, "Attività").select("Sviluppatore software / programmatore").run()
    _widget(at.radio, "Situazione").set_value("Sono dipendente").run()
    _widget(at.number_input, "Reddito lordo annuo da lavoro dipendente o pensione (€)").set_value(60_000.0).run()
    assert not at.exception
    assert "Ti conviene il regime ordinario" in _testi(at.markdown)
    assert "non è accessibile" in _testi(at.warning)


def test_fatturato_zero_non_calcola():
    at = _avvia()
    _widget(at.selectbox, "Attività").select("E-commerce / vendita online").run()
    _widget(at.number_input, "Fatturato mensile previsto all'inizio (€)").set_value(0.0).run()
    assert not at.exception and len(at.metric) == 0


def test_modalita_avanzata_funziona():
    # La pagina si apre dall'app principale, come in produzione (il link «Torna alla modalità semplice» punta a app.py).
    at = _avvia()
    at.switch_page("pages/Modalita_avanzata.py").run()
    assert not at.exception
    assert len(at.tabs) == 5
