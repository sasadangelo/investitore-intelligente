---
title: Calcolatore BOT
description: Come usare il calcolatore per simulare acquisto e vendita di un BOT, con commissioni bancarie e tasse.
icon: bi-calculator
order: 2
---

# Calcolatore BOT

Dopo aver scelto il BOT da acquistare nel **[Catalogo BOT](/guides/catalogo)**, usa il **Calcolatore BOT** per sapere con esattezza i guadagni e i rendimenti lordi e netti.

Il calcolatore tiene conto di:
- Commissioni bancarie (diverse per asta e mercato secondario)
- Imposta di bollo
- Tassazione sul capital gain (solo per vendita anticipata sul MOT)

In questo modo conoscerai l'esatta misura dei soldi che metterai in tasca al rimborso a scadenza o alla vendita anticipata.

Se intendi vendere il titolo prima della scadenza, il calcolatore ti permette di simulare l'operazione con i dati di vendita per verificare la convenienza della transazione prima di eseguirla.

## Parametri di input

Per simulare un acquisto, o un acquisto seguito da una vendita anticipata, è necessario compilare i campi descritti di seguito. La maggior parte verrà prepopolata con valori di default in base alle scelte effettuate (BOT selezionato, mercato, profilo bancario), ma tutti i campi rimangono modificabili manualmente.

### BOT e mercato

- **BOT**: seleziona il BOT dal menu a tendina. I dati (ISIN, date, prezzo) si aggiornano automaticamente.
- **Mercato di acquisto**:
    - **Asta (mercato primario)**: acquisto direttamente all'emissione tramite la propria banca. Il prezzo
      viene precompilato con il prezzo di emissione.
    - **MOT (mercato secondario)**: acquisto sul mercato dopo l'emissione. Il prezzo viene precompilato
      con l'ultima quotazione disponibile.
- **Data acquisto**: per l'asta corrisponde alla data di regolamento o emissione; per il MOT si imposta automaticamente a oggi.
- **Prezzo acquisto**: prezzo in euro per ogni 100€ di valore nominale (es. `98.50` = 98,50€ ogni 100€). Per l'asta è il prezzo di emissione; per il MOT è l'ultimo prezzo.
- **Lotto nominale**: importo nominale in euro (multiplo di 100, es. `5000` = 50 BOT da €100 ciascuno).

### Profilo bancario

Seleziona la tua banca dal menu **Profilo bancario** per precompilare automaticamente i campi commissione in base al mercato selezionato e alla durata del BOT.

Se la tua banca non è presente, seleziona *"Inserisci commissioni manualmente"* e compila i campi.

### Commissioni acquisto

| Campo | Descrizione |
|---|---|
| **%** | Percentuale sul nominale (asta) o sul controvalore (MOT) |
| **Min (€)** | Commissione minima garantita (solo MOT) |
| **Max (€)** | Commissione massima applicata (solo MOT; lascia vuoto per nessun limite) |
| **Commissione fissa (€)** | Quota fissa aggiuntiva per ordine (es. spese dossier) |

### Vendita anticipata

Attiva il toggle **Vendita anticipata** per simulare la vendita prima della scadenza naturale.
Inserisci la data di vendita, il prezzo di vendita e le commissioni di vendita.

Se non si attiva, il calcolo assume il rimborso a scadenza a 100.

### Parametri fiscali

- **Periodicità bollo**: trimestrale (default) o annuale. Influenza il numero di periodi di imposta
  di bollo applicati durante il possesso.
- **Minusvalenze (€)**: eventuali perdite pregresse nel portafoglio che possono compensare il capital gain
  (solo per acquisti sul MOT).

## Nota sull'acquisto in Asta per BOT già emessi

Selezionare il mercato **Asta** per un BOT già emesso è utile principalmente per **analisi storiche**: ad esempio per ricostruire il rendimento che si sarebbe ottenuto acquistando a una determinata asta passata.

Per simulare un **acquisto all'asta futuro**, il flusso corretto è diverso:

1. Consulta il **[Calendario Aste MEF](/auctions/)**: date di emissione e scadenza dei prossimi BOT sono già pubblicate.
2. Vai alla pagina delle **[Previsioni](/auctions/forecast)** per ottenere il prezzo di emissione stimato del BOT prossimo all'emissione.
3. Inserisci manualmente nel calcolatore la data di emissione, scadenza e il prezzo stimato al posto del prezzo di emissione ufficiale.

In questo modo otterrai una simulazione prospettica realistica, pur con la consapevolezza che il prezzo definitivo verrà stabilito solo il giorno dell'asta.

## Risultati

Il calcolatore produce 4 sezioni di risultato:

### Acquisto

Mostra il costo totale dell'operazione:
- **Quantità**: `Lotto nominale / 100`
- **Importo secco**: `Quantità × Prezzo Acquisto`
- **Commissioni**: calcolate come percentuale sull'importo nominale (asta) o sull'importo secco (MOT); si applicano poi i valori minimo e massimo e si sommano gli eventuali costi fissi.
- **Disaggio pro-quota**: quota di disaggio per singolo BOT (100€ nominali). Per l'**asta** è l'intero disaggio (`100 − Prezzo emissione`); per il **MOT** è la quota proporzionale ai giorni rimanenti alla scadenza. Per i dettagli consulta la **[guida Approfondimenti sul Calcolatore BOT](/guides/calcolatore-approfondimenti)**.
- **Imposta disaggio pro-quota**: imposta per singolo BOT, pari a `Disaggio pro-quota × 12,5%`.
- **Imposta disaggio**: imposta totale anticipata, pari a `Imposta disaggio pro-quota × Quantità`.
- **Totale pagato**: somma di importo secco, commissioni e imposta disaggio.

