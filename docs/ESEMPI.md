---
title: Esempi di simulazione partita IVA - forfettario e ordinario
description: Scenari tipici di partita IVA a 4 anni: carico fiscale, versamenti del primo anno e interessi netti su conto deposito.
---

# Esempi di simulazione

Generato da `scripts/genera_esempi.py`: 4 anni di attività dal gennaio 2027, fatturato costante,
accantonamento automatico, offerte di deposito di esempio (libero 2,5%, 12 mesi 4%, 24 mesi 4,75%).
Valori in euro. Il vantaggio è l'interesse netto (dopo 26% e bollo 0,20%) rispetto al conto corrente a tasso zero.

| Scenario | Fatturato annuo | Carico 4 anni | Pressione | Versato nel 1° anno | Riserva a fine 1° anno | Interessi netti | Interessi / carico |
|---|---:|---:|---:|---:|---:|---:|---:|
| Consulente (forfettario 78%, Gestione Separata, 5%) | 30.000 | 27.861 | 23,2% | 0 | 6.965 | 262 | 0,94% |
| E-commerce (forfettario 40%, commerciante, 5%) | 30.000 | 19.924 | 16,6% | 3.459 | 1.522 | 85 | 0,43% |
| E-commerce (forfettario 40%, commerciante, 5%, riduzione INPS 35%) | 30.000 | 13.801 | 11,5% | 2.250 | 1.200 | 60 | 0,44% |
| E-commerce (forfettario 40%, commerciante, 5%) | 70.000 | 31.675 | 11,3% | 3.459 | 4.460 | 173 | 0,55% |
| Ordinario (commerciante, costi 20%) | 50.000 | 68.479 | 34,2% | 3.459 | 13.661 | 479 | 0,70% |

Lettura: il primo anno non si versano acconti né saldo, quindi la riserva si accumula e matura interessi fino
al versamento dell'anno successivo. Gli interessi netti compensano una frazione piccola del carico fiscale:
il conto deposito non riduce l'imposta dovuta, migliora marginalmente la liquidità.
