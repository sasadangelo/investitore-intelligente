---
title: "Esempi di calcolo: BOT"
description: Due BOT riga per riga con i numeri del calcolatore, uno comprato sul MOT e tenuto a scadenza, uno comprato in asta e venduto prima.
icon: bi-journal-check
order: 20
---

# Esempi di calcolo: BOT

Ogni esempio mostra il risultato del **[Calcolatore Obbligazioni](/calculator/)** riga per riga, con il calcolo che c'è dietro. Cosa significa ogni riga è spiegato nella guida **[Calcolatore Obbligazioni](/guides/calcolatore)**.

[TOC]

## BOT Feb24 comprato sul MOT e tenuto a scadenza

**BOT Feb24 A**, comprato sul MOT con regolamento il 01/03/2023 e tenuto fino alla scadenza del 14/02/2024.

| Parametro | Valore |
|---|---|
| Mercato | MOT |
| Data emissione | 14/02/2023 |
| Data scadenza | 14/02/2024 |
| Prezzo emissione | 96,877 |
| Data regolamento | 01/03/2023 |
| Prezzo acquisto | 96,846 |
| Lotto nominale | 5.000 € (50 BOT) |
| Commissioni acquisto | 0,24% — minimo 3 € — fissa 3,50 € |
| Vendita anticipata | No (rimborso a scadenza) |

### Acquisto

| Riga | Come si calcola | Valore |
|---|---|---|
| Quantità | 5.000 / 100 | 50 |
| Importo secco | 50 × 96,846 | 4.842,30 € |
| Commissioni | max(4.842,30 × 0,24%; 3 €) | 11,62 € |
| Commissioni fisse | — | 3,50 € |
| Disaggio pro-quota | 100 − prezzo teorico 97,00534 (vedi Capital Gain) | 2,99466 |
| Imposta disaggio | 2,99466 × 12,5% × 50 | 18,72 € |
| **Totale pagato** | 4.842,30 + 11,62 + 3,50 + 18,72 | **4.876,14 €** |

### Capital Gain

| Riga | Come si calcola | Valore |
|---|---|---|
| Prezzo teorico acquisto | 96,877 + 3,123 × (15/365) | 97,00534 |
| Prezzo teorico vendita (scadenza) | 96,877 + 3,123 × (365/365) | 100,00000 |
| Prezzo di carico | 96,846 + (11,62 + 3,50) / 50 − (97,00534 − 96,877) | 97,02014 |
| Prezzo di scarico | 100 − 0 / 50 − (100 − 96,877) | 96,87700 |
| Plus/Minus valenza (per 100 nominale) | 96,87700 − 97,02014 | −0,14314 |
| Plus/Minus realizzata | −0,14314 × 50 | −7,16 € |
| Riduzione imponibile TdS (48,08%) | 7,16 × 48,08% | 3,44 € |
| Minus valenza da zainetto | | 3,44 € |
| **Imposta sulla plusvalenza** | minusvalenza → nessuna imposta | **0,00 €** |

Il prezzo di scarico coincide con il prezzo di emissione (96,877): a scadenza tutto lo scarto è maturato e viene tolto, perché è già tassato a parte. Il risultato è una piccola minusvalenza, dovuta alle commissioni e al prezzo pagato un po' sopra il teorico: nessuna imposta, e la minusvalenza va nello zainetto.

### Rimborso a scadenza

| Riga | Come si calcola | Valore |
|---|---|---|
| Importo secco | 50 × 100 | 5.000,00 € |
| Commissioni | il rimborso non è una vendita | 0,00 € |
| Imposta disaggio rimborsata | a scadenza non c'è nulla da rimborsare | 0,00 € |
| Imposta sulla plusvalenza | minusvalenza | 0,00 € |
| **Totale ricevuto** | 5.000,00 + 0,00 − 0,00 | **5.000,00 €** |

A scadenza la banca accredita solo il nominale, 5.000 €: l'imposta sul disaggio l'hai già pagata tutta all'acquisto (18,72 €), sulla parte di disaggio che sarebbe maturata mentre il BOT era tuo. L'imposta disaggio rimborsata c'è solo se vendi prima della scadenza: in quel caso il compratore ti restituisce la parte che riguarda i giorni dopo la vendita.

### Riepilogo

| Riga | Come si calcola | Valore |
|---|---|---|
| Guadagno lordo | 5.000,00 − 4.842,30 | 157,70 € |
| Guadagno netto (pre-bollo) | 157,70 − 18,72 (imposta disaggio) − 15,12 (commissioni) | 123,86 € |
| **Guadagno netto** | 123,86 − 9,84 (bollo) | **114,02 €** |

| Rendimento | Semplice | Composto |
|---|---|---|
| Lordo | 3,396% | 3,399% |
| Netto (pre-bollo) | 2,649% | 2,650% |
| **Netto** | **2,439%** | **2,440%** |

## BOT Apr25 comprato in asta e venduto prima della scadenza

