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

> ℹ️ I rendimenti mostrati sono **annualizzati** e calcolati al netto dell'imposta sostitutiva sul disaggio (12,5%), ma **non includono** commissioni bancarie, imposta di bollo, né altre variabili coe le commissioni sul capital gain. Per il calcolo esatto con tutte le imposte e commissioni della tua banca, usa il **[Calcolatore BOT](/bonds/calculator)**.

## Aggiornamento quotazioni

Le quotazioni vengono sincronizzate da **Teleborsa** tramite il pulsante **Aggiorna quotazioni**
nella barra in alto. L'aggiornamento è asincrono: una barra di progresso mostra l'avanzamento
in tempo reale.

## Dalla lista al dettaglio

Cliccando su un BOT nella tabella si accede alla **scheda dettaglio**, che mostra:

- Tutti i dati dell'emissione (ISIN, date, prezzi, aliquota)
- Rendimento lordo e netto calcolati
- Pulsante **Calcolatore** per simulare l'acquisto di quel BOT con le proprie commissioni bancarie
