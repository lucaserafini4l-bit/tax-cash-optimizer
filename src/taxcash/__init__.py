"""tax-cash-optimizer: calcolo tasse per regime fiscale e simulazione della liquidità accantonata."""

from .params import PARAMETRI_2026, Parametri
from .tasse import Profilo, EsitoAnno, calcola_anno, confronta_regimi
from .simulazione import Scenario, Risultato, simula

__all__ = [
    "PARAMETRI_2026",
    "Parametri",
    "Profilo",
    "EsitoAnno",
    "calcola_anno",
    "confronta_regimi",
    "Scenario",
    "Risultato",
    "simula",
]
