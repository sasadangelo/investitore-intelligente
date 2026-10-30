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
| **Guadagno netto** | Solo con i [Parametri avanzati](#parametri-avanzati-i-rendimenti-con-i-tuoi-costi): quanto incassi in euro, al netto di tutto, sul lotto indicato |
| **Azioni** | Pulsanti per accedere al dettaglio o al calcolatore |

> ℹ️ I rendimenti mostrati sono **annualizzati** e calcolati al netto dell'imposta sostitutiva sul disaggio (12,5%), ma **non includono** commissioni bancarie, imposta di bollo, né altre variabili coe le commissioni sul capital gain. Per il calcolo esatto con tutte le imposte e commissioni della tua banca, usa il **[Calcolatore BOT](/calculator/)**.

> 💡 Accanto al nome di ogni colonna trovi l'icona **ⓘ**: cliccala per una spiegazione breve di quel valore.

## Parametri avanzati: i rendimenti con i tuoi costi

Di default i rendimenti del catalogo non contano commissioni e bollo, così confronti i titoli tra loro senza pensare alla tua banca. Se vuoi vedere quanto rendono **davvero a te**, apri **Parametri avanzati** sopra la tabella e inserisci:

- il **lotto nominale** che vuoi investire (multiplo di 100 €);
- il tuo **profilo bancario**, oppure le commissioni a mano (percentuale, minimo, massimo, quota fissa) e l'eventuale **spesa per cedola** che la banca trattiene a ogni stacco dei BTP;
- le eventuali **minusvalenze** che hai nello zainetto.

Premi **Applica**: ogni titolo viene simulato come nel [Calcolatore](/calculator/), comprato oggi sul MOT all'ultimo prezzo e tenuto fino a scadenza. Il **rendimento netto** include commissioni, imposta di bollo e zainetto, e compare la colonna **Guadagno netto** in euro. Un riquadro sopra la tabella ricorda quali parametri stai usando; **Rimuovi** torna ai rendimenti di default. I parametri restano attivi mentre cambi pagina, ordinamento o tipo di titolo.

### Quando servono davvero

Se hai già deciso per quanto tempo vuoi investire, tra titoli con scadenze simili le commissioni pesano quasi allo stesso modo e l'ordine della tabella cambia poco. I parametri avanzati fanno la differenza in due casi.

**Quando confronti durate diverse.** La commissione si paga una volta sola, ma il rendimento è annuale: su un titolo breve quella spesa pesa su pochi mesi, su un titolo lungo si spalma su molti anni. Con 10.000 € e le commissioni MOT di un broker online (0,19%, massimo 19 €), a fine ottobre 2026:

| Titolo | Scadenza | Rendimento netto di default | Con i costi reali |
|---|---|---|---|
| BOT Apr 2027 | 6 mesi | 2,63% | 1,98% |
| BTP 3,35% Lug 2029 | 3 anni | 3,21% | 2,94% |
| BTP 4,5% Ott 2053 | 27 anni | 4,40% | 4,27% |

Il BOT perde più di mezzo punto, il BTP a 27 anni poco più di un decimo. Una parte della differenza è il bollo (0,20% l'anno), uguale per tutti; il resto è la commissione.

**Quando investi poco.** Molte banche hanno una **commissione minima**: su un lotto piccolo vale molto più della percentuale. Con 1.000 € e un minimo di 5 € (0,5% del lotto) il BOT di Aprile 2027 scende all'**1,29%**, il BTP Lug 2029 al **2,83%**. Prova lotti diversi per vedere da quale importo in su la spesa diventa trascurabile.

Anche lo **zainetto** può cambiare la scelta: se hai minusvalenze da recuperare, un titolo comprato sotto il prezzo teorico ti fa realizzare una plusvalenza su cui non paghi tasse.

> I rendimenti con i costi sono quelli di un acquisto **oggi sul MOT** tenuto **fino a scadenza**, con bollo trimestrale. Per un acquisto in asta, una vendita anticipata o un altro tipo di bollo usa il [Calcolatore](/calculator/).

## Aggiornamento quotazioni

Le quotazioni vengono sincronizzate da **Teleborsa** tramite il pulsante **Aggiorna quotazioni**
nella barra in alto. L'aggiornamento è asincrono: una barra di progresso mostra l'avanzamento
in tempo reale.

## Dalla lista al dettaglio

Cliccando su un BOT nella tabella si accede alla **scheda dettaglio**, che mostra:

- Tutti i dati dell'emissione (ISIN, date, prezzi, aliquota)
- Rendimento lordo e netto calcolati
- Duration modificata (solo BTP con più di un anno alla scadenza): di quanto scende il prezzo se i tassi salgono dell'1%, spiegata in **[Cos'è un BTP](/guides/cosa-e-un-btp)**
- Pulsante **Calcolatore** per simulare l'acquisto di quel BOT con le proprie commissioni bancarie
