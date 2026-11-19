# Tax Cash Optimizer

Strumento per partite IVA italiane che calcola imposte e contributi in base al regime fiscale, costruisce lo scadenzario
dei versamenti e simula quanto rende la liquidità accantonata per pagarli se viene tenuta su un conto deposito invece che
sul conto corrente. Parametri fiscali 2026.

> Strumento di simulazione a scopo informativo. Non è consulenza fiscale: verificare i risultati con un commercialista.

## Perché esiste

In Italia nel **primo anno di attività non si versano né acconti né saldo**. Il saldo del primo anno e il primo acconto del
secondo si pagano insieme a giugno dell'anno dopo (il "doppio carico"). Nel frattempo gli incassi accantonati restano
fermi per circa 17 mesi: tenerli su un conto deposito produce interessi.

Due precisazioni importanti, emerse dai numeri del modello:

1. Gli interessi **non riducono l'imposta dovuta**. Sono un reddito di capitale tassato al 26% (più bollo 0,20% sulla giacenza):
   compensano una piccola parte del carico fiscale, non lo abbattono.
2. L'ordine di grandezza è contenuto: con le offerte di esempio gli interessi netti valgono tra lo 0,4% e l'1% del carico
   fiscale totale (tabella sotto). Il vantaggio principale dello strumento è sapere **quanto accantonare e quando serve
   la cassa**, non il rendimento.

## Cosa calcola

- Regime **forfettario** (coefficienti di redditività, aliquota 5% per 5 anni o 15%, soglie 85.000 / 100.000) e **ordinario semplificato**
  (IRPEF 2026 a 23/33/43%, detrazione da lavoro autonomo, addizionali, altri redditi).
- Contributi **INPS**: Gestione Separata, Artigiani, Commercianti (minimale, rate fisse, quota variabile, riduzione 35% per i forfettari).
- **Scadenzario**: saldo, acconti con metodo storico, rate fisse INPS, crediti da acconti in eccesso.
- **Liquidità**: accantonamento mensile, riserva nel tempo, abbinamento di ogni somma alla scadenza che la userà,
  scelta del prodotto (libero o vincolato) compatibile con il tempo disponibile, interessi netti e confronto con il conto corrente.
- **Confronto forfettario / ordinario** a diversi livelli di fatturato.

## Esempi (4 anni dal gennaio 2027, fatturato costante)

| Scenario | Fatturato annuo | Carico 4 anni | Pressione | Versato nel 1° anno | Riserva a fine 1° anno | Interessi netti | Interessi / carico |
|---|---:|---:|---:|---:|---:|---:|---:|
| Consulente (forfettario 78%, Gestione Separata, 5%) | 30.000 | 27.861 | 23,2% | 0 | 6.965 | 262 | 0,94% |
| E-commerce (forfettario 40%, commerciante, 5%) | 30.000 | 19.924 | 16,6% | 3.459 | 1.522 | 85 | 0,43% |
| E-commerce (forfettario 40%, commerciante, 5%, riduzione INPS 35%) | 30.000 | 13.801 | 11,5% | 2.250 | 1.200 | 60 | 0,44% |
| E-commerce (forfettario 40%, commerciante, 5%) | 70.000 | 31.675 | 11,3% | 3.459 | 4.460 | 173 | 0,55% |
| Ordinario (commerciante, costi 20%) | 50.000 | 68.479 | 34,2% | 3.459 | 13.661 | 479 | 0,70% |

Importi in euro. Offerte di deposito di esempio: libero 2,5%, vincolo 12 mesi 4%, 24 mesi 4,75% (da sostituire con quelle reali).
Riprodurre con `python scripts/genera_esempi.py`.

## Installazione e uso

```bash
git clone <url-del-repo>
cd tax-cash-optimizer
pip install -r requirements.txt
streamlit run app.py
```

Nell'app: profilo fiscale, scenario, offerte del conto deposito nella barra laterale; risultati in cinque schede
(riepilogo, scadenzario, liquidità e conto deposito, confronto regimi, note e limiti).

### Come libreria

```python
from taxcash import Profilo, Scenario, simula

profilo = Profilo(regime="forfettario", gestione="commercianti", coefficiente=0.40, startup=True)
scenario = Scenario(anno_inizio=2027, anni=4, ricavi_annui_regime=30_000, crescita_annua=0.05)
r = simula(profilo, scenario)

print(r.kpi["carico_totale"], r.kpi["interessi_netti"])
print(r.timeline.head())      # riserva e versamenti mese per mese
for pg in r.pagamenti[:5]:    # scadenzario
    print(pg.periodo, pg.voce, round(pg.importo, 2))
```

## Struttura

```
app.py                     interfaccia Streamlit
src/taxcash/params.py      parametri 2026 e coefficienti (modificabili)
src/taxcash/tasse.py       IRPEF, forfettario, ordinario, confronto regimi
src/taxcash/inps.py        contributi INPS
src/taxcash/scadenzario.py saldo, acconti, rate fisse
src/taxcash/deposito.py    interessi netti, tasso di pareggio, scelta del prodotto
src/taxcash/simulazione.py simulazione mensile e KPI
tests/                     test con valori calcolati a mano
docs/                      PARAMETRI.md (fonti), METODO.md, ESEMPI.md
```

## Test

```bash
python -m pytest -q
```

I test verificano scaglioni IRPEF, detrazioni, contributi minimali 2026, calcolo forfettario e ordinario con valori
calcolati a mano, la regola del primo anno senza versamenti, il doppio carico del secondo anno, la conservazione degli importi
tra accantonamenti e versamenti e le formule del conto deposito.

## Limiti noti

- Parametri 2026 applicati a tutti gli anni; contributi dedotti per competenza e non per cassa.
- Addizionali regionale e comunale come valori illustrativi (1,5% e 0,5%): da personalizzare.
- Non modellati: massimale INPS, aliquota aggiuntiva oltre la prima fascia, IRAP, IVA, cause di esclusione dal forfettario.
- Due soglie sugli acconti (51,65 euro e acconto INPS 80%) non sono state riverificate: vedi `docs/PARAMETRI.md`.
- Le scadenze sono mensili; il calendario reale può slittare per weekend o proroghe.

## Licenza

MIT
