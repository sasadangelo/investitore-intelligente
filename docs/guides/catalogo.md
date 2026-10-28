---
title: Catalogo BOT
description: Come leggere il catalogo, i rendimenti lordo e netto, e come navigare alle schede dettaglio.
icon: bi-list-ul
order: 3
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
| **Duration mod.** | Solo BTP con più di un anno alla scadenza: di quanto scende in percentuale il prezzo se i tassi salgono dell'1% (vedi sotto) |
| **Azioni** | Pulsanti per accedere al dettaglio o al calcolatore |

> ℹ️ I rendimenti mostrati sono **annualizzati** e calcolati al netto dell'imposta sostitutiva sul disaggio (12,5%), ma **non includono** commissioni bancarie, imposta di bollo, né altre variabili coe le commissioni sul capital gain. Per il calcolo esatto con tutte le imposte e commissioni della tua banca, usa il **[Calcolatore BOT](/calculator/)**.

## Duration modificata (solo BTP)

Misura quanto il prezzo di un BTP reagisce ai tassi: con una duration di **4** il prezzo scende di circa il **4%** se i tassi di mercato salgono dell'1%, e sale di circa il 4% se scendono. Più è alta, più il titolo è rischioso per chi pensa di venderlo prima della scadenza; per chi lo tiene fino alla fine non cambia nulla, perché il rimborso è sempre 100.

È calcolata sull'ultimo prezzo e sul rendimento netto della riga. Per i BOT e per i BTP che scadono entro un anno la colonna è vuota: su durate così brevi il prezzo si muove poco. La spiegazione completa, con esempi su BTP reali, è in **[Cos'è un BTP](/guides/cosa-e-un-btp)**.

## Aggiornamento quotazioni

Le quotazioni vengono sincronizzate da **Teleborsa** tramite il pulsante **Aggiorna quotazioni**
nella barra in alto. L'aggiornamento è asincrono: una barra di progresso mostra l'avanzamento
in tempo reale.

## Dalla lista al dettaglio

Cliccando su un BOT nella tabella si accede alla **scheda dettaglio**, che mostra:

- Tutti i dati dell'emissione (ISIN, date, prezzi, aliquota)
- Rendimento lordo e netto calcolati
- Duration modificata (solo BTP con più di un anno alla scadenza)
- Pulsante **Calcolatore** per simulare l'acquisto di quel BOT con le proprie commissioni bancarie
