"""Simulazione mensile: incassi, accantonamento per le imposte e rendimento su conto deposito."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from .deposito import interessi_periodo, miglior_prodotto
from .params import Parametri, PARAMETRI_2026
from .scadenzario import Pagamento, costruisci_pagamenti
from .tasse import EsitoAnno, Profilo, calcola_anno

# Esempi di offerte di mercato rilevate da articoli di giugno-luglio 2026 (vedi docs/PARAMETRI.md).
# Da sostituire con le offerte reali al momento dell'apertura del conto.
PRODOTTI_ESEMPIO: dict[int, float] = {0: 0.025, 12: 0.040, 24: 0.0475}


@dataclass
class Scenario:
    anno_inizio: int = 2027
    mese_inizio: int = 1
    anni: int = 3
    ricavi_annui_regime: float = 30_000.0      # fatturato annuo a regime (anno intero)
    crescita_annua: float = 0.0
    accantonamento_pct: float | None = None    # None = aliquota effettiva calcolata dal modello
    prodotti: dict[int, float] = field(default_factory=lambda: dict(PRODOTTI_ESEMPIO))
    tasso_conto_corrente: float = 0.0
    # Se valorizzato, sostituisce ricavi_annui_regime e crescita_annua: fatturato di ogni mese di attività,
    # dal primo mese in poi (lunghezza = somma dei mesi attivi di tutti gli anni simulati).
    ricavi_mensili: list[float] | None = None

    def mesi_attivi(self, k: int) -> int:
        """Mesi di attività nell'anno k (0 = primo anno)."""
        return 13 - self.mese_inizio if k == 0 else 12


def serie_ricavi_mensili(
    iniziale: float,
    crescita_mensile: float,
    mesi: int,
    tetto_mensile: float | None = None,
) -> list[float]:
    """Fatturato mensile con crescita composta; `tetto_mensile` ferma la crescita a un massimo."""
    serie = []
    for j in range(mesi):
        valore = max(0.0, iniziale * (1.0 + crescita_mensile) ** j)
        if tetto_mensile is not None:
            valore = min(valore, tetto_mensile)
        serie.append(valore)
    return serie


@dataclass
class Risultato:
    esiti: list[EsitoAnno]
    pagamenti: list[Pagamento]
    timeline: pd.DataFrame
    allocazioni: pd.DataFrame
    kpi: dict[str, float]
    avvisi: list[str]


def _abbina_fifo(
    tranche: list[list[float]], pagamenti: list[tuple[int, float]]
) -> tuple[list[tuple[int, int, float]], list[tuple[int, float]], list[tuple[int, float]]]:
    """Ogni pagamento consuma le somme accantonate più vecchie (FIFO).

    Restituisce (abbinamenti (t_versamento, t_pagamento, importo), scoperti, residui).
    """
    abbinamenti: list[tuple[int, int, float]] = []
    scoperti: list[tuple[int, float]] = []
    idx = 0
    for tp, importo in pagamenti:
        da_coprire = importo
        while da_coprire > 1e-9 and idx < len(tranche) and tranche[idx][0] <= tp:
            t, disponibile = int(tranche[idx][0]), tranche[idx][1]
            uso = min(disponibile, da_coprire)
            abbinamenti.append((t, tp, uso))
            tranche[idx][1] -= uso
            da_coprire -= uso
            if tranche[idx][1] <= 1e-9:
                idx += 1
        if da_coprire > 1e-9:
            scoperti.append((tp, da_coprire))
    residui = [(int(t), a) for t, a in tranche[idx:] if a > 1e-9]
    return abbinamenti, scoperti, residui


