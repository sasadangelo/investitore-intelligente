---
title: Calcolatore BOT
description: Come usare il calcolatore per simulare acquisto e vendita di un BOT, con commissioni bancarie e tasse.
icon: bi-calculator
order: 2
---

# Calcolatore BOT

Il **Calcolatore BOT** permette di simulare l'acquisto (e l'eventuale vendita anticipata) di un BOT,
tenendo conto di commissioni bancarie, imposta di bollo e tassazione sul capital gain.

## Parametri di input

### BOT e mercato

- **BOT**: seleziona il BOT dal menu a tendina. I dati (ISIN, date, prezzo) si aggiornano automaticamente.
- **Mercato di acquisto**:
  - **Asta (mercato primario)**: acquisto direttamente all'emissione tramite la propria banca. Il prezzo
    viene precompilato con il prezzo di emissione.
  - **MOT (mercato secondario)**: acquisto sul mercato dopo l'emissione. Il prezzo viene precompilato
    con l'ultima quotazione disponibile.
- **Data acquisto**: per l'asta corrisponde alla data di regolamento dell'emissione; per il MOT
  si imposta automaticamente a oggi.
- **Prezzo acquisto**: espresso in percentuale del valore nominale (es. `98.50` = 98,50%).
- **Lotto nominale**: importo nominale in euro (multiplo di 100, es. `5000` = 50 BOT da €100 ciascuno).

### Profilo bancario

Seleziona la tua banca dal menu **Profilo bancario** per precompilare automaticamente i campi
commissione in base al mercato selezionato e alla durata del BOT.

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

## Risultati

Il calcolatore produce 4 sezioni di risultato:

### Acquisto

Mostra il costo totale dell'operazione:
- **Importo secco**: `quantità × prezzo acquisto / 100`
- **Commissioni** e **commissioni fisse**
- **Disaggio lordo per BOT** e **imposta disaggio** (12,5% del disaggio pro-quota)
- **Totale pagato**: tutto compreso

### Vendita / Rimborso

Mostra il ricavato dell'operazione:
- **Importo secco**: controvalore alla vendita o al rimborso
- **Commissioni** di vendita (zero se rimborso a scadenza)
- **Imposta disaggio rimborsata** (pro-quota se vendita anticipata)
- **Totale ricevuto**

### Capital Gain (solo MOT)

Per acquisti sul mercato secondario si calcola la plusvalenza o minusvalenza:
- **Prezzo teorico di acquisto/vendita**: il prezzo di carico/scarico depurato del rateo disaggio fiscale
- **Imponibile** e **imposta capital gain** (26%)
- Se presente la minusvalenza pregressa, viene dedotta dall'imponibile

### Imposta di Bollo

L'imposta di bollo è pari allo **0,2% annuo** del controvalore di mercato, applicata per ogni
periodo di detenzione (trimestrale o annuale).

### Riepilogo

- **Guadagno lordo**: ricevuto − pagato
- **Guadagno netto**: al netto di tutte le imposte e commissioni
- **Rendimento semplice lordo/netto**: guadagno / totale pagato
- **Rendimento composto lordo/netto**: tasso annualizzato con capitalizzazione composta

## Consigli pratici

- Confronta lo stesso BOT acquistato all'**asta** vs sul **MOT** per vedere quale conviene di più.
- Cambia il profilo bancario per vedere l'impatto delle commissioni sul rendimento netto.
- Usa il campo **minusvalenze** se hai perdite pregresse da compensare: abbatte l'imposta capital gain.
