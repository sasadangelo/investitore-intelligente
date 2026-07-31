---
title: Catalogo BOT
description: Come leggere il catalogo, i rendimenti lordo e netto, e come navigare alle schede dettaglio.
icon: bi-list-ul
order: 1
---

# Catalogo BOT

Il **Catalogo BOT** è il punto di partenza dell'applicazione. Mostra tutti i Buoni Ordinari del Tesoro (BOT) attualmente in circolazione con le relative quotazioni di mercato aggiornate.

## Cos'è un BOT

Un **Buono Ordinario del Tesoro** è un titolo di Stato italiano a breve termine (durata massima 12 mesi),
emesso dal Ministero dell'Economia e delle Finanze (MEF) tramite asta competitiva.

- È uno **strumento zero-coupon**: non paga cedole periodiche.
- Il rendimento è dato dalla **differenza tra il valore di rimborso (100) e il prezzo di acquisto**.
- L'aliquota fiscale agevolata è del **12,5%** (come tutti i titoli di Stato italiani).

## Come leggere la tabella

| Colonna | Significato |
|---|---|
| **Nome** | Identificativo del BOT (es. `Bot Zc Nov26 A Eur` = zero-coupon, scadenza novembre 2026, annuale) |
| **ISIN** | Codice identificativo internazionale |
| **Scadenza** | Data di rimborso a 100 |
| **GG residui** | Giorni mancanti alla scadenza da oggi |
| **Prezzo emissione** | Prezzo al quale il MEF ha emesso il BOT in asta |
| **Last price** | Ultima quotazione disponibile sul mercato secondario (MOT) |
| **Rend. lordo** | Rendimento annualizzato lordo calcolato sul last price |
| **Rend. netto** | Rendimento annualizzato netto (al netto del 12,5% sul disaggio) |

## Come vengono calcolati i rendimenti

I rendimenti sono calcolati con la formula **composta** (non semplice):

```
rendimento_lordo = (100 / last_price) ^ (365 / giorni_residui) - 1
```

Per il rendimento netto si detrae l'imposta sostitutiva dal valore di rimborso:

```
disaggio_lordo   = (100 - prezzo_emissione) × giorni_residui / giorni_totali
imposta_disaggio = disaggio_lordo × 12,5%
rendimento_netto = ((100 - imposta_disaggio) / last_price) ^ (365 / giorni_residui) - 1
```

> **Nota:** l'anno è considerato di 365 giorni (366 negli anni bisestili).

## Aggiornamento quotazioni

Le quotazioni vengono sincronizzate da **Teleborsa** tramite il pulsante **Aggiorna quotazioni**
nella barra in alto. L'aggiornamento è asincrono: una barra di progresso mostra l'avanzamento
in tempo reale.

## Dalla lista al dettaglio

Cliccando su un BOT nella tabella si accede alla **scheda dettaglio**, che mostra:

- Tutti i dati dell'emissione (ISIN, date, prezzi, aliquota)
- Rendimento lordo e netto calcolati
- Pulsante **Calcolatore** per simulare l'acquisto di quel BOT con le proprie commissioni bancarie