def simula(
    profilo: Profilo,
    scenario: Scenario,
    p: Parametri = PARAMETRI_2026,
) -> Risultato:
    n = scenario.anni
    avvisi: list[str] = []

    # --- 1. Imposte e contributi per anno ---
    mesi = [scenario.mesi_attivi(k) for k in range(n)]
    if scenario.ricavi_mensili is None:
        ricavi = [
            scenario.ricavi_annui_regime * (1 + scenario.crescita_annua) ** k * mesi[k] / 12.0
            for k in range(n)
        ]
        mensili_per_anno = [[ricavi[k] / mesi[k]] * mesi[k] if mesi[k] else [] for k in range(n)]
    else:
        if len(scenario.ricavi_mensili) != sum(mesi):
            raise ValueError(
                f"ricavi_mensili deve avere {sum(mesi)} valori (mesi di attività), non {len(scenario.ricavi_mensili)}"
            )
        mensili_per_anno, pos = [], 0
        for k in range(n):
            mensili_per_anno.append(list(scenario.ricavi_mensili[pos : pos + mesi[k]]))
            pos += mesi[k]
        ricavi = [sum(m) for m in mensili_per_anno]
    esiti = [calcola_anno(profilo, ricavi[k], k + 1, mesi[k], p) for k in range(n)]
    for e in esiti:
        for nota in e.note:
            avvisi.append(f"Anno {e.anno_attivita}: {nota}")

    # --- 2. Scadenzario ---
    pagamenti = costruisci_pagamenti(esiti, profilo, scenario.anno_inizio, scenario.mese_inizio, p)
    t_fine = n * 12 + p.mese_saldo_e_primo_acconto - 1
    durata = t_fine + 1

    # --- 3. Incassi e accantonamento mensile ---
    incasso = [0.0] * durata
    accantonato = [0.0] * durata
    for k in range(n):
        primo = k * 12 + (scenario.mese_inizio - 1 if k == 0 else 0)
        if scenario.accantonamento_pct is None:
            quota = esiti[k].pressione
        else:
            quota = scenario.accantonamento_pct
        for j, t in enumerate(range(primo, primo + mesi[k])):
            incasso[t] = mensili_per_anno[k][j]
            accantonato[t] = mensili_per_anno[k][j] * quota

    # --- 4. Abbinamento versamenti <-> accantonamenti e interessi ---
    tranche = [[float(t), a] for t, a in enumerate(accantonato) if a > 1e-9]
    flussi = [(pg.t, pg.importo) for pg in pagamenti]
    abbin, scoperti, residui = _abbina_fifo(tranche, flussi)

    righe = []
    beneficio_per_mese = [0.0] * durata
    totali = dict(lordi=0.0, imposta=0.0, bollo=0.0, cc_netti=0.0)

    def registra(t_in: int, t_out: int, importo: float, destinazione: str) -> None:
        mesi_fermi = t_out - t_in
        vincolo, tasso = miglior_prodotto(scenario.prodotti, mesi_fermi)
        dep = interessi_periodo(importo, mesi_fermi, tasso, p=p)
        cc = interessi_periodo(importo, mesi_fermi, scenario.tasso_conto_corrente, con_bollo=False, p=p)
        totali["lordi"] += dep.lordi
        totali["imposta"] += dep.imposta
        totali["bollo"] += dep.bollo
        totali["cc_netti"] += cc.netti
        beneficio_per_mese[min(t_out, durata - 1)] += dep.netti - cc.netti
        righe.append(
            dict(
                versato_a=_periodo(t_in, scenario.anno_inizio),
                destinato_a=destinazione,
                mesi_fermi=mesi_fermi,
                importo=importo,
                prodotto="libero" if vincolo == 0 else f"vincolato {vincolo} mesi",
                tasso_lordo=tasso,
                interessi_lordi=dep.lordi,
                imposta_26=dep.imposta,
                bollo=dep.bollo,
                interessi_netti=dep.netti,
                beneficio_vs_conto_corrente=dep.netti - cc.netti,
            )
        )

    for t_in, t_out, importo in abbin:
        registra(t_in, t_out, importo, _periodo(t_out, scenario.anno_inizio))
    for t_in, importo in residui:
        registra(t_in, t_fine, importo, "riserva residua a fine orizzonte")

    allocazioni = pd.DataFrame(righe)

    # --- 5. Timeline mensile ---
    pag_imp = [0.0] * durata
    pag_inps = [0.0] * durata
    for pg in pagamenti:
        (pag_imp if pg.categoria == "imposta" else pag_inps)[pg.t] += pg.importo

    riserva, cum_acc, cum_pag, cum_ben = [], 0.0, 0.0, 0.0
    cum_beneficio = []
    for t in range(durata):
        cum_acc += accantonato[t]
        cum_pag += pag_imp[t] + pag_inps[t]
        cum_ben += beneficio_per_mese[t]
        riserva.append(cum_acc - cum_pag)
        cum_beneficio.append(cum_ben)

    timeline = pd.DataFrame(
        {
            "periodo": [_periodo(t, scenario.anno_inizio) for t in range(durata)],
            "incassi": incasso,
            "accantonato": accantonato,
            "versamenti_imposte": pag_imp,
            "versamenti_inps": pag_inps,
            "riserva": riserva,
            "beneficio_cumulato": cum_beneficio,
        }
    )

    # --- 6. KPI ---
    tot_imposte = sum(e.imposta for e in esiti)
    tot_inps = sum(e.inps_totale for e in esiti)
    tot_ricavi = sum(ricavi)
    riserva_positiva = [max(0.0, r) for r in riserva]
    riserva_media = sum(riserva_positiva) / durata if durata else 0.0
    interessi_netti = totali["lordi"] - totali["imposta"] - totali["bollo"]
    beneficio = interessi_netti - totali["cc_netti"]
    scoperto_tot = sum(x for _, x in scoperti)
    if scoperto_tot > 1e-6:
        avvisi.append(
            f"Accantonamento insufficiente: {scoperto_tot:,.0f} euro di versamenti non coperti dalla riserva."
        )
    if min(riserva) < -1e-6:
        avvisi.append("La riserva scende sotto zero: serve liquidità aggiuntiva alle scadenze.")

    kpi = {
        "ricavi_totali": tot_ricavi,
        "imposte_totali": tot_imposte,
        "contributi_inps_totali": tot_inps,
        "carico_totale": tot_imposte + tot_inps,
        "pressione_effettiva": (tot_imposte + tot_inps) / tot_ricavi if tot_ricavi else 0.0,
        "versamenti_nell_orizzonte": sum(pg.importo for pg in pagamenti),
        "riserva_massima": max(riserva_positiva) if riserva_positiva else 0.0,
        "riserva_media": riserva_media,
        "riserva_fine_primo_anno": riserva[min(11, durata - 1)],
        "interessi_lordi": totali["lordi"],
        "imposta_sugli_interessi": totali["imposta"],
        "bollo_deposito": totali["bollo"],
        "interessi_netti": interessi_netti,
        "beneficio_vs_conto_corrente": beneficio,
        "beneficio_su_carico_totale": beneficio / (tot_imposte + tot_inps) if (tot_imposte + tot_inps) else 0.0,
        "rendimento_netto_medio_annuo": (
            beneficio / (riserva_media * durata / 12.0) if riserva_media > 0 else 0.0
        ),
        "scoperto_totale": scoperto_tot,
    }
    return Risultato(esiti, pagamenti, timeline, allocazioni, kpi, avvisi)


def _periodo(t: int, anno_inizio: int) -> str:
    return f"{anno_inizio + t // 12}-{t % 12 + 1:02d}"