**BOT Apr25 A**, comprato all'asta con regolamento il 12/04/2024 e venduto sul MOT con regolamento il 01/04/2025, 13 giorni prima della scadenza del 14/04/2025. Mostra due righe che compaiono solo in questo caso: l'imposta sul disaggio che ti viene rimborsata e il capital gain di un acquisto in asta.

| Parametro | Valore |
|---|---|
| Mercato di acquisto | Asta |
| Data emissione | 12/04/2024 |
| Data scadenza | 14/04/2025 |
| Prezzo emissione | 96,524 |
| Data regolamento acquisto | 12/04/2024 |
| Prezzo acquisto | 96,524 (il prezzo d'asta) |
| Lotto nominale | 5.000 € (50 BOT) |
| Commissioni acquisto | 0,15% del nominale |
| Vendita anticipata | Sì: regolamento 01/04/2025, prezzo 99,70 |
| Commissioni vendita | 0,24% — minimo 3 € — fissa 3,50 € |
| Bollo | Trimestrale |

### Acquisto

| Riga | Come si calcola | Valore |
|---|---|---|
| Quantità | 5.000 / 100 | 50 |
| Importo secco | 50 × 96,524 | 4.826,20 € |
| Commissioni | in asta si calcolano sul nominale: 5.000 × 0,15% | 7,50 € |
| Commissioni fisse | — | 0,00 € |
| Disaggio pro-quota | in asta è tutto lo scarto: 100 − 96,524 | 3,476 |
| Imposta disaggio | 3,476 × 12,5% × 50 | 21,73 € |
| **Totale pagato** | 4.826,20 + 7,50 + 21,73 | **4.855,43 €** |

In asta paghi subito l'imposta su **tutto** lo scarto, come se dovessi tenere il BOT fino alla scadenza. Vendendo prima, una parte ti torna indietro (vedi la vendita).

### Capital Gain

| Riga | Come si calcola | Valore |
|---|---|---|
| Prezzo teorico acquisto | in asta coincide con il prezzo di emissione | 96,52400 |
| Prezzo teorico vendita | 96,524 + 3,476 × 354 / 367 (giorni fino alla vendita, su quelli di vita del BOT) | 99,87687 |
| Prezzo di carico | 96,524 + 7,50 / 50 − (96,524 − 96,524) | 96,67400 |
| Prezzo di scarico | 99,70 − (11,96 + 3,50) / 50 − (99,87687 − 96,524) | 96,03785 |
| Plus/Minus valenza (per 100 nominale) | 96,03785 − 96,67400 | −0,63615 |
| Plus/Minus realizzata | −0,63615 × 50 | −31,81 € |
| Riduzione imponibile TdS (48,08%) | −31,81 × 48,08% | −15,29 € |
| Minus valenza da zainetto | | 15,29 € |
| **Imposta sulla plusvalenza** | minusvalenza → nessuna imposta | **0,00 €** |

La minusvalenza ha due cause: vendi a 99,70, un po' sotto il prezzo teorico di quel giorno (99,877), e paghi le commissioni di acquisto e di vendita. Non paghi imposte, e 15,29 € vanno nello zainetto: potrai usarli per pagare meno tasse su plusvalenze future.

### Vendita anticipata

| Riga | Come si calcola | Valore |
|---|---|---|
| Importo secco | 50 × 99,70 | 4.985,00 € |
| Commissioni | max(4.985,00 × 0,24%; 3 €) | 11,96 € |
| Commissioni fisse | — | 3,50 € |
| Imposta disaggio rimborsata | disaggio che maturerà dopo la vendita: (100 − 99,87687) × 12,5% × 50 | 0,77 € |
| Imposta sulla plusvalenza | minusvalenza | 0,00 € |
| **Totale ricevuto** | 4.985,00 − 11,96 − 3,50 + 0,77 | **4.970,31 €** |

L'imposta disaggio rimborsata è la parte dell'imposta pagata all'acquisto che riguarda i 13 giorni dopo la vendita: quei giorni di disaggio li matura il compratore, che te la restituisce nel prezzo.

### Imposta di bollo

| Riga | Valore |
|---|---|
| Periodi di possesso | 4 trimestri |
| Stima bollo | 9,83 € |

### Riepilogo

| Riga | Come si calcola | Valore |
|---|---|---|
| Guadagno lordo | 4.985,00 − 4.826,20 | 158,80 € |
| Guadagno netto (pre-bollo) | totale ricevuto − totale pagato = 4.970,31 − 4.855,43 | 114,88 € |
| **Guadagno netto** | 114,88 − 9,83 (bollo) | **105,05 €** |

| Rendimento | Semplice | Composto |
|---|---|---|
| Lordo | 3,393% | 3,394% |
| Netto (pre-bollo) | 2,440% | 2,440% |
| **Netto** | **2,231%** | **2,232%** |

---

Gli esempi con i BTP sono in **[Esempi di calcolo: BTP](/guides/esempi-btp)**.
