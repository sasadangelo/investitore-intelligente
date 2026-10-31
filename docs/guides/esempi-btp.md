---
title: "Esempi di calcolo: BTP"
description: Un BTP comprato sul MOT, tenuto fino alla scadenza o venduto prima, riga per riga con i numeri del calcolatore.
icon: bi-journal-check
order: 21
---

# Esempi di calcolo: BTP

Ogni esempio mostra il risultato del **[Calcolatore Obbligazioni](/calculator/)** riga per riga, con il calcolo che c'è dietro. Cosa significa ogni riga è spiegato nella guida **[Calcolatore Obbligazioni](/guides/calcolatore)**, alla sezione **[Righe in più per un BTP](/guides/calcolatore#righe-in-piu-per-un-btp)**; i concetti (rateo, scarto di emissione, duration) in **[Cos'è un BTP](/guides/cosa-e-un-btp)**.

[TOC]

## BTP 3,35% Lug 2029 comprato sul MOT e tenuto a scadenza

**BTP 3,35% Lug 2029** (ISIN IT0005584849): emesso il 1° marzo 2024 a **99,82**, scade il 1° luglio 2029, paga una cedola semestrale di **1,675 €** ogni 1° gennaio e 1° luglio per ogni 100 € di nominale.

| Parametro | Valore |
|---|---|
| Mercato | MOT |
| Data regolamento | 29/10/2026 (ordine del 27/10 + 2 giorni lavorativi) |
| Prezzo acquisto (corso secco) | 99,18 |
| Lotto nominale | 10.000 € (100 BTP) |
| Commissioni acquisto | 0,10% — minimo 5 € — nessun massimo, nessuna quota fissa |
| Vendita anticipata | No (rimborso a scadenza) |
| Bollo | Trimestrale |
| Minusvalenze | 0 € |

### Acquisto

| Riga | Come si calcola | Valore |
|---|---|---|
| Quantità BTP | 10.000 / 100 | 100 |
| Corso secco | il prezzo inserito | 99,1800 |
| Rateo lordo | 1,675 × 120 / 184 (giorni dal 1° luglio al 29 ottobre, su 184 del semestre) | 1,092391 |
| Prezzo tel quel | 99,18 + 1,092391 | 100,272391 |
| Importo secco | 99,18 × 100 | 9.918,00 € |
| Rateo pagato al venditore | 1,092391 × 100 | 109,24 € |
| Importo tel quel | 9.918,00 + 109,24 | 10.027,24 € |
| Commissioni | max(9.918,00 × 0,10%; 5) | 9,92 € |
| Commissioni fisse | — | 0,00 € |
| Disaggio maturato pro-quota | scarto (100 − 99,82 = 0,18) maturato dall'emissione al 29 ottobre | 0,089815 |
| Credito imposta disaggio | −0,089815 × 12,5% × 100 | −1,12 € |
| Credito imposta sul rateo | −109,24 × 12,5% | −13,65 € |
| **Totale pagato** | 10.027,24 + 9,92 − 1,12 − 13,65 | **10.022,38 €** |

I due crediti sono importi che la banca ti riconosce subito e che pareggiano le tasse che pagherai sulla cedola intera e sullo scarto alla scadenza.

### Piano cedole

| Data stacco | Lorda (per 100) | Lorda (€) | Netta (€) |
|---|---|---|---|
| 01/01/2027 | 1,675000 | 167,50 € | 146,56 € |
| 01/07/2027 | 1,675000 | 167,50 € | 146,56 € |
| 01/01/2028 | 1,675000 | 167,50 € | 146,56 € |
| 01/07/2028 | 1,675000 | 167,50 € | 146,56 € |
| 01/01/2029 | 1,675000 | 167,50 € | 146,56 € |
| 01/07/2029 | 1,675000 | 167,50 € | 146,56 € |
| **Totale cedole (6)** | | **1.005,00 €** | **879,37 €** |

La cedola netta è la lorda meno il 12,5%: 167,50 × 87,5% = 146,56 €. L'ultima cedola si incassa insieme al rimborso.

### Capital Gain

| Riga | Come si calcola | Valore |
|---|---|---|
| Prezzo teorico acquisto | 99,82 + 0,089815 di scarto maturato | 99,90982 |
| Prezzo teorico vendita | a scadenza lo scarto è maturato tutto | 100,00000 |
| Prezzo di carico | 99,18 + 9,92 / 100 − 0,089815 | 99,18936 |
| Prezzo di scarico | 100 − 0 / 100 − 0,18 | 99,820 |
| Plus/Minus valenza (per 100 nominale) | 99,820 − 99,18936 | +0,63064 |
| Plus/Minus realizzata | 0,63064 × 100 | 63,06 € |
| Riduzione imponibile TdS (48,08%) | 63,06 × 48,08% | 30,32 € |
| **Imposta sulla plusvalenza (12,5%)** | 63,06 × 12,5% | **7,88 €** |

