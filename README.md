# Calcolatore tasse partita IVA 2026: forfettario o ordinario, quanto accantonare e quando pagare

![tests](https://github.com/lucaserafini4l-bit/tax-cash-optimizer/actions/workflows/tests.yml/badge.svg)
![licenza MIT](https://img.shields.io/badge/licenza-MIT-green)
![anno fiscale](https://img.shields.io/badge/parametri-2026-blue)

Strumento gratuito e open source per chi sta **aprendo la partita IVA** (o l'ha appena aperta) e vuole rispondere a tre domande prima che arrivi la prima scadenza:

1. **Quanto devo mettere da parte** ogni mese per tasse e contributi INPS?
2. **Forfettario o ordinario**: quale regime mi costa meno?
3. **Quando pago** saldo e acconti, e quanto pesa il famoso "doppio carico" del secondo anno?

In più simula quanto rende la liquidità accantonata se la tieni su un **conto deposito** invece che sul conto corrente.

> Strumento di simulazione a scopo informativo, non consulenza fiscale. Parametri 2026: controlla sempre i risultati con un commercialista.

## Perché ti serve

Chi apre la partita IVA si trova davanti sempre lo stesso problema: **nel primo anno sembra che non si paghi nulla**, poi arriva una scadenza che pesa molto più di quanto si pensasse.

Esempio dal modello, consulente in regime forfettario con 30.000 euro di ricavi l'anno (coefficiente 78%, Gestione Separata, aliquota 5%):

| Quando | Cosa si versa | Importo |
|---|---|---:|
| Anno 1 (2027) | nessun acconto, nessun saldo | 0 euro |
| Giugno anno 2 | saldo anno 1 + primo acconto anno 2, imposta e INPS | 9.838 euro |
| Novembre anno 2 | secondo acconto | 2.873 euro |

Chi ha speso tutto l'incassato del primo anno si ritrova senza i 9.838 euro di giugno. Con questo strumento sai **già dal primo mese** quanto accantonare (qui il 23,2% di ogni incasso) e quando serve la cassa.

## Cosa ottieni

| Vantaggio | Come |
|---|---|
| Sai quanto accantonare | percentuale effettiva di imposte e contributi su ogni incasso, per il tuo profilo |
| Scegli il regime giusto | confronto forfettario / ordinario a diversi livelli di fatturato |
| Non hai sorprese a giugno e novembre | scadenzario di saldo, acconti e rate fisse INPS, mese per mese |
| Vedi le leve che fanno davvero risparmiare | aliquota 5% per i primi 5 anni, riduzione INPS 35%, scelta del regime |
| Valuti il conto deposito con numeri reali | interessi netti dopo imposta 26% e bollo 0,20%, confronto con il conto corrente |

## Come risparmiare davvero con la partita IVA (numeri del modello)

| Leva | Effetto nell'esempio | Condizioni |
|---|---|---|
| Aliquota 5% per i primi 5 anni (forfettario, nuova attività) | circa 1.730 euro l'anno in meno a 30.000 euro di ricavi (consulente: 865 euro contro 2.595 al 15%) | requisiti del forfettario e attività realmente nuova |
| Riduzione INPS del 35% (forfettari artigiani e commercianti) | e-commerce da 30.000 euro: carico di 4 anni 13.801 euro contro 19.924, circa 1.530 euro l'anno | richiesta all'INPS, solo Artigiani e Commercianti |
| Regime forfettario invece di ordinario | consulente a 30.000 euro con costi al 10%: carico 6.965 euro contro 11.256 | ricavi sotto 85.000 euro e assenza di cause di esclusione |
| Conto deposito sulla liquidità accantonata | interessi netti pari a circa lo 0,4%-0,9% del carico fiscale totale | tasso, vincoli e bollo della banca |

Il conto deposito è la leva più piccola: **gli interessi non riducono le tasse dovute**, sono un reddito tassato al 26%. Le prime tre leve contano molto di più. Lo strumento serve proprio a mostrartele insieme.

## Domande frequenti

**Nel primo anno di partita IVA si pagano le tasse?**
Non nell'anno stesso, ma si pagano dopo. Il saldo del primo anno e il primo acconto del secondo si versano insieme a giugno dell'anno successivo. Chi è artigiano o commerciante paga però già nel primo anno le rate fisse INPS sul minimale (nel modello 3.459 euro su e-commerce da 30.000 euro).

**Quanto devo accantonare per le tasse con la partita IVA?**
Dipende da regime e gestione INPS. Nel modello, in forfettario al 5% con Gestione Separata il carico è il 23,2% dei ricavi; dopo i 5 anni, con aliquota al 15%, sale al 29,0%. Un e-commerce commerciante in forfettario ha il 16,6% a 30.000 euro di ricavi ma il 23,9% a 20.000, perché i contributi fissi pesano di più sui redditi bassi.

**Forfettario o ordinario, quale conviene?**
Nei casi simulati il forfettario costa meno (guida: [forfettario o ordinario](docs/forfettario-o-ordinario.md)), ma dipende da ricavi, costi reali e requisiti. Il confronto nell'app usa i tuoi numeri.

**Quando si pagano saldo e acconti?**
In generale 30 giugno (saldo e primo acconto) e 30 novembre (secondo acconto); le rate fisse INPS di artigiani e commercianti a maggio, agosto, novembre e febbraio. Il calendario reale può slittare per weekend o proroghe.

**Conviene mettere i soldi delle tasse su un conto deposito?**
Conviene se il tasso lordo supera lo 0,27% (pareggio rispetto a un conto corrente a tasso zero), ma il guadagno è piccolo: un deposito al 4% lordo rende il 2,76% netto, circa 192 euro all'anno su 6.965 euro tenuti fermi. Vedi [la guida](docs/conto-deposito-tasse-partita-iva.md).

**Gli interessi del conto deposito riducono le imposte?**
No. Sono tassati al 26% e il bollo è lo 0,20% annuo: compensano in parte il versamento, non lo abbassano.

**Devo saper programmare?**
Basta saper installare Python e lanciare due comandi (sotto). L'interfaccia è un'app web in locale, senza codice.

**Serve ancora il commercialista?**
Sì: lo strumento stima e confronta, non presenta dichiarazioni e non verifica i requisiti di accesso al forfettario.

## Come si usa

Serve Python 3.10 o superiore ([download](https://www.python.org/downloads/)).

```bash
git clone https://github.com/lucaserafini4l-bit/tax-cash-optimizer.git
cd tax-cash-optimizer
pip install -r requirements.txt
streamlit run app.py
```

Si apre il browser con l'app: scegli regime, gestione INPS, attività e fatturato nella barra laterale; leggi il risultato in cinque schede (riepilogo, scadenzario, liquidità e conto deposito, confronto regimi, note e limiti).

### Come libreria Python

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

## Cosa calcola

- Regime **forfettario** (coefficienti di redditività, aliquota 5% o 15%, soglie 85.000 / 100.000 euro) e **ordinario semplificato** (IRPEF 2026 al 23/33/43%, detrazione da lavoro autonomo, addizionali, altri redditi).
- Contributi **INPS**: Gestione Separata, Artigiani, Commercianti (minimale, rate fisse, quota variabile, riduzione 35% per i forfettari).
- **Scadenzario**: saldo, acconti con metodo storico, rate fisse INPS, crediti da acconti in eccesso.
- **Liquidità**: accantonamento mensile, riserva nel tempo, abbinamento di ogni somma alla scadenza che la userà, scelta del prodotto (libero o vincolato) compatibile con il tempo disponibile, interessi netti e confronto con il conto corrente.

## Guide

- [Primo anno di partita IVA: si pagano le tasse?](docs/primo-anno-partita-iva-tasse.md)
- [Quanto accantonare per le tasse](docs/quanto-accantonare-tasse-partita-iva.md)
- [Forfettario o ordinario: quale conviene](docs/forfettario-o-ordinario.md)
- [Conto deposito e tasse della partita IVA](docs/conto-deposito-tasse-partita-iva.md)
- [Parametri e fonti](docs/PARAMETRI.md), [metodo di calcolo](docs/METODO.md), [esempi](docs/ESEMPI.md)

## Struttura del progetto

```
app.py                     interfaccia Streamlit
src/taxcash/params.py      parametri 2026 e coefficienti (modificabili)
src/taxcash/tasse.py       IRPEF, forfettario, ordinario, confronto regimi
src/taxcash/inps.py        contributi INPS
src/taxcash/scadenzario.py saldo, acconti, rate fisse
src/taxcash/deposito.py    interessi netti, tasso di pareggio, scelta del prodotto
src/taxcash/simulazione.py simulazione mensile e KPI
tests/                     34 test con valori calcolati a mano
docs/                      guide, parametri e fonti, metodo, esempi
```

Test: `python -m pytest -q`.

## Limiti noti

- Parametri 2026 applicati a tutti gli anni; contributi dedotti per competenza e non per cassa.
- Addizionali regionale e comunale come valori illustrativi (1,5% e 0,5%): da personalizzare.
- Non modellati: massimale INPS, aliquota aggiuntiva oltre la prima fascia, IRAP, IVA, cause di esclusione dal forfettario.
- Due soglie sugli acconti (51,65 euro e acconto INPS 80%) non sono state riverificate: vedi [parametri e fonti](docs/PARAMETRI.md).
- Offerte di conto deposito di esempio (giugno-luglio 2026): sostituirle con quelle reali.

## Contribuire

Segnalazioni di errori nei parametri fiscali e miglioramenti sono benvenuti tramite issue e pull request.

## Licenza

MIT
