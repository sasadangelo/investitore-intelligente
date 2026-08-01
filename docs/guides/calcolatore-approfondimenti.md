---
title: Approfondimenti sul Calcolatore BOT
description: Spiegazione dettagliata dei calcoli interni del Calcolatore BOT — disaggio lordo, imposta disaggio e rimborso pro-quota.
icon: bi-journal-text
order: 5
---

# Approfondimenti sul Calcolatore BOT

Questa pagina approfondisce i calcoli che il **[Calcolatore BOT](/guides/calcolatore)** esegue
internamente e che nella guida principale sono stati volutamente semplificati. Se sei curioso di
sapere come vengono prodotti certi numeri, sei nel posto giusto.

## Disaggio lordo e imposta disaggio

### Che cos'è il disaggio

I BOT sono titoli **zero coupon**: non pagano cedole periodiche, ma vengono emessi a un prezzo
inferiore a 100 e rimborsati a 100 alla scadenza. La differenza tra il prezzo di rimborso (100) e
il prezzo di emissione è il **disaggio lordo**, cioè il guadagno lordo del titolo.

> **Esempio**: BOT emesso a 97,50 → disaggio lordo = 100 − 97,50 = **2,50€ per ogni 100€ nominali**

### L'imposta sul disaggio

Il disaggio è soggetto a un'imposta sostitutiva del **12,5%**, che viene però pagata *in anticipo*
dall'acquirente all'asta, al momento dell'emissione. Questo significa che chi compra il BOT
direttamente in asta anticipa l'intera imposta anche se il titolo lo terrà solo per una parte della
sua vita.

Quando il BOT viene venduto prima della scadenza o acquistato sul MOT, l'imposta deve essere
ripartita in modo proporzionale alla durata effettiva di possesso. Per farlo si usa il
**prezzo teorico**.

### Il prezzo teorico

Il prezzo teorico è il valore "giusto" del BOT in un dato momento, calcolato interpolando
linearmente tra:

- il punto di partenza: **(data emissione, prezzo emissione)**
- il punto di arrivo: **(data scadenza, 100)**

In pratica si immagina una retta che parte dal prezzo di emissione e sale fino a 100 nel giorno
della scadenza. Ogni giorno intermedio cade su un punto preciso di questa retta.

```
Prezzo teorico = Prezzo emissione + (100 − Prezzo emissione) × (giorni trascorsi / durata totale)
```

> **Esempio**: BOT emesso a 97,50 con durata 365 giorni.  
> Se acquisto dopo 30 giorni:  
> Prezzo teorico = 97,50 + 2,50 × (30 / 365) ≈ **97,71**

### Calcolo dell'imposta disaggio pro-quota

L'imposta disaggio che spetta al periodo di possesso è:

```
Disaggio pro-quota = 100 − Prezzo teorico alla data di acquisto
Imposta disaggio   = Disaggio pro-quota × 12,5% × Quantità
```

Chi acquista sul **MOT** (mercato secondario) paga solo l'imposta sul disaggio relativa ai giorni
che il titolo rimarrà in suo possesso — non sull'intera vita del BOT. Il venditore avrà già
pagato la sua quota quando aveva acquistato.

Chi acquista in **Asta** anticipa l'intera imposta sull'intero disaggio, ma al rimborso a
scadenza non ne pagherà altra.

### Imposta disaggio rimborsata (vendita anticipata)

Se si vende prima della scadenza, il calcolatore stima l'imposta disaggio già anticipata e non
ancora "consumata" (cioè relativa ai giorni di possesso del prossimo acquirente). Quella quota
viene convenzionalmente indicata come **imposta disaggio rimborsata** e contribuisce ad aumentare
il ricavato netto della vendita.

```
Prezzo teorico alla data di vendita = Prezzo emissione + (100 − Prezzo emissione) × (giorni alla vendita / durata totale)
Imposta rimborsata = (100 − Prezzo teorico vendita) × 12,5% × Quantità
```
