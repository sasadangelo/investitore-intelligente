---
title: Calcolatore Obbligazioni
description: Come usare il calcolatore per simulare acquisto, cedole e vendita o rimborso di un BOT o di un BTP, con commissioni e tasse, e un esempio completo per ciascuno.
icon: bi-calculator
order: 4
---

# Calcolatore Obbligazioni

Dopo aver scelto il titolo nel **[Catalogo Obbligazioni](/guides/catalogo)**, usa il **[Calcolatore Obbligazioni](/calculator/)** per sapere con esattezza quanto paghi, quanto incassi e quanto ti resta in tasca, con le commissioni della tua banca e tutte le tasse. Il calcolatore è lo stesso per **BOT** e **BTP**: per un BTP il risultato ha qualche riga in più (rateo, prezzo tel quel, piano cedole).

Il calcolatore tiene conto di:

- commissioni bancarie, diverse per asta e mercato (MOT), e per i BTP l'eventuale spesa fissa per cedola;
- tasse al 12,5% su scarto di emissione, cedole, rateo e plusvalenza, compreso lo zainetto fiscale;
- imposta di bollo;
- per un BTP, il rateo e tutte le cedole che incassi.

Puoi simulare il titolo tenuto fino alla scadenza o venduto prima, per capire se una vendita conviene prima di farla.

> 💡 Accanto a ogni campo del form e a ogni riga del risultato trovi l'icona **ⓘ**: cliccala per una spiegazione breve. Questa guida spiega gli stessi campi più nel dettaglio.

> 📖 Esempi completi, riga per riga: **[Esempi di calcolo: BOT](/guides/esempi-bot)** · **[Esempi di calcolo: BTP](/guides/esempi-btp)**

[TOC]

## I campi del form

La maggior parte dei campi si compila da sola in base al titolo, al mercato e al profilo bancario scelti; tutti restano modificabili. All'apertura il calcolatore è pronto per un acquisto **sul MOT, oggi, all'ultimo prezzo**, con un lotto di 10.000 €.

### Titolo e mercato

- **Titolo**: scegli il BOT o il BTP dal menu, dove sono divisi in due gruppi. I dati del titolo (ISIN, date, prezzo di emissione, cedola) compaiono sotto il menu. Con **Inserisci BOT manualmente** puoi simulare un BOT che non è in archivio, per esempio quello della prossima asta.
- **Mercato di acquisto**:
    - **MOT**: compri in Borsa, tramite la banca, un titolo già emesso. Il prezzo proposto è l'ultima quotazione, la data è oggi.
    - **Asta**: compri all'emissione. Il prezzo proposto è quello di emissione, la data quella di emissione.
- **Data regolamento**: il giorno in cui paghi e ricevi il titolo. Sul MOT è il giorno dell'ordine più 2 giorni lavorativi; in asta è la data di regolamento dell'asta.
- **Prezzo acquisto**: il prezzo ogni 100 € di nominale (es. `98.50` = 98,50 € ogni 100 €). Per un BTP è il **corso secco**, cioè il prezzo quotato senza rateo: il rateo lo aggiunge il calcolatore.
- **Lotto nominale**: quanto valore nominale compri, in multipli di 100 € (es. `10000` = 100 titoli da 100 €). Non è quanto paghi: quello dipende dal prezzo.

### Profilo bancario e commissioni

Scegli la tua banca da **Profilo bancario**: le commissioni si compilano da sole in base al mercato, al tipo di titolo e alla durata. Molte banche fanno pagare i BTP diversamente dai BOT: sul MOT alcune applicano ai BTP una percentuale più alta, e in asta la sottoscrizione dei BTP è di solito gratuita, mentre per i BOT ci sono commissioni massime fissate per legge in base alla durata. Se la tua banca non c'è, lascia *"Inserisci commissioni manualmente"* e compila i campi:

| Campo | Descrizione |
|---|---|
| **%** | Percentuale sul nominale (asta) o sull'importo secco (MOT) |
| **Min (€)** | Commissione minima (solo MOT): pesa molto sui lotti piccoli |
| **Max (€)** | Commissione massima (solo MOT); vuoto = nessun tetto |
| **Commissione fissa (€)** | Quota fissa per ordine, oltre alla percentuale |

Nel profilo di una banca (menu **Banche**) puoi salvare anche la **spesa fissa per cedola** (vedi sotto).

### Vendita anticipata

Attiva **Vendita anticipata** per simulare una vendita sul MOT prima della scadenza: inserisci data di regolamento, prezzo di vendita (per un BTP il corso secco) e commissioni di vendita. Se non lo attivi, il calcolo assume che tieni il titolo fino al rimborso a 100, dove non si pagano commissioni.

