---
title: Previsione Prezzo Emissione BOT
description: Come viene stimata la previsione del prezzo di emissione e il rendimento atteso per i BOT non ancora emessi.
icon: bi-graph-up-arrow
order: 4
---

# Previsione Prezzo Emissione BOT

La pagina **Previsione** stima il prezzo di emissione e il rendimento atteso per i BOT non ancora emessi, utilizzando le quotazioni di mercato dei BOT della stessa durata già in circolazione.

## Obiettivo

Prima di un'asta, l'investitore non conosce il prezzo al quale il MEF emetterà il BOT. Questo strumento fornisce una **stima indicativa** basata sulle condizioni di mercato correnti, utile per decidere se partecipare all'asta o acquistare sul mercato secondario.

## Metodo di calcolo

### Passo 1 — Selezione dei BOT di riferimento

Per ogni asta futura vengono selezionati tutti i BOT attivi della **stessa categoria di durata**:

- **Annuali**: BOT con durata totale ≥ 271 giorni
- **Semestrali**: BOT con durata totale ≤ 270 giorni

Sono inclusi solo i BOT con una **quotazione di mercato (last price) disponibile**. Sono richiesti almeno **2 BOT** per calcolare la previsione.

### Passo 2 — Rendimento lordo implicito

Per ciascun BOT di riferimento si calcola il **rendimento lordo annualizzato** implicito nel prezzo di mercato corrente:

```
r_i = (100 / last_price_i) ^ (365 / giorni_residui_i) − 1
```

Dove `giorni_residui_i` è il numero di giorni che mancano alla scadenza del BOT *i* da oggi.

### Passo 3 — Media ponderata

I rendimenti vengono combinati con una **media ponderata** in cui il peso di ciascun BOT è proporzionale ai suoi giorni residui a scadenza:

```
r_avg = Σ (r_i × giorni_i) / Σ giorni_i
```

**Perché ponderare per i giorni residui?**
I BOT con più giorni alla scadenza riflettono condizioni di tasso più simili a quelle del nuovo BOT che verrà emesso (anch'esso con durata lunga all'inizio). Ricevono quindi un peso maggiore nella media.

### Passo 4 — Prezzo stimato

Dal rendimento medio ponderato si ricava il prezzo di emissione atteso per la durata `giorni_target` (giorni tra regolamento e scadenza del BOT da emettere):

```
prezzo_stimato = 100 / (1 + r_avg × giorni_target / 365)
```

### Passo 5 — Rendimento netto

Si applica l'aliquota del **12,5%** sull'imposta sostitutiva del disaggio (differenza tra il valore di rimborso e il prezzo stimato):

```
imposta = (100 − prezzo_stimato) × 12,5%
rendimento_netto = ((100 − imposta) / prezzo_stimato) ^ (365 / giorni_target) − 1
```

## Come leggere i risultati

Ogni card mostra:

- **Prezzo emissione stimato**: il prezzo al quale ci si aspetta che il MEF emetta il BOT
- **Rendimento lordo**: rendimento annualizzato prima delle imposte
- **Rendimento netto**: rendimento annualizzato dopo l'imposta sostitutiva del 12,5%
- **Tabella dettaglio** (espandibile): i BOT usati per il calcolo con i rispettivi pesi

Il colore del bordo della card indica la durata:
- **Blu** = BOT annuale
- **Verde** = BOT semestrale
- **Grigio** = durata *t.b.d.* (non calcolabile)

## Limiti e avvertenze

- La previsione è una **stima indicativa**, non una previsione finanziaria certificata.
- Le condizioni di mercato possono cambiare significativamente tra oggi e la data d'asta.
- Il MEF fissa il prezzo in base alla domanda effettiva nell'asta competitiva: il rendimento reale può differire dalla stima.
- Per aste con durata *t.b.d.* non è possibile calcolare la previsione.
- Il modello non tiene conto di eventi macroeconomici straordinari (decisioni BCE, comunicati di inflazione, ecc.) che possono spostare i tassi prima dell'asta.

> **Nota metodologica** — Il metodo adottato (interpolazione lineare sui rendimenti dei BOT in circolazione) è volutamente semplice e trasparente. Esiste un approccio più sofisticato — la **curva dei rendimenti a termine** (*forward rate curve*), utilizzata anche dal MEF e dalle banche centrali — che stima il tasso implicito tra due date future partendo dall'intera struttura a termine dei tassi di mercato. Quel metodo richiede però la costruzione di una curva zero-coupon completa (bootstrapping) e l'applicazione di modelli statistici avanzati (es. Nelson-Siegel), ed è significativamente più complesso da implementare e da spiegare. Il modello attuale offre una buona approssimazione per l'uso pratico che ci interessa.

## Confronto con il mercato secondario

Una volta nota la previsione, puoi confrontarlo con il rendimento dei BOT già quotati sul MOT
per decidere se conviene:

- **Partecipare all'asta** (prezzo stimato, nessuna commissione percentuale per alcune banche)
- **Acquistare sul MOT** (prezzo noto, ma commissioni di negoziazione più alte)

Usa il [Calcolatore BOT](/guides/calcolatore) per simulare entrambi gli scenari con le
commissioni della tua banca.
