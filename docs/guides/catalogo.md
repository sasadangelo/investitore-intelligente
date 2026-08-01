---
title: Catalogo BOT
description: Come leggere il catalogo, i rendimenti lordo e netto, e come navigare alle schede dettaglio.
icon: bi-list-ul
order: 1
---

# Catalogo BOT

Il **Catalogo BOT** è il punto di partenza dell'applicazione. Mostra tutti i Buoni Ordinari del Tesoro (BOT) attualmente in circolazione con le relative quotazioni di mercato aggiornate.

## Cos'è un BOT

Se non conosci ancora i BOT, leggi la guida completa: **[Cos'è un BOT](/guides/cosa-e-un-bot)**

## Come leggere la tabella

| Colonna | Significato |
|---|---|
| **Nome** | Identificativo del BOT (es. `Bot Zc Nov26 A Eur` = zero-coupon, scadenza novembre 2026, annuale) |
| **ISIN** | Codice identificativo internazionale |
| **Data Emissione** | Data di emissione del BOT |
| **Data Scadenza** | Data di rimborso a 100 |
| **Ultimo Prezzo** | Ultima quotazione disponibile sul mercato secondario (MOT) |
| **Rendimento lordo** | Rendimento annualizzato lordo calcolato sull'ultimo prezzo |
| **Rendimento netto** | Rendimento annualizzato netto (al netto del 12,5% sul disaggio) |
| **Azioni** | Pulsanti per accedere al dettaglio o al calcolatore |

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

> **Nota:** l'anno è considerato di 365 giorni (366 negli anni bisestili). Per annualizzare il rendimento usiamo il metodo **Act/Act**, uno dei sistemi standard per calcolare i giorni effettivi in un anno. Questo metodo consente di normalizzare i rendimenti e renderli comparabili fra titoli con scadenze diverse.

## Aggiornamento quotazioni

Le quotazioni vengono sincronizzate da **Teleborsa** tramite il pulsante **Aggiorna quotazioni**
nella barra in alto. L'aggiornamento è asincrono: una barra di progresso mostra l'avanzamento
in tempo reale.

## Dalla lista al dettaglio

Cliccando su un BOT nella tabella si accede alla **scheda dettaglio**, che mostra:

- Tutti i dati dell'emissione (ISIN, date, prezzi, aliquota)
- Rendimento lordo e netto calcolati
- Pulsante **Calcolatore** per simulare l'acquisto di quel BOT con le proprie commissioni bancarie