### Parametri fiscali

- **Periodicità bollo**: trimestrale (di solito) o annuale, come la addebita la tua banca. Cambia di poco il totale.
- **Minusvalenze (€)**: le perdite passate che hai nello **zainetto fiscale** e non hai ancora recuperato. Riducono le tasse su un'eventuale plusvalenza. Lascia 0 se non ne hai.
- **Spesa per cedola (€)**: solo BTP. Alcune banche trattengono una cifra fissa a ogni cedola incassata, qualunque sia l'importo. Se la tua lo fa, inseriscila qui (o salvala nel profilo della banca, così si compila da sola). Non si paga se vendi prima di uno stacco, perché in quel caso incassi il rateo, non una cedola. Su un lotto piccolo pesa molto: 2 € su una cedola da 16,75 € (1.000 € di un BTP al 3,35%) sono il 12%.

### Simulare un acquisto in asta

- **BOT della prossima asta**: il titolo non è ancora in archivio. Prendi le date dal **[Calendario Aste](/auctions/)** e il prezzo stimato dalle **[Previsioni](/auctions/forecast)**, poi scegli **Asta** e **Inserisci BOT manualmente** e inserisci date di emissione e scadenza e il prezzo stimato come prezzo di emissione e di acquisto.
- **BTP in riapertura**: nel **[Calendario Aste](/auctions/)**, accanto al BTP offerto, l'icona del calcolatore apre il calcolatore già impostato su quel BTP, mercato Asta e data di regolamento. Inserisci il prezzo di aggiudicazione (prima dell'asta, l'ultimo prezzo di mercato è una buona stima). Paghi anche il rateo della cedola in corso, come sul MOT.
- Puoi anche scegliere **Asta** per un BOT già emesso, per ricostruire il rendimento di un'asta passata.

Controlla che le commissioni proposte dal profilo bancario siano quelle che la tua banca applica in asta.

## I risultati

### Acquisto

- **Quantità**: lotto nominale / 100.
- **Importo secco**: prezzo × quantità.
- **Commissioni** e **Commissioni fisse**: la percentuale sul nominale (asta) o sull'importo secco (MOT), con minimo e massimo, più la quota fissa.
- Per un **BOT**, **Disaggio pro-quota**, **Imposta disaggio pro-quota** e **Imposta disaggio**: la parte dello scarto di emissione (100 meno il prezzo di emissione) che maturerà mentre tieni il titolo, e il 12,5% su di essa, che per i BOT la banca trattiene subito.
- **Totale pagato**: quanto esce dal conto, con commissioni e imposte.

### Capital Gain

C'è per ogni acquisto, in asta o sul MOT, sia con vendita anticipata sia a scadenza. Anche un titolo comprato in asta e tenuto fino alla scadenza ha di solito una piccola minusvalenza: le commissioni d'acquisto, che finiscono nello zainetto. Separa il guadagno dovuto allo scarto di emissione, tassato a parte, dalla vera plusvalenza o minusvalenza.

- **Prezzo teorico di acquisto / vendita**: il prezzo di emissione più lo scarto maturato a quella data; a scadenza è 100.
- **Prezzo di carico / scarico**: il prezzo pagato o incassato con le commissioni per 100 € di nominale, meno lo scarto già maturato.
- **Plus/Minus valenza** e **Plus/Minus realizzata**: scarico meno carico, ogni 100 € di nominale e sul lotto.
- **Riduzione imponibile TdS (48,08%)**: sui titoli di Stato una plusvalenza o minusvalenza conta per il 48,08% (12,5% / 26%) quando la compensi con lo zainetto.
- **Imposta sulla plusvalenza (12,5%)**: trattenuta dalla banca alla vendita o al rimborso, al netto delle minusvalenze dello zainetto. Se invece c'è una minusvalenza, la riga **Minus valenza da zainetto** mostra quanto ne aggiungi allo zainetto.

Il perché di ogni passaggio è in **[Approfondimenti sul Calcolatore](/guides/calcolatore-approfondimenti)**.

### Rimborso o vendita anticipata

- **Importo secco**: prezzo di vendita o di rimborso × quantità.
- **Commissioni** di vendita: zero al rimborso a scadenza.
- Per un **BOT**, **Imposta disaggio rimborsata**: se vendi prima, il compratore ti rimborsa la parte di imposta sul disaggio che riguarda i giorni dopo la vendita; a scadenza è zero.
- **Imposta sulla plusvalenza**: quella della sezione Capital Gain.
- **Totale ricevuto**: quanto entra sul conto, dopo commissioni e tasse. Per un BTP le cedole sono a parte, nel piano cedole.

