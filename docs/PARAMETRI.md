---
title: Parametri fiscali 2026 e fonti - calcolatore tasse partita IVA
description: Aliquote IRPEF 2026, coefficienti forfettario, contributi INPS, acconti e regole del conto deposito usati dal calcolatore, con le fonti consultate.
---

# Parametri e fonti (riferimento 2026)

Tutti i valori sono in `src/taxcash/params.py` e si possono modificare. Fonti consultate il 19/11/2026.
Dove un valore non è stato riverificato è indicato esplicitamente.

## Imposte

| Parametro | Valore | Fonte |
|---|---|---|
| Scaglioni IRPEF 2026 | 23% fino a 28.000; 33% fino a 50.000; 43% oltre (L. 199/2025, art. 1 c. 3) | https://www.ecnews.it/lavoro/news-del-giorno/legge-bilancio-2026-revisione-aliquote-irpef/ , https://www.fiscozen.it/guide/quanto-si-risparmia-con-le-nuove-aliquote-irpef/ |
| Detrazione lavoro autonomo (art. 13 c. 5 TUIR) | 1.265 fino a 5.500; 500 + 765 x (28.000 - R) / 22.500 fino a 28.000; 500 x (50.000 - R) / 22.000 fino a 50.000; 0 oltre | https://www.informazionefiscale.it/Detrazioni-lavoro-autonomo-2024-importo-istruzioni-calcolo , https://www.money.it/detrazioni-IRPEF-lavoro-autonomo |
| Imposta sostitutiva forfettario | 15%; 5% per i primi 5 anni di una nuova attività | https://www.informazionefiscale.it/Regime-forfettario-2020-novita-partita-IVA , https://www.pmi.it/professioni/regole-e-compensi/350336/regime-forfettario-requisiti-limiti-cause-di-esclusione.html |
| Soglie forfettario | 85.000 di ricavi; uscita immediata oltre 100.000 | https://www.pmi.it/professioni/regole-e-compensi/350336/regime-forfettario-cosa-cambia.html |
| Coefficienti di redditività | 40%, 54%, 62%, 67%, 78%, 86% per gruppo ATECO (Allegato 4, L. 190/2014) | https://www.studiocataldi.it/articoli/33647-coefficiente-di-redditivita.asp , https://www.fiscozen.it/guide/coefficiente-redditivita-forfettario/ |
| Soglia reddito da lavoro dipendente/pensione per il forfettario | 35.000 per il 2026 (30.000 ordinaria negli anni successivi), riferita all'anno precedente; non vale se il rapporto è cessato | https://www.informazionefiscale.it/Regime-forfettario-2026-dipendenti-pensionati-limite-reddito , https://www.teamsystem.com/magazine/fatturazione-e-normativa/regime-forfettario-dipendenti-pensionati/ |
| Corrispondenza ATECO - coefficiente | per divisione/gruppo: alimentari 10-11 e commercio 45-47, alloggio e ristorazione 55-56 al 40%; ambulanti 47.82-47.89 al 54%; intermediari 46.1 al 62%; 01-03, 05-09, 12-33, 35-39, 49-53, 58-63, 77-82, 84, 90-99 al 67%; 64-66, 69-75, 85-88 al 78%; costruzioni 41-43 e immobiliare 68 all'86% | Allegato 4 L. 190/2014: https://www.fiscozen.it/guide/coefficiente-redditivita-forfettario/ , https://www.studiocataldi.it/articoli/33647-coefficiente-di-redditivita.asp |
| Costo del commercialista (ipotesi di confronto) | forfettario 600 l'anno (intervallo indicativo 400-1.100); ordinario 1.200 (intervallo indicativo 950-2.800): stime da preventivi pubblicati, non tariffe ufficiali | stime Fiscozen, da personalizzare |
| Addizionali regionale e comunale | 1,5% e 0,5% **valori illustrativi**, da personalizzare | non applicabile |

## Contributi INPS 2026

