"""Contributi previdenziali INPS (Gestione Separata, Artigiani, Commercianti)."""

from __future__ import annotations

from dataclasses import dataclass

from .params import Parametri, PARAMETRI_2026

GESTIONI = ("separata", "commercianti", "artigiani")


@dataclass(frozen=True)
class Contributi:
    fissi: float       # quota sul minimale (pagata a rate fisse), solo artigiani/commercianti
    variabili: float   # quota sul reddito eccedente il minimale (saldo e acconti)

    @property
    def totale(self) -> float:
        return self.fissi + self.variabili


def calcola_contributi(
    reddito: float,
    gestione: str,
    *,
    mesi_attivita: int = 12,
    riduzione_35: bool = False,
    altra_copertura: bool = False,
    p: Parametri = PARAMETRI_2026,
) -> Contributi:
    """Contributi INPS dovuti sul reddito d'impresa/professionale dell'anno.

    reddito: base imponibile previdenziale (nel forfettario è il reddito dopo il
    coefficiente di redditività, prima della deduzione dei contributi).
    Semplificazioni: nessun massimale, nessuna aliquota aggiuntiva oltre la prima
    fascia, contributo di maternità non soggetto a riduzione.
    """
    if gestione not in GESTIONI:
        raise ValueError(f"Gestione INPS non valida: {gestione}")
    reddito = max(0.0, reddito)

    if gestione == "separata":
        aliq = p.gs_aliq_altra_copertura if altra_copertura else p.gs_aliq_professionisti
        return Contributi(fissi=0.0, variabili=reddito * aliq)

    aliq = p.aliq_commercianti if gestione == "commercianti" else p.aliq_artigiani
    fattore_mesi = mesi_attivita / 12.0
    minimale = p.minimale_reddito * fattore_mesi
    fattore_riduzione = (1.0 - p.riduzione_forfettari) if riduzione_35 else 1.0

    fissi = minimale * aliq * fattore_riduzione + p.contributo_maternita_annuo * fattore_mesi
    variabili = max(0.0, reddito - minimale) * aliq * fattore_riduzione
    return Contributi(fissi=fissi, variabili=variabili)
