"""Parametri fiscali e contributivi (riferimento 2026).

Ogni valore è un parametro modificabile. Le fonti sono elencate in docs/PARAMETRI.md.
Gli importi relativi al 2026 vengono applicati a tutti gli anni simulati: aggiornarli
quando escono le circolari INPS e la legge di bilancio dell'anno successivo.
"""

from __future__ import annotations

from dataclasses import dataclass

INF = float("inf")


@dataclass(frozen=True)
class Parametri:
    anno: int = 2026

    # --- IRPEF (Legge di Bilancio 2026, L. 199/2025): 23% / 33% / 43% ---
    scaglioni_irpef: tuple[tuple[float, float], ...] = (
        (28_000.0, 0.23),
        (50_000.0, 0.33),
        (INF, 0.43),
    )

    # --- Detrazione redditi di lavoro autonomo / impresa minore (art. 13 c.5 TUIR) ---
    detr_aut_soglia_1: float = 5_500.0   # fino a qui: detrazione massima
    detr_aut_max: float = 1_265.0
    detr_aut_soglia_2: float = 28_000.0
    detr_aut_base: float = 500.0         # detrazione a 28.000 euro
    detr_aut_soglia_3: float = 50_000.0  # oltre: nessuna detrazione

    # --- Regime forfettario ---
    aliq_forfettario: float = 0.15
    aliq_forfettario_startup: float = 0.05
    anni_startup: int = 5
    soglia_ricavi_forfettario: float = 85_000.0
    soglia_uscita_immediata: float = 100_000.0

    # --- INPS Gestione Separata (circ. INPS n. 8/2026) ---
    gs_aliq_professionisti: float = 0.2607       # senza altra copertura previdenziale
    gs_aliq_altra_copertura: float = 0.24        # già assicurati altrove / pensionati

    # --- INPS Artigiani e Commercianti (circ. INPS n. 14/2026) ---
    aliq_artigiani: float = 0.24
    aliq_commercianti: float = 0.2448
    minimale_reddito: float = 18_808.0
    contributo_maternita_annuo: float = 7.44     # 0,62 euro al mese (commercianti e artigiani)
    riduzione_forfettari: float = 0.35           # regime contributivo agevolato (su domanda)

    # --- Acconti ---
    acconto_pct_imposta: float = 1.0             # metodo storico: 100% dell'imposta dell'anno prima
    acconto_pct_inps: float = 0.80               # 2 rate da 40%
    acconto_minimo: float = 51.65                # sotto: nessun acconto
    soglia_acconto_unico: float = 257.52         # sotto: acconto in unica rata a novembre

    # --- Conto deposito / conto corrente ---
    imposta_sostitutiva_interessi: float = 0.26
    bollo_deposito: float = 0.002                # 0,20% annuo sulla giacenza
    bollo_conto_corrente: float = 34.20          # fisso, uguale in entrambi gli scenari

    # --- Scadenze (mesi) ---
    mese_saldo_e_primo_acconto: int = 6          # 30 giugno (a volte prorogato a luglio)
    mese_secondo_acconto: int = 11               # 30 novembre
    mesi_rate_fisse_inps: tuple[int, ...] = (5, 8, 11, 2)  # 4a rata a febbraio anno dopo


PARAMETRI_2026 = Parametri()


# Coefficienti di redditività forfettario (Allegato 4, L. 190/2014)
COEFFICIENTI_FORFETTARIO: dict[str, float] = {
    "Industrie alimentari e bevande (ATECO 10-11)": 0.40,
    "Commercio all'ingrosso e al dettaglio, e-commerce (ATECO 45, 46, 47)": 0.40,
    "Commercio ambulante alimentare (ATECO 47.81)": 0.40,
    "Servizi di alloggio e ristorazione (ATECO 55-56)": 0.40,
    "Commercio ambulante altri prodotti (ATECO 47.82-47.89)": 0.54,
    "Intermediari del commercio (ATECO 46.1)": 0.62,
    "Altre attività economiche (manifattura, trasporti, servizi alla persona, informatica e media: ATECO 58-63)": 0.67,
    "Attività professionali, scientifiche, tecniche, sanitarie, di istruzione, finanziarie (ATECO 64-66, 69-75, 85-88)": 0.78,
    "Costruzioni e attività immobiliari (ATECO 41-43, 68)": 0.86,
}
