"""Genera docs/ESEMPI.md eseguendo alcuni scenari tipici. Uso: python scripts/genera_esempi.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from taxcash import Profilo, Scenario, simula  # noqa: E402

SCENARI = [
    ("Consulente (forfettario 78%, Gestione Separata, 5%)", "30.000",
     Profilo(regime="forfettario", gestione="separata", coefficiente=0.78), 30_000),
    ("E-commerce (forfettario 40%, commerciante, 5%)", "30.000",
     Profilo(regime="forfettario", gestione="commercianti", coefficiente=0.40), 30_000),
    ("E-commerce (forfettario 40%, commerciante, 5%, riduzione INPS 35%)", "30.000",
     Profilo(regime="forfettario", gestione="commercianti", coefficiente=0.40, riduzione_inps_35=True), 30_000),
    ("E-commerce (forfettario 40%, commerciante, 5%)", "70.000",
     Profilo(regime="forfettario", gestione="commercianti", coefficiente=0.40), 70_000),
    ("Ordinario (commerciante, costi 20%)", "50.000",
     Profilo(regime="ordinario", gestione="commercianti", costi_pct=0.20), 50_000),
]


def euro(x: float) -> str:
    return f"{x:,.0f}".replace(",", ".")


def pct(x: float, dec: int) -> str:
    return f"{x * 100:.{dec}f}%".replace(".", ",")


righe = [
    "---",
    "title: Esempi di simulazione partita IVA - forfettario e ordinario",
    "description: Scenari tipici di partita IVA a 4 anni: carico fiscale, versamenti del primo anno e interessi netti su conto deposito.",
    "---",
    "",
    "# Esempi di simulazione",
    "",
    "Generato da `scripts/genera_esempi.py`: 4 anni di attività dal gennaio 2027, fatturato costante,",
    "accantonamento automatico, offerte di deposito di esempio (libero 2,5%, 12 mesi 4%, 24 mesi 4,75%).",
    "Valori in euro. Il vantaggio è l'interesse netto (dopo 26% e bollo 0,20%) rispetto al conto corrente a tasso zero.",
    "",
    "| Scenario | Fatturato annuo | Carico 4 anni | Pressione | Versato nel 1° anno | Riserva a fine 1° anno | Interessi netti | Interessi / carico |",
    "|---|---:|---:|---:|---:|---:|---:|---:|",
]
for nome, label, prof, ricavi in SCENARI:
    r = simula(prof, Scenario(anno_inizio=2027, anni=4, ricavi_annui_regime=ricavi))
    primo = sum(pg.importo for pg in r.pagamenti if pg.anno == 2027)
    k = r.kpi
    righe.append(
        f"| {nome} | {label} | {euro(k['carico_totale'])} | {pct(k['pressione_effettiva'], 1)} | "
        f"{euro(primo)} | {euro(k['riserva_fine_primo_anno'])} | {euro(k['interessi_netti'])} | "
        f"{pct(k['beneficio_su_carico_totale'], 2)} |"
    )
righe += [
    "",
    "Lettura: il primo anno non si versano acconti né saldo, quindi la riserva si accumula e matura interessi fino",
    "al versamento dell'anno successivo. Gli interessi netti compensano una frazione piccola del carico fiscale:",
    "il conto deposito non riduce l'imposta dovuta, migliora marginalmente la liquidità.",
    "",
]
Path(__file__).resolve().parent.parent.joinpath("docs", "ESEMPI.md").write_text("\n".join(righe), encoding="utf-8")
print("\n".join(righe))
