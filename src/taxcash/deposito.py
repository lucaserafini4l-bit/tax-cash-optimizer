"""Rendimento netto della liquidità accantonata su conto deposito (e confronto con il conto corrente)."""

from __future__ import annotations

from dataclasses import dataclass

from .params import Parametri, PARAMETRI_2026


@dataclass(frozen=True)
class Interessi:
    lordi: float
    imposta: float
    bollo: float

    @property
    def netti(self) -> float:
        return self.lordi - self.imposta - self.bollo


def interessi_periodo(
    importo: float,
    mesi: float,
    tasso_lordo: float,
    *,
    con_bollo: bool = True,
    p: Parametri = PARAMETRI_2026,
) -> Interessi:
    """Interessi di un importo tenuto fermo per `mesi` (interesse semplice, bollo pro rata)."""
    frazione = mesi / 12.0
    lordi = importo * tasso_lordo * frazione
    imposta = lordi * p.imposta_sostitutiva_interessi
    bollo = importo * p.bollo_deposito * frazione if con_bollo else 0.0
    return Interessi(lordi=lordi, imposta=imposta, bollo=bollo)


def rendimento_netto_annuo(tasso_lordo: float, p: Parametri = PARAMETRI_2026) -> float:
    """Rendimento netto annuo = tasso x (1 - 26%) - bollo 0,20%."""
    return tasso_lordo * (1.0 - p.imposta_sostitutiva_interessi) - p.bollo_deposito


def tasso_pareggio(tasso_conto_corrente: float = 0.0, p: Parametri = PARAMETRI_2026) -> float:
    """Tasso lordo minimo del deposito perché convenga rispetto al conto corrente."""
    netto_cc = tasso_conto_corrente * (1.0 - p.imposta_sostitutiva_interessi)
    return (netto_cc + p.bollo_deposito) / (1.0 - p.imposta_sostitutiva_interessi)


def miglior_prodotto(prodotti: dict[int, float], mesi_disponibili: float) -> tuple[int, float]:
    """Tra i prodotti con vincolo <= mesi disponibili, quello col tasso lordo più alto.

    `prodotti` mappa mesi di vincolo -> tasso lordo annuo (0 = deposito libero).
    Ipotesi: il vincolo può essere dimensionato sulla data di scadenza del versamento.
    """
    candidati = [(m, t) for m, t in prodotti.items() if m <= mesi_disponibili + 1e-9]
    if not candidati:
        m_min = min(prodotti)
        return m_min, prodotti[m_min]
    return max(candidati, key=lambda x: x[1])
