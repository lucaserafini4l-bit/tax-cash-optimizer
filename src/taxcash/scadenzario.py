"""Scadenzario dei versamenti: saldo, acconti e rate fisse INPS."""

from __future__ import annotations

from dataclasses import dataclass

from .params import Parametri, PARAMETRI_2026
from .tasse import EsitoAnno, Profilo


@dataclass(frozen=True)
class Pagamento:
    t: int            # mesi dall'inizio di gennaio dell'anno di partenza
    anno: int
    mese: int
    importo: float
    voce: str
    categoria: str    # "imposta" | "inps"

    @property
    def periodo(self) -> str:
        return f"{self.anno}-{self.mese:02d}"


def mese_assoluto(anno: int, mese: int, anno_inizio: int) -> int:
    return (anno - anno_inizio) * 12 + (mese - 1)


def _dividi_acconto(totale: float, rate_50_50: bool, p: Parametri) -> tuple[float, float]:
    """Prima e seconda rata dell'acconto d'imposta."""
    if totale < p.acconto_minimo:
        return 0.0, 0.0
    if totale < p.soglia_acconto_unico:
        return 0.0, totale
    if rate_50_50:
        return totale / 2.0, totale / 2.0
    return totale * 0.4, totale * 0.6


def costruisci_pagamenti(
    esiti: list[EsitoAnno],
    profilo: Profilo,
    anno_inizio: int,
    mese_inizio: int = 1,
    p: Parametri = PARAMETRI_2026,
) -> list[Pagamento]:
    """Versamenti generati da `esiti` (un EsitoAnno per ciascun anno di attività).

    Regole modellate:
    - nel primo anno non si versano acconti: saldo e primo acconto arrivano insieme
      l'anno dopo (doppio carico);
    - acconti con metodo storico (100% imposta, 80% contributi variabili INPS);
    - rate fisse INPS (artigiani/commercianti) a maggio, agosto, novembre e febbraio;
    - un saldo negativo (acconti superiori al dovuto) diventa credito sui versamenti successivi.
    L'orizzonte termina con il saldo dell'ultimo anno simulato: gli acconti dell'anno
    successivo non sono inclusi.
    """
    n = len(esiti)
    m_saldo = p.mese_saldo_e_primo_acconto
    m_acc2 = p.mese_secondo_acconto
    rate_50_50 = profilo.regime == "forfettario" or profilo.isa
    t_fine = mese_assoluto(anno_inizio + n, m_saldo, anno_inizio)

    grezzi: list[tuple[int, int, str, str, float]] = []  # (t, ordine, categoria, voce, importo)

    def aggiungi(anno: int, mese: int, ordine: int, cat: str, voce: str, importo: float) -> None:
        t = mese_assoluto(anno, mese, anno_inizio)
        if t <= t_fine and abs(importo) > 1e-9:
            grezzi.append((t, ordine, cat, voce, importo))

    for i, e in enumerate(esiti):
        k = i + 1
        anno = anno_inizio + i
        prev = esiti[i - 1] if i > 0 else None

        # --- Acconti dell'anno k (calcolati sull'anno k-1) ---
        acc_imp_1 = acc_imp_2 = acc_inps_1 = acc_inps_2 = 0.0
        if prev is not None:
            acc_imp_1, acc_imp_2 = _dividi_acconto(prev.imposta * p.acconto_pct_imposta, rate_50_50, p)
            base_inps = prev.inps_variabili * p.acconto_pct_inps
            acc_inps_1 = acc_inps_2 = base_inps / 2.0
        aggiungi(anno, m_saldo, 1, "imposta", f"1° acconto imposta (anno {k})", acc_imp_1)
        aggiungi(anno, m_acc2, 1, "imposta", f"2° acconto imposta (anno {k})", acc_imp_2)
        aggiungi(anno, m_saldo, 1, "inps", f"1° acconto contributi INPS (anno {k})", acc_inps_1)
        aggiungi(anno, m_acc2, 1, "inps", f"2° acconto contributi INPS (anno {k})", acc_inps_2)

        # --- Saldo dell'anno k, pagato a giugno dell'anno dopo ---
        saldo_imp = e.imposta - (acc_imp_1 + acc_imp_2)
        saldo_inps = e.inps_variabili - (acc_inps_1 + acc_inps_2)
        aggiungi(anno + 1, m_saldo, 0, "imposta", f"Saldo imposta (anno {k})", saldo_imp)
        aggiungi(anno + 1, m_saldo, 0, "inps", f"Saldo contributi INPS (anno {k})", saldo_inps)

        # --- Rate fisse INPS sul minimale ---
        if e.inps_fissi > 0:
            rate = [(anno, m) for m in p.mesi_rate_fisse_inps if m != 2 and (k > 1 or m >= mese_inizio)]
            rate.append((anno + 1, 2))
            quota = e.inps_fissi / len(rate)
            for (a, m) in rate:
                aggiungi(a, m, 1, "inps", f"Rata fissa contributi INPS (anno {k})", quota)

    grezzi.sort(key=lambda x: (x[0], x[1]))

    # Crediti (saldi negativi) compensati con i versamenti successivi della stessa categoria
    credito = {"imposta": 0.0, "inps": 0.0}
    pagamenti: list[Pagamento] = []
    for t, _ord, cat, voce, importo in grezzi:
        if importo < 0:
            credito[cat] += -importo
            continue
        compensato = min(importo, credito[cat])
        credito[cat] -= compensato
        netto = importo - compensato
        if netto > 1e-9:
            anno = anno_inizio + t // 12
            mese = t % 12 + 1
            pagamenti.append(Pagamento(t, anno, mese, netto, voce, cat))
    return pagamenti
