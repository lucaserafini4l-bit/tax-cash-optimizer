---
title: Metodo di calcolo - imposte, scadenze e conto deposito
description: Come il calcolatore calcola imposta sostitutiva, IRPEF, contributi INPS, saldo e acconti e il rendimento della liquidità accantonata.
---

# Metodo di calcolo

## 1. Imposte e contributi di competenza (per anno)

Forfettario:
- reddito = ricavi x coefficiente di redditività
- contributi INPS = f(reddito) secondo la gestione scelta
- imponibile = reddito - contributi
- imposta = imponibile x aliquota (5% nei primi 5 anni se nuova attività, altrimenti 15%)

Ordinario semplificato (cassa):
- reddito = ricavi - costi
- contributi INPS = f(reddito); imponibile attività = reddito - contributi
- IRPEF netta = IRPEF lorda(imponibile attività + altri redditi) - detrazione lavoro autonomo
- imposta attività = IRPEF netta - IRPEF lorda(altri redditi) + addizionali sull'imponibile attività
  (si attribuisce all'attività solo l'imposta marginale rispetto agli altri redditi)

Contributi INPS:
- Gestione Separata: aliquota x reddito.
- Artigiani e Commercianti: quota fissa sul minimale (4 rate) + quota variabile sul reddito oltre il minimale;
  nel primo anno il minimale è proporzionato ai mesi di attività.

## 2. Scadenzario

Per ogni anno k:
- acconti di k (solo da k = 2): imposta = 100% dell'imposta di k-1; contributi variabili = 80% di quelli di k-1
- saldo di k: pagato a giugno dell'anno solare successivo = dovuto di k - acconti già versati
- rate fisse INPS: maggio, agosto, novembre dell'anno e febbraio dell'anno dopo
- un saldo negativo diventa credito e riduce i versamenti successivi della stessa categoria

Effetto "primo anno": in k = 1 nessun acconto e nessun saldo fino a giugno dell'anno dopo; quel giorno si pagano
insieme saldo di k = 1 e primo acconto di k = 2 ("doppio carico"). La liquidità non versata resta disponibile
per circa 17 mesi (da gennaio del primo anno a giugno del secondo).

## 3. Accantonamento e conto deposito

- Accantonamento mensile = incasso x aliquota effettiva dell'anno (carico totale / ricavi), oppure una percentuale fissa.
- Ogni accantonamento viene abbinato al versamento che lo userà (FIFO: il versamento consuma le somme più vecchie).
- Per ciascun abbinamento si sceglie il prodotto con il tasso lordo più alto tra quelli con vincolo non superiore
  ai mesi che mancano al versamento (ipotesi: il vincolo si può dimensionare sulla scadenza).
- Interesse semplice = importo x tasso x mesi / 12; imposta 26% sugli interessi; bollo 0,20% x importo x mesi / 12.
- Vantaggio = interessi netti del deposito - interessi netti del conto corrente (tasso configurabile, default 0).
- Tasso di pareggio sul conto corrente a tasso zero: 0,20% / (1 - 26%) = 0,27% lordo.
- Se un versamento supera le somme accantonate disponibili, la parte scoperta viene segnalata.

## 4. Cosa non fa

- Non riduce l'imposta dovuta: gli interessi sono reddito di capitale tassato al 26% e compensano solo in parte il costo del versamento.
- Non verifica i requisiti di accesso al forfettario (cause di esclusione, soglia di 35.000 euro per i redditi da lavoro dipendente).
- Non tiene conto di IVA, IRAP, bolli sulle fatture, cassa previdenziale di categoria, detrazioni familiari.
- Applica i parametri 2026 a tutti gli anni simulati.