### Vendita / Rimborso

Mostra il ricavato dell'operazione:
- **Importo secco**: controvalore alla vendita o al rimborso
- **Commissioni** di vendita: calcolate con la stessa logica dell'acquisto (zero se rimborso a scadenza).
- **Imposta disaggio rimborsata**: per i dettagli sul calcolo consulta la **[guida Approfondimenti sul Calcolatore BOT](/guides/calcolatore-approfondimenti)**.
- **Totale ricevuto**: somma di importo secco, al netto di commissioni e imposta disaggio.

### Capital Gain (solo MOT)

Per acquisti sul mercato secondario si calcola la plusvalenza o minusvalenza:
- **Prezzo teorico di acquisto/vendita**: il prezzo di carico/scarico depurato del rateo disaggio fiscale
- **Imponibile** e **imposta capital gain** (26%)
- Se presente la minusvalenza pregressa, viene dedotta dall'imponibile

### Imposta di Bollo

L'imposta di bollo è pari allo **0,2% annuo** del controvalore di mercato, applicata per ogni
periodo di detenzione (trimestrale o annuale).

### Riepilogo

- **Guadagno lordo**: importo secco ricevuto − importo secco pagato
- **Guadagno netto**: al netto di tutte le imposte e commissioni
- **Rendimento semplice**: guadagno / capitale × (YEARFRAC ACT/ACT)⁻¹ — base lordo = importo secco, base netti = totale pagato
- **Rendimento composto (TIR/XIRR)**: (incasso finale / capitale)^(365/giorni) − 1 — stesso criterio di Excel XIRR

## Esempio completo

Di seguito un esempio reale con tutti i campi compilati, per capire cosa produce il calcolatore.

**BOT Feb24 A** — acquistato sul MOT il 01/03/2023, portato a scadenza il 14/02/2024.

| Parametro | Valore |
|---|---|
| Mercato | MOT |
| Data emissione | 14/02/2023 |
| Data scadenza | 14/02/2024 |
| Prezzo emissione | 96,877 |
| Data acquisto (regolamento) | 01/03/2023 |
| Prezzo acquisto | 96,846 |
| Lotto nominale | 5.000€ (50 BOT) |
| Commissioni acquisto | 0,24% — min 3€ — costi fissi 3,50€ |
| Vendita anticipata | No (rimborso a scadenza) |

### Acquisto

| Campo | Formula | Valore |
|---|---|---|
| Quantità | 5.000 / 100 | 50 |
| Importo secco | 50 × 96,846 | 4.842,30€ |
| Commissioni | max(4.842,30 × 0,24%, 3€) | 11,62€ |
| Commissioni fisse | — | 3,50€ |
| Disaggio pro-quota | 100 − 97,005 | 2,9950 |
| Imposta disaggio | 2,9950 × 12,5% × 50 | 18,72€ |
| **Totale pagato** | 4.842,30 + 11,62 + 3,50 + 18,72 | **4.876,14€** |

### Rimborso a scadenza

| Campo | Formula | Valore |
|---|---|---|
| Importo secco | 50 × 100 | 5.000,00€ |
| Commissioni | — | 0,00€ |
| Imposta disaggio rimborsata | (100 − 97,005) × 12,5% × 50 | 18,72€ |
| **Totale ricevuto** | 5.000,00 + 0 + 18,72 | **5.018,72€** |

### Capital Gain (MOT)

| Campo | Formula | Valore |
|---|---|---|
| Prezzo teorico acquisto | 96,877 + 3,123 × (15/365) | 97,00534 |
| Prezzo teorico vendita (scadenza) | 96,877 + 3,123 × (365/365) | 100,00000 |
| Prezzo di carico | 96,846 + (11,62+3,50)/50 − (97,00534−96,877) | 97,02014 |
| Prezzo di scarico | 100 − 0/50 − (100−96,877) | 96,87700 |
| Plus/Minus valenza (per BOT) | 96,87700 − 97,02014 | −0,14314 |
| Plus/Minus realizzata | −0,143 × 50 | −7,15€ |
| Riduzione imponibile TdS (48,08%) | −7,15 × 48,08% | −3,44€ |
| Minus valenza da zainetto | 7,15 × 48,08% | 3,44€ |

> Il prezzo di scarico coincide con il prezzo di emissione (96,877) perché alla scadenza l'intero disaggio è stato maturato e viene sottratto, lasciando esattamente il valore di emissione (al netto delle commissioni di vendita, che in questo caso sono zero).

### Riepilogo

| Campo | Formula | Valore |
|---|---|---|
| Guadagno lordo | 5.000,00 − 4.842,30 | 157,70€ |
| Guadagno netto (pre-bollo) | 157,70 − 18,72 (imp. disaggio) − 15,12 (comm.) | 123,86€ |
| Guadagno netto | 123,86 − 9,84 (imposta di bollo) | 114,02€ |

| Campo | Semplice | Composto |
|---|---|---|
| Rendimento lordo | 3,396% | 3,399% |
| Rendimento netto (pre-bollo) | 2,649% | 2,650% |
| Rendimento netto | 2,439% | 2,440% |

## Consigli pratici

- Confronta lo stesso BOT acquistato all'**asta** vs sul **MOT** per vedere quale conviene di più.
- Cambia il profilo bancario per vedere l'impatto delle commissioni sul rendimento netto.
- Usa il campo **minusvalenze** se hai perdite pregresse da compensare: abbatte l'imposta capital gain.
