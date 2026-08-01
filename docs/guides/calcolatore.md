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
- **Data regolamento**: per l'asta corrisponde alla data di regolamento o emissione; per il MOT si imposta automaticamente a oggi ma va inserito la data di acquisto del BOT + 2gg.
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
- **Imposta disaggio**: il calcolo è più articolato — per i dettagli consulta la **[guida Approfondimenti sul Calcolatore BOT](/guides/calcolatore-approfondimenti)**.
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

- **Guadagno lordo**: ricevuto − pagato
- **Guadagno netto**: al netto di tutte le imposte e commissioni
- **Rendimento semplice lordo/netto**: guadagno / totale pagato
- **Rendimento composto lordo/netto**: tasso annualizzato con capitalizzazione composta

## Consigli pratici

- Confronta lo stesso BOT acquistato all'**asta** vs sul **MOT** per vedere quale conviene di più.
- Cambia il profilo bancario per vedere l'impatto delle commissioni sul rendimento netto.
- Usa il campo **minusvalenze** se hai perdite pregresse da compensare: abbatte l'imposta capital gain.