Prezzo di carico e di scarico non contengono lo scarto maturato, che è già tassato a parte: così ogni euro di guadagno sul prezzo è tassato una sola volta. Il rateo non entra mai nel capital gain.

### Rimborso a scadenza

| Riga | Come si calcola | Valore |
|---|---|---|
| Corso secco | prezzo di rimborso | 100,0000 |
| Importo secco | 100 × 100 | 10.000,00 € |
| Commissioni | il rimborso non è una vendita | 0,00 € |
| Disaggio maturato pro-quota | tutto lo scarto | 0,180000 |
| Imposta disaggio trattenuta | −0,18 × 12,5% × 100 | −2,25 € |
| Imposta sulla plusvalenza | dalla sezione Capital Gain | −7,88 € |
| **Totale ricevuto** | 10.000,00 − 2,25 − 7,88 | **9.989,87 €** |

A scadenza non c'è rateo: l'ultima cedola è pagata per intero ed è nel piano cedole. Sullo scarto, tra il credito all'acquisto (1,12 €) e la trattenuta a scadenza (2,25 €), paghi 1,13 €: il 12,5% dello scarto maturato mentre il titolo era tuo.

### Imposta di bollo

| Riga | Valore |
|---|---|
| Periodi di possesso | 11 trimestri |
| Stima bollo | 54,77 € |

### Riepilogo

| Riga | Come si calcola | Valore |
|---|---|---|
| Guadagno lordo | cedole lorde + rimborso − importo tel quel = 1.005,00 + 10.000,00 − 10.027,24 | 977,76 € |
| Guadagno netto (pre-bollo) | cedole nette + totale ricevuto − totale pagato = 879,37 + 9.989,87 − 10.022,38 | 846,86 € |
| **Guadagno netto** | 846,86 − 54,77 | **792,09 €** |

| Rendimento | Semplice | Composto |
|---|---|---|
| Lordo | 3,649% | 3,707% |
| Netto (pre-bollo) | 3,162% | 3,207% |
| **Netto** | **2,958%** | **2,995%** |

La **duration modificata** è **2,51**: se i tassi di mercato salgono dell'1%, il prezzo del BTP scende di circa il 2,51%. Nel rendimento netto composto il bollo (54,77 €) è diviso sui tre anni solari 2027, 2028 e 2029.

## Lo stesso BTP, venduto prima della scadenza

Stessi dati di acquisto, ma con **Vendita anticipata**: vendi con regolamento il 15/12/2027 a un corso secco di **100,50**, con le stesse commissioni dell'acquisto. Il piano cedole si ferma alle due cedole del 2027 (293,13 € nette) e la sezione di vendita si allunga:

| Riga | Come si calcola | Valore |
|---|---|---|
| Corso secco | il prezzo di vendita | 100,5000 |
| Rateo lordo | 1,675 × 167 / 184 (dal 1° luglio al 15 dicembre) | 1,520244 |
| Prezzo tel quel | 100,50 + 1,520244 | 102,020244 |
| Importo secco | 100,50 × 100 | 10.050,00 € |
| Rateo incassato dal compratore | 1,520244 × 100 | 152,02 € |
| Importo tel quel | 10.050,00 + 152,02 | 10.202,02 € |
| Commissioni | 10.050,00 × 0,10% | 10,05 € |
| Disaggio maturato pro-quota | scarto maturato fino al 15 dicembre | 0,127914 |
| Imposta disaggio trattenuta | −0,127914 × 12,5% × 100 | −1,60 € |
| Imposta sul rateo incassato | −152,02 × 12,5% | −19,00 € |
| Imposta sulla plusvalenza | (100,50 − 0,1005 − 0,127914) − 99,18936 = 1,08222 → 108,22 € × 12,5% | −13,53 € |
| **Totale ricevuto** | 10.202,02 − 10,05 − 1,60 − 19,00 − 13,53 | **10.157,84 €** |

Vendendo prima dello stacco del 1° gennaio non incassi quella cedola, ma il compratore ti paga la parte maturata finora (il rateo), su cui la banca trattiene il 12,5% come su una cedola. Con 4 trimestri di bollo (19,92 €) il guadagno netto è **408,67 €**, con un rendimento netto composto del **3,664%**: più alto del rimborso a scadenza perché in questo esempio il prezzo è salito da 99,18 a 100,50 in poco più di un anno.

Se nel risultato il piano cedole è vuoto vuol dire che vendi prima del primo stacco: l'unico interesse che incassi è il rateo pagato dal compratore.

---

L'esempio con un BOT è in **[Esempi di calcolo: BOT](/guides/esempi-bot)**.
