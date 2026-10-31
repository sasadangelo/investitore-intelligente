---
title: Catalogo Obbligazioni
description: Come leggere il catalogo di BOT e BTP, i rendimenti lordo e netto, i parametri avanzati e le schede dei titoli.
icon: bi-list-ul
order: 3
---

# Catalogo Obbligazioni

Il **[Catalogo Obbligazioni](/catalogue/)** è il punto di partenza del sito: mostra tutti i **BOT** e i **BTP a tasso fisso** in circolazione, con l'ultimo prezzo di mercato e il rendimento che otterresti comprandoli oggi e tenendoli fino alla scadenza.

Se non sai ancora cosa sono, parti da **[Cos'è un'obbligazione](/guides/cosa-e-un-obbligazione)**, che porta alle guide di BOT e BTP.

## Filtrare e ordinare

- Il menu **Tipo** mostra tutti i titoli, solo i BOT o solo i BTP.
- Cliccando sulle intestazioni **Data Scadenza**, **Rendimento lordo** e **Rendimento netto** ordini la tabella; un secondo clic inverte l'ordine. Di default i titoli sono in ordine di scadenza, dal più vicino.

## Come leggere la tabella

| Colonna | Significato |
|---|---|
| **Nome** | Il nome con cui il titolo è quotato: `Bot Zc Nov26 A Eur` è un BOT (zero coupon) che scade a novembre 2026; `Btp Fx 3.35% Jul29 Eur` è un BTP a tasso fisso con cedola del 3,35% annuo che scade a luglio 2029. Cliccalo per la scheda del titolo |
| **ISIN** | Il codice che identifica il titolo: serve per comprarlo dalla tua banca |
| **Data Emissione** | Data in cui il titolo è stato emesso |
| **Data Scadenza** | Data in cui lo Stato lo rimborsa a 100: è il tuo orizzonte se lo tieni fino alla fine |
| **Ultimo Prezzo** | Ultima quotazione sul MOT ogni 100 € di nominale, senza rateo |
| **Rendimento lordo** | Rendimento annuo composto comprando oggi all'ultimo prezzo e tenendo il titolo a scadenza, prima delle tasse; per un BTP comprende le cedole |
| **Rendimento netto** | Lo stesso dopo le tasse al 12,5% (scarto di emissione, cedole, plusvalenza) |
| **Guadagno netto** | Solo con i [Parametri avanzati](#parametri-avanzati-i-rendimenti-con-i-tuoi-costi): quanto incassi in euro, al netto di tutto, sul lotto indicato |

> ℹ️ I rendimenti mostrati sono **annui** e già al netto delle tasse, ma di default **non includono** le commissioni della tua banca né l'imposta di bollo. Per vederli con i tuoi costi usa i **Parametri avanzati** (qui sotto) o il **[Calcolatore Obbligazioni](/calculator/)**.

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

Le quotazioni vengono scaricate da **Teleborsa** con il pulsante **Aggiorna Quotazioni**, in alto
nella pagina del catalogo: una barra mostra l'avanzamento, prima dei BOT e poi dei BTP. I prezzi
non si aggiornano da soli: quelli che vedi sono dell'ultimo aggiornamento.

## Gestire l'archivio dei titoli

Il pulsante **Gestisci**, accanto ad **Aggiorna Quotazioni**, apre l'elenco completo dei titoli in archivio, scaduti compresi: da lì puoi aggiungere un titolo a mano, correggerne i dati (per esempio la data della prima cedola di un BTP) o cancellarlo. Di solito non serve: l'aggiornamento delle quotazioni aggiunge da solo i titoli nuovi e ignora quelli scaduti.

## Dalla lista al dettaglio

Cliccando sul nome di un titolo si apre la sua **scheda**, che mostra:

- Tutti i dati dell'emissione (ISIN, date, prezzi, aliquota)
- Rendimento lordo e netto calcolati
- Duration modificata (solo BTP con più di un anno alla scadenza): una stima di quanto scenderebbe il prezzo se i tassi di mercato salissero dell'1% (e di quanto salirebbe se scendessero); conta solo se pensi di vendere prima della scadenza: **[cos'è la duration](/guides/cosa-e-un-btp#quanto-si-muove-il-prezzo-la-duration)**
- Pulsante **Calcolatore** per simulare l'acquisto di quel titolo con le commissioni della tua banca
