---
title: Calcolatore BTP
description: Come simulare acquisto, cedole, vendita o rimborso di un BTP a tasso fisso, con rateo, scarto di emissione, commissioni e tasse.
icon: bi-calculator
order: 4
---

# Calcolatore BTP

Il **[Calcolatore](/calculator/)** è lo stesso per BOT e BTP: scegli un BTP dal gruppo **BTP** del menu **Titolo** e il calcolatore aggiunge alle sezioni che conosci dal BOT quelle tipiche di un titolo con cedola: **rateo**, **prezzo tel quel** e **piano cedole**.

Questa guida dà per buono quello che trovi in due altre guide:

- **[Calcolatore BOT](/guides/calcolatore)**: i campi del form (mercato, data, prezzo, lotto, profilo bancario, commissioni, vendita anticipata, bollo, minusvalenze) funzionano allo stesso modo;
- **[Cos'è un BTP](/guides/cosa-e-un-btp)**: cos'è il rateo, cosa sono il corso secco e il tel quel, come è tassato lo scarto di emissione.

## Cosa cambia rispetto al BOT

- **Il prezzo che inserisci è il corso secco**, quello che vedi quotato sul MOT. Il rateo lo calcola il calcolatore dalla data di regolamento.
- **Le cedole**: il calcolatore elenca tutte quelle che incassi tra l'acquisto e la vendita (o la scadenza), lorde e nette.
- **Lo scarto di emissione va al contrario rispetto al BOT.** Nel BOT l'imposta sul disaggio si paga all'acquisto e una parte torna indietro se vendi prima. Nel BTP all'acquisto ricevi un **credito** sullo scarto già maturato, e alla vendita o a scadenza la banca **trattiene** l'imposta sullo scarto maturato fino a quel giorno. Per questo nel risultato le righe hanno nomi diversi e importi negativi.
- **Il rateo è tassato**: credito del 12,5% sul rateo che paghi al venditore, trattenuta del 12,5% su quello che ti paga il compratore se vendi prima della scadenza.
- **Asta**: se compri un BTP in asta, inserisci come data la data di regolamento e come prezzo quello di aggiudicazione. Nelle riaperture (asta di un BTP già in circolazione) paghi anche il rateo maturato dall'ultimo stacco, che il calcolatore aggiunge come per il MOT. Controlla che le commissioni precompilate dal profilo bancario corrispondano a quelle che la tua banca applica ai BTP in asta.

## Esempio completo: acquisto sul MOT e rimborso a scadenza

**BTP 3,35% Lug 2029** (ISIN IT0005584849): emesso il 1° marzo 2024 a **99,82**, scade il 1° luglio 2029, paga una cedola semestrale di **1,675 €** ogni 1° gennaio e 1° luglio per ogni 100 € di nominale.

| Parametro | Valore |
|---|---|
| Mercato | MOT |
| Data regolamento | 29/10/2026 (ordine del 27/10 + 2 giorni lavorativi) |
| Prezzo acquisto (corso secco) | 99,18 |
| Lotto nominale | 10.000 € (100 BTP) |
| Commissioni acquisto | 0,10% — minimo 5 € — nessun massimo, nessun costo fisso |
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

Il rateo non è un costo: lo recuperi con la prima cedola, che incassi per intero. I due crediti sono importi che la banca ti riconosce subito e che pareggiano le tasse che pagherai sulla cedola intera e sullo scarto alla scadenza.

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

Prezzo di carico e di scarico non contengono lo scarto maturato, che è già tassato a parte: così ogni euro di guadagno sul prezzo è tassato una sola volta. Il prezzo di carico comprende anche le commissioni, quindi riducono la plusvalenza. Il rateo non entra mai nel capital gain. Il perché di ogni riga è spiegato in **[Approfondimenti sul Calcolatore BOT](/guides/calcolatore-approfondimenti)**: le formule sono le stesse.

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
| **Netto** | **2,958%** | **3,004%** |

Il **rendimento composto** è il tasso interno di rendimento (TIR) calcolato su tutti i flussi con le loro date: il pagamento iniziale, ogni cedola e il rimborso. Per un BTP è il numero da guardare, perché tiene conto che le cedole arrivano prima della scadenza. Il **rendimento semplice** divide il guadagno per il capitale e per gli anni, senza badare a quando arrivano i soldi.

## Stesso BTP, venduto prima della scadenza

Stessi dati di acquisto, ma attivi **Vendita anticipata**: vendi con regolamento il 15/12/2027 a un corso secco di **100,50**, con le stesse commissioni dell'acquisto. Il piano cedole si ferma alle due cedole del 2027 (293,13 € nette) e la sezione di vendita si allunga:

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

Vendendo prima dello stacco del 1° gennaio non incassi quella cedola, ma il compratore ti paga la parte maturata finora (il rateo), su cui la banca trattiene il 12,5% come su una cedola. Con 4 trimestri di bollo (19,92 €) il guadagno netto è **408,67 €**, con un rendimento netto composto del **3,671%**: più alto del rimborso a scadenza perché in questo esempio il prezzo è salito da 99,18 a 100,50 in poco più di un anno.

Se nel risultato il piano cedole è vuoto vuol dire che vendi prima del primo stacco: l'unico interesse che incassi è il rateo pagato dal compratore.

## Consigli pratici

- **Guarda il rendimento netto composto**, non la cedola: un BTP con cedola alta comprato sopra 100 può rendere meno di uno con cedola bassa comprato sotto 100.
- **Confronta più date di vendita** per lo stesso titolo: il rateo e lo scarto si spostano dal compratore al venditore giorno per giorno, il prezzo di mercato no.
- **Per lotti piccoli** il minimo di commissione e il bollo pesano di più: prova a cambiare il lotto nominale per vedere da dove in su la spesa diventa trascurabile.
- **Inserisci le minusvalenze** che hai nello zainetto: riducono l'imposta sulla plusvalenza, come per i BOT.

---

Torna a **[Cos'è un BTP](/guides/cosa-e-un-btp)** per i concetti, o a **[Sei Nuovo? Inizia Qui](/guides/inizia-qui)** per i passi pratici.