| Parametro | Valore | Fonte |
|---|---|---|
| Gestione Separata professionisti | 26,07% (24% se già assicurati altrove o pensionati) | https://www.informazionefiscale.it/Aliquote-gestione-separata-INPS-2026-importo-contributi , circ. INPS n. 8/2026 |
| Artigiani / Commercianti | aliquota 24% / 24,48%; minimale 18.808 | circ. INPS n. 14/2026, https://www.inps.it/it/it/inps-comunica/notizie/dettaglio-news-page.news.2026.02.gestioni-artigiani-e-commercianti-i-contributi-per-il-2026.html |
| Contributi fissi sul minimale | 4.521,36 (artigiani), 4.611,64 (commercianti) | https://www.soluzionetasse.com/contributi-artigiani-e-commercianti/ |
| Contributo maternità 7,44 / anno | ricavato per differenza: 4.611,64 - 18.808 x 24,48% = 7,44 | calcolo |
| Rate fisse | maggio, agosto, novembre, febbraio | https://www.quotidianopiu.it/dettaglio/14805771/artigiani-e-commercianti-aliquote-contributi-per-lanno-2026 |
| Riduzione 35% per forfettari | su domanda all'INPS (verificare i termini sul sito INPS) | https://www.informazionefiscale.it/riduzione-contributi-inps-forfettari-regime-agevolazioni |

Non modellati: massimale contributivo, aliquota aggiuntiva oltre la prima fascia di reddito, sconto del 50% per nuovi iscritti 2025 (L. 207/2024).
La riduzione del 35% è applicata alla quota IVS e non al contributo maternità: ipotesi non riverificata.

## Acconti e scadenze

| Parametro | Valore | Fonte |
|---|---|---|
| Rate acconto forfettari e soggetti ISA | 50% a giugno + 50% a novembre; ordinari 40% + 60% | https://www.partitaiva.it/secondo-acconto-novembre-2026/ |
| Primo anno | nessun acconto; saldo e primo acconto arrivano a giugno dell'anno dopo | https://www.pmi.it/?p=487691 , https://quickfisco.it/blog/calcolo-acconti-saldo-regime-forfettario-scadenze-esempi |
| Acconto unico in novembre sotto 257,52 | soglia di legge, coerente con la guida Fiscozen (258) | https://www.fiscozen.it/guide/come-si-pagano-le-tasse-nel-regime-forfettario/ |
| Nessun acconto sotto 51,65 | **non riverificato** in questa sessione | verificare |
| Acconto INPS 80% in due rate da 40% | **non riverificato** in questa sessione | verificare |

Nel 2026 i forfettari hanno avuto una proroga al 20 luglio per saldo e primo acconto: il parametro `mese_saldo_e_primo_acconto` permette di spostare la scadenza.

## Conto deposito

| Parametro | Valore | Fonte |
|---|---|---|
| Imposta sostitutiva sugli interessi | 26% | https://www.raisin.com/it-it/fisco-e-tasse/tassazione-conto-deposito/ |
| Imposta di bollo | 0,20% annuo sulla giacenza (tetto non previsto per le persone fisiche) | https://www.money.it/imposta-di-bollo-sul-conto-deposito-quanto-si-paga-e-come-si-calcola |
| Bollo conto corrente | 34,20 fisso; uguale nei due scenari, escluso dal confronto | https://quifinanza.it/fisco-tasse/interessi-attivi-tassazione-ritenute-obblighi-2026/1006478/ |
| Offerte di esempio | libero 2,5%; vincolo 12 mesi 4%; 24 mesi 4,75% | https://www.facile.it/conti/news/deposito-titoli-e-pagamento-imposta-di-bollo.html , https://www.businessonline.it/news/conti-deposito-giugno-2026-guadagni-rendimenti-pi-alti-diverse-offerte-attuali-attesa-rialzo-tassi_n85007.html |

Le offerte di esempio sono casi riportati da articoli di giugno-luglio 2026, non quotazioni attuali: vanno sostituite con quelle reali.
Alcune banche applicano un bollo minimo annuo di 34,20 sul deposito: non modellato.