### Imposta di bollo

Lo **0,20% l'anno** sulla media tra importo pagato e nominale, per i trimestri (o i mesi, con il bollo annuale) in cui tieni il titolo.

### Riepilogo

- **Guadagno lordo**: cedole lorde più incasso finale, meno quanto hai pagato, prima di commissioni, tasse e bollo.
- **Guadagno netto (pre-bollo)**: cedole nette più totale ricevuto, meno totale pagato.
- **Guadagno netto**: quello che ti resta in tasca, anche al netto del bollo.
- **Rendimenti** lordo, netto pre-bollo e netto, ciascuno **semplice / composto**. Il **composto** è il tasso interno di rendimento (TIR) calcolato su tutti i flussi con le loro date: è il numero da usare per confrontare titoli diversi. Il **semplice** divide il guadagno per il capitale e per gli anni, senza badare a quando arrivano i soldi. Nel rendimento netto il bollo si toglie un anno alla volta, come lo paghi davvero.
- Per un BTP tenuto almeno un anno, la **Duration modificata**: una stima di quanto scenderebbe il prezzo del BTP, in percentuale, se i tassi di mercato salissero dell'1% (e di quanto salirebbe se scendessero). Conta solo se pensi di venderlo prima della scadenza: **[cos'è la duration](/guides/cosa-e-un-btp#quanto-si-muove-il-prezzo-la-duration)**.

## Righe in più per un BTP

Per un BTP il calcolatore aggiunge quello che serve per un titolo con cedola. I concetti (rateo, corso secco e tel quel, scarto di emissione) sono spiegati in **[Cos'è un BTP](/guides/cosa-e-un-btp)**.

- **Corso secco, Rateo lordo, Prezzo tel quel**: il prezzo quotato, la parte di cedola maturata dall'ultimo stacco e la loro somma, che è quanto paghi davvero ogni 100 € di nominale. **Rateo pagato al venditore** e **Importo tel quel** sono gli stessi valori sul lotto. Il rateo non è un costo: lo recuperi con la prossima cedola, che incassi per intero.
- **Piano cedole**: tutte le cedole che incassi tra l'acquisto e la vendita o la scadenza, lorde e nette, con i totali. Le nette sono già al netto della spesa per cedola, se c'è.
- **Lo scarto di emissione va al contrario rispetto al BOT.** Nel BOT l'imposta sul disaggio si paga all'acquisto. Nel BTP all'acquisto ricevi un **Credito imposta disaggio** sullo scarto già maturato (chi ti vende l'ha già pagato), e alla vendita o a scadenza la banca trattiene l'**Imposta disaggio trattenuta** sullo scarto maturato fino a quel giorno. Per questo le righe hanno nomi diversi e importi negativi.
- **Il rateo è tassato**: **Credito imposta sul rateo** del 12,5% sul rateo che paghi al venditore (alla cedola successiva la banca tassa la cedola intera); se vendi prima della scadenza, **Imposta sul rateo incassato** del 12,5% su quello che ti paga il compratore.

## Esempi completi

Per vedere il calcolatore all'opera su casi reali, riga per riga e con il calcolo di ogni valore:

- **[Esempi di calcolo: BOT](/guides/esempi-bot)**: un BOT comprato sul MOT e tenuto fino alla scadenza, e uno comprato in asta e venduto prima;
- **[Esempi di calcolo: BTP](/guides/esempi-btp)**: un BTP comprato sul MOT, tenuto fino alla scadenza o venduto prima.

## Consigli pratici

- **Guarda il rendimento netto composto**, non la cedola: un BTP con cedola alta comprato sopra 100 può rendere meno di uno con cedola bassa comprato sotto 100.
- **Confronta asta e MOT** per lo stesso titolo, e cambia il profilo bancario per vedere quanto pesano le commissioni.
- **Per lotti piccoli** il minimo di commissione e il bollo pesano di più: prova lotti diversi per vedere da quale importo in su la spesa diventa trascurabile.
- **Confronta più date di vendita** per lo stesso BTP: rateo e scarto si spostano dal venditore al compratore giorno per giorno, il prezzo di mercato no.
- **Inserisci le minusvalenze** che hai nello zainetto: riducono l'imposta sulla plusvalenza.

---

Per i concetti torna a **[Cos'è un BOT](/guides/cosa-e-un-bot)** e **[Cos'è un BTP](/guides/cosa-e-un-btp)**, o a **[Sei Nuovo? Inizia Qui](/guides/inizia-qui)** per i passi pratici.
