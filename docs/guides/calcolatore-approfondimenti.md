---
title: Approfondimenti sul Calcolatore BOT
description: Spiegazione dettagliata dei calcoli interni del Calcolatore BOT — disaggio lordo, imposta disaggio e rimborso pro-quota.
icon: bi-journal-text
order: 5
---

# Approfondimenti sul Calcolatore BOT

Questa pagina approfondisce i calcoli che il **[Calcolatore BOT](/guides/calcolatore)** esegue internamente e che nella guida principale sono stati volutamente semplificati. Se sei curioso di sapere come vengono prodotti certi numeri, sei nel posto giusto.

## Prezzo Teorico Acquisto e Vendita

Il prezzo teorico è il valore "giusto" del BOT in un dato momento, calcolato interpolando linearmente tra:

- il punto di partenza: **(data emissione, prezzo emissione)**
- il punto di arrivo: **(data scadenza, 100)**

In pratica si immagina una retta che parte dal prezzo di emissione e sale fino a 100 nel giorno
della scadenza. Ogni giorno intermedio cade su un punto preciso di questa retta.

```
Prezzo teorico = Prezzo emissione + (100 − Prezzo emissione) × (giorni trascorsi / durata totale)
```

> **Esempio — prezzo teorico all'acquisto**: BOT emesso a 97,50 con durata 365 giorni.
> Se acquisto dopo 30 giorni:
> Prezzo teorico = 97,50 + 2,50 × (30 / 365) ≈ **97,71**

> **Esempio — prezzo teorico alla vendita anticipata**: stesso BOT, venduto dopo 200 giorni dall'emissione:
> Prezzo teorico = 97,50 + 2,50 × (200 / 365) ≈ **99,12**

Il grafico seguente mostra la retta del prezzo teorico con i tre scenari possibili: il punto di acquisto (dopo 30 giorni), una vendita anticipata (dopo 200 giorni) e il rimborso a scadenza (a 100).

![Grafico prezzo teorico BOT](/static/img/guides/prezzo-teorico-bot.svg)

## Disaggio pro-quota e Imposta disaggio

### Che cos'è il disaggio

I BOT sono titoli **zero coupon**: non pagano cedole periodiche, ma vengono emessi a un prezzo inferiore a 100 e rimborsati a 100 alla scadenza. La differenza tra il prezzo di rimborso (100) e il prezzo di emissione è il **disaggio lordo**, cioè il guadagno lordo del titolo.

> **Esempio**: BOT emesso a 97,50 → disaggio lordo = 100 − 97,50 = **2,50€ per ogni 100€ nominali**

### L'imposta sul disaggio

Il disaggio è soggetto a un'imposta sostitutiva del **12,5%**, che viene però pagata *in anticipo* dall'acquirente all'asta, al momento dell'emissione. Questo significa che chi compra il BOT direttamente in asta anticipa l'intera imposta anche se il titolo lo terrà solo per una parte della sua vita.

Quando il BOT viene venduto prima della scadenza o acquistato sul MOT, l'imposta deve essere ripartita in modo proporzionale alla durata effettiva di possesso. Per farlo si usa il **prezzo teorico** (vedi sezione precedente).

### Calcolo dell'imposta disaggio pro-quota

L'imposta disaggio che spetta al periodo di possesso è:

```
Disaggio pro-quota = 100 − Prezzo teorico alla data di acquisto
Imposta disaggio   = Disaggio pro-quota × 12,5% × Quantità
```

Chi acquista sul **MOT** (mercato secondario) paga solo l'imposta sul disaggio relativa ai giorni che il titolo rimarrà in suo possesso — non sull'intera vita del BOT. Il venditore avrà già pagato la sua quota quando aveva acquistato.

Chi acquista in **Asta** anticipa l'intera imposta sull'intero disaggio, ma al rimborso a scadenza non ne pagherà altra.

### Imposta disaggio rimborsata (vendita anticipata)

Se si vende prima della scadenza, il calcolatore stima l'imposta disaggio già anticipata e non
ancora "consumata" (cioè relativa ai giorni di possesso del prossimo acquirente). Quella quota
viene convenzionalmente indicata come **imposta disaggio rimborsata** e contribuisce ad aumentare
il ricavato netto della vendita.

```
Prezzo teorico alla data di vendita = Prezzo emissione + (100 − Prezzo emissione) × (giorni alla vendita / durata totale)
Imposta rimborsata = (100 − Prezzo teorico vendita) × 12,5% × Quantità
```

