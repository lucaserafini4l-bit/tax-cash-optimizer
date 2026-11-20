"""Calcolo delle imposte annuali per regime fiscale (forfettario / ordinario semplificato)."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from .inps import calcola_contributi
from .params import Parametri, PARAMETRI_2026

REGIMI = ("forfettario", "ordinario")


@dataclass(frozen=True)
class Profilo:
    """Caratteristiche fiscali del contribuente (persona fisica con partita IVA)."""

    regime: str = "forfettario"
    gestione: str = "separata"             # separata | commercianti | artigiani
    coefficiente: float = 0.78             # forfettario: coefficiente di redditività
    costi_pct: float = 0.0                 # ordinario: costi deducibili in % dei ricavi
    startup: bool = True                   # forfettario: aliquota 5% per i primi 5 anni
    riduzione_inps_35: bool = False        # forfettario + artigiani/commercianti, su domanda
    altra_copertura: bool = False          # Gestione Separata: già assicurato altrove (24%)
    altri_redditi: float = 0.0             # ordinario: imponibile IRPEF da altre fonti
    addizionale_regionale: float = 0.015   # valore illustrativo: personalizzare
    addizionale_comunale: float = 0.005    # valore illustrativo: personalizzare
    isa: bool = False                      # ordinario: soggetto a ISA (acconti 50% + 50%)


@dataclass(frozen=True)
class EsitoAnno:
    anno_attivita: int
    regime: str
    ricavi: float
    costi: float
    reddito: float               # reddito d'impresa/professionale (forfettario: dopo coefficiente)
    inps_fissi: float
    inps_variabili: float
    imponibile: float            # base su cui si applica l'imposta (dopo deduzione contributi)
    aliquota_forfettaria: float  # 0 se ordinario
    imposta: float               # imposta sostitutiva oppure IRPEF netta + addizionali sull'attività
    note: tuple[str, ...] = field(default_factory=tuple)
    costi_reali: float = 0.0     # costi effettivamente sostenuti (nel forfettario non deducibili)

    @property
    def inps_totale(self) -> float:
        return self.inps_fissi + self.inps_variabili

    @property
    def carico_totale(self) -> float:
        return self.imposta + self.inps_totale

    @property
    def netto_dopo_carico(self) -> float:
        return self.ricavi - self.costi_reali - self.carico_totale

    @property
    def pressione(self) -> float:
        return self.carico_totale / self.ricavi if self.ricavi > 0 else 0.0


def irpef_lorda(reddito: float, p: Parametri = PARAMETRI_2026) -> float:
    """IRPEF lorda per scaglioni."""
    totale, precedente = 0.0, 0.0
    for limite, aliquota in p.scaglioni_irpef:
        if reddito > precedente:
            totale += (min(reddito, limite) - precedente) * aliquota
        precedente = limite
    return totale


def detrazione_autonomo(reddito_complessivo: float, p: Parametri = PARAMETRI_2026) -> float:
    """Detrazione per redditi di lavoro autonomo e impresa minore (art. 13 c.5 TUIR)."""
    r = reddito_complessivo
    if r <= p.detr_aut_soglia_1:
        return p.detr_aut_max
    if r <= p.detr_aut_soglia_2:
        quota = (p.detr_aut_soglia_2 - r) / (p.detr_aut_soglia_2 - p.detr_aut_soglia_1)
        return p.detr_aut_base + (p.detr_aut_max - p.detr_aut_base) * quota
    if r <= p.detr_aut_soglia_3:
        return p.detr_aut_base * (p.detr_aut_soglia_3 - r) / (p.detr_aut_soglia_3 - p.detr_aut_soglia_2)
    return 0.0


def calcola_anno(
    profilo: Profilo,
    ricavi: float,
    anno_attivita: int = 1,
    mesi_attivita: int = 12,
    p: Parametri = PARAMETRI_2026,
) -> EsitoAnno:
    """Calcola imposta e contributi di competenza di un anno.

    Semplificazione dichiarata: i contributi INPS di competenza dell'anno vengono
    dedotti nello stesso anno (la norma ammette la deduzione per cassa).
    """
    if profilo.regime not in REGIMI:
        raise ValueError(f"Regime non valido: {profilo.regime}")
    ricavi = max(0.0, ricavi)
    note: list[str] = []

    if profilo.regime == "forfettario":
        reddito = ricavi * profilo.coefficiente
        contrib = calcola_contributi(
            reddito,
            profilo.gestione,
            mesi_attivita=mesi_attivita,
            riduzione_35=profilo.riduzione_inps_35 and profilo.gestione != "separata",
            altra_copertura=profilo.altra_copertura,
            p=p,
        )
        imponibile = max(0.0, reddito - contrib.totale)
        startup_attiva = profilo.startup and anno_attivita <= p.anni_startup
        aliquota = p.aliq_forfettario_startup if startup_attiva else p.aliq_forfettario
        imposta = imponibile * aliquota
        if ricavi > p.soglia_uscita_immediata:
            note.append("Ricavi oltre 100.000 euro: uscita immediata dal forfettario (IRPEF dall'anno stesso).")
        elif ricavi > p.soglia_ricavi_forfettario:
            note.append("Ricavi oltre 85.000 euro: uscita dal forfettario dall'anno successivo.")
        if profilo.startup and anno_attivita > p.anni_startup:
            note.append("Oltre i 5 anni di attività: aliquota ordinaria del 15%.")
        return EsitoAnno(
            anno_attivita=anno_attivita,
            regime="forfettario",
            ricavi=ricavi,
            costi=0.0,
            reddito=reddito,
            inps_fissi=contrib.fissi,
            inps_variabili=contrib.variabili,
            imponibile=imponibile,
            aliquota_forfettaria=aliquota,
            imposta=imposta,
            note=tuple(note),
            costi_reali=ricavi * profilo.costi_pct,
        )

    # --- Ordinario semplificato (cassa) ---
    costi = ricavi * profilo.costi_pct
    reddito = ricavi - costi
    contrib = calcola_contributi(
        reddito,
        profilo.gestione,
        mesi_attivita=mesi_attivita,
        riduzione_35=False,
        altra_copertura=profilo.altra_copertura,
        p=p,
    )
    base_attivita = max(0.0, reddito - contrib.totale)
    altri = max(0.0, profilo.altri_redditi)
    totale_imponibile = base_attivita + altri
    irpef_netta_totale = max(
        0.0, irpef_lorda(totale_imponibile, p) - detrazione_autonomo(totale_imponibile, p)
    )
    irpef_attivita = max(0.0, irpef_netta_totale - irpef_lorda(altri, p))
    addizionali = base_attivita * (profilo.addizionale_regionale + profilo.addizionale_comunale)
    return EsitoAnno(
        anno_attivita=anno_attivita,
        regime="ordinario",
        ricavi=ricavi,
        costi=costi,
        reddito=reddito,
        inps_fissi=contrib.fissi,
        inps_variabili=contrib.variabili,
        imponibile=base_attivita,
        aliquota_forfettaria=0.0,
        imposta=irpef_attivita + addizionali,
        note=tuple(note),
        costi_reali=costi,
    )


def confronta_regimi(
    ricavi: float,
    profilo: Profilo,
    *,
    costi_pct_ordinario: float | None = None,
    anno_attivita: int = 1,
    mesi_attivita: int = 12,
    p: Parametri = PARAMETRI_2026,
) -> dict[str, EsitoAnno]:
    """Stesso fatturato calcolato nei due regimi, per capire quale conviene."""
    costi = profilo.costi_pct if costi_pct_ordinario is None else costi_pct_ordinario
    forf = replace(profilo, regime="forfettario", costi_pct=costi)
    ordi = replace(profilo, regime="ordinario", costi_pct=costi)
    return {
        "forfettario": calcola_anno(forf, ricavi, anno_attivita, mesi_attivita, p),
        "ordinario": calcola_anno(ordi, ricavi, anno_attivita, mesi_attivita, p),
    }