## Capital Gain (solo acquisti MOT)

Quando si acquista un BOT sul mercato secondario (MOT), il calcolatore determina sempre se si è realizzata una plusvalenza o una minusvalenza — sia in caso di **vendita anticipata** sia in caso di **rimborso a scadenza**. Questa sezione spiega ciascun campo della sezione **Capital Gain**.

### Prezzo di carico

Immagina di comprare un BOT sul MOT a 96,846. Il fisco non usa direttamente quel prezzo per calcolare se hai guadagnato o perso: deve prima "ripulirlo" da due cose.

**Prima cosa — aggiungi le commissioni.** Le commissioni sono un costo reale che hai sostenuto. Se le ignori, il tuo guadagno appare più alto di quello che è davvero. Si sommano quindi al prezzo pagato, spalmate per ogni singolo BOT: 15,12€ / 50 = **0,302** per BOT.

**Seconda cosa — togli il disaggio già maturato.** Dal giorno di emissione (14/02/2023) al giorno di acquisto (01/03/2023) sono passati 15 giorni. In quei 15 giorni il BOT ha già "guadagnato" un pezzettino di valore lungo la retta del prezzo teorico: 97,00534 − 96,877 = **0,128**. Quella quota non è tua — era già incorporata nel prezzo di mercato quando hai comprato, e viene tassata separatamente come imposta disaggio. Se la lasciassi nel calcolo del capital gain, verrebbe tassata due volte. Quindi si sottrae.

Il risultato è il **prezzo di carico**: la cifra che il fisco considera come tuo vero costo di acquisto, da cui misurerà guadagno o perdita.

```
Prezzo di carico = Prezzo acquisto + (Commissioni acquisto / Quantità) − (Prezzo teorico acquisto − Prezzo emissione)
                = 96,846 + 15,12/50 − (97,00534 − 96,877)
                = 96,846 + 0,302 − 0,128
                = 97,02014
```

### Prezzo di scarico

Il **prezzo di scarico** è il prezzo di vendita (o 100 se a scadenza) depurato delle commissioni di vendita e della quota di disaggio maturata fino alla data di vendita. Alla scadenza, l'intero disaggio è stato maturato, quindi il prezzo di scarico converge verso il prezzo di emissione.

```
Prezzo di scarico = Prezzo vendita − (Commissioni vendita / Quantità) − (Prezzo teorico vendita − Prezzo emissione)
```

> **Esempio** (stesso BOT venduto a 97,10 dopo 200 gg dall'emissione, commissioni vendita 3,50€):
> - Prezzo teorico vendita ≈ 99,12 → quota disaggio = 99,12 − 97,50 = **1,62**
> - Prezzo di scarico = 97,10 − 3,50/50 − 1,62 ≈ **96,88**

### Plus/Minus valenza (per BOT)

È la differenza tra prezzo di scarico e prezzo di carico, **per singolo BOT** (cioè per ogni 100€ nominali):

```
Plus/Minus valenza (per BOT) = Prezzo di scarico − Prezzo di carico
```

Un valore positivo indica una plusvalenza, negativo una minusvalenza.

### Plus/Minus realizzata

È la plus/minus moltiplicata per la quantità, cioè il risultato economico complessivo dell'operazione:

```
Plus/Minus realizzata = Plus/Minus valenza (per BOT) × Quantità
```

### Riduzione imponibile TdS (48,08%)

I BOT sono titoli di Stato (TdS), tassati al **12,5%** anziché al 26% standard. Per rendere le minusvalenze su TdS compensabili con plusvalenze su altri strumenti al 26%, l'Agenzia delle Entrate applica un **fattore di riduzione del 48,08%** (= 12,5% / 26%) all'imponibile.

In caso di **minusvalenza**, questo importo ridotto (48,08% della minus realizzata) è quello che entra nello "zainetto fiscale" e può compensare future plusvalenze.

```
Riduzione imponibile TdS = Plus/Minus realizzata × 48,08%
```

### Minus valenza da zainetto

In caso di minusvalenza, il valore che viene aggiunto allo zainetto fiscale — già ridotto al 48,08% — pronto a compensare future plusvalenze su altri strumenti:

```
Minus valenza da zainetto = |Plus/Minus realizzata| × 48,08%
```

> **Esempio**: minus realizzata = −7,15€ → minus da zainetto = 7,15 × 48,08% ≈ **3,44€**
