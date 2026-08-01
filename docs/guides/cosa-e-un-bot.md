---
title: Cos'è un BOT
description: Obbligazioni, Titoli di Stato, disaggio e rendimento spiegati dall'inizio.
icon: bi-info-circle
order: 0
---

# Cos'è un BOT

## Partiamo dall'inizio: cos'è un'obbligazione

Un'**obbligazione** è, nella sua forma più semplice, un prestito. Invece di andare in banca, un'azienda o uno Stato emette un titolo che chiunque può comprare: il compratore presta i soldi, e l'emittente si impegna a restituirli alla scadenza, aggiungendo una remunerazione (interesse) per il prestito.

- Se l'obbligazione è emessa dallo **Stato italiano** si chiama **Titolo di Stato**.
- Se è emessa da un'**azienda privata** si chiama **Corporate Bond** (*bond* è semplicemente la parola inglese per *obbligazione*).

## I Titoli di Stato italiani

Lo Stato italiano emette diverse tipologie di titoli di Stato, ciascuna con caratteristiche diverse di durata e modalità di rendimento:

| Sigla | Nome | Durata | Cedole |
|---|---|---|---|
| **BOT** | Buono Ordinario del Tesoro | fino a 12 mesi | nessuna (zero-coupon) |
| **BTP** | Buono del Tesoro Poliennale | da 3 a 50 anni | semestrali, tasso fisso |
| **BTP Valore / BTP Italia / BTP Più** | Varianti del BTP | da 4 a 10 anni | crescenti o indicizzate |
| **CCT / CCTeu** | Certificato di Credito del Tesoro | 7 anni | variabili (Euribor + spread) |

Questo sito si concentra per ora sui **BOT** — la scelta più adatta per chi vuole parcheggiare liquidità per un periodo breve (da 3 a 12 mesi) con piena garanzia dello Stato.

## Cos'è un BOT

Il **Buono Ordinario del Tesoro (BOT)** è un titolo di Stato a brevissimo termine:

- Durata **massima di 12 mesi** (esistono BOT trimestrali, semestrali e annuali).
- È uno strumento **zero-coupon**: **non paga cedole** durante la vita del titolo.
- Il guadagno deriva esclusivamente dal **disaggio**, cioè dalla differenza tra il prezzo a cui lo si acquista (sempre inferiore a 100) e il valore di rimborso fisso di **100 euro** per ogni BOT.

> **Esempio:** acquisti un BOT annuale a 97,20 €. Alla scadenza il MEF ti rimborsa 100,00 €.
> Il tuo guadagno **lordo** è 2,80 € per ogni BOT.

### Taglio minimo e lotti

Ogni BOT ha un **valore nominale di 100 €**. Le banche impongono un **lotto minimo di 1.000 €** (10 BOT), acquistabile per multipli di 1.000 €.

## Rendimento lordo e rendimento netto

### Rendimento lordo

Il rendimento lordo è il guadagno prima delle imposte, espresso come tasso annualizzato:

```
rendimento_lordo = (100 / prezzo_acquisto) ^ (365 / giorni_a_scadenza) − 1
```

Questo è il rendimento che trovi nel [Catalogo BOT](/bonds/) e nelle quotazioni di mercato.

### L'imposta sostitutiva agevolata al 12,5%

I Titoli di Stato italiani godono di una **tassazione agevolata**: l'imposta sostitutiva sul disaggio è del **12,5%**, contro il 26% applicato ai Corporate Bond e alla maggior parte degli altri strumenti finanziari.

L'imposta si calcola sul **disaggio pro-quota**: la quota di disaggio maturata proporzionalmente al tempo di possesso rispetto alla durata totale del BOT.

### Rendimento netto

Il rendimento netto è il guadagno reale dopo le imposte:

```
disaggio_lordo   = 100 − prezzo_emissione
imposta_disaggio = disaggio_lordo × 12,5%
rendimento_netto = ((100 − imposta_disaggio) / prezzo_acquisto) ^ (365 / giorni_a_scadenza) − 1
```

> Il **Catalogo BOT** mostra sia il rendimento lordo che quello netto per ogni BOT in circolazione. È pensato per una scelta rapida: ti permette di confrontare i BOT disponibili in base all'orizzonte temporale e al rendimento indicativo.
>
> Per un calcolo più preciso — che includa le commissioni bancarie, l'imposta di bollo e tutti i dettagli del tuo investimento — usa il **Calcolatore BOT** con il BOT che hai scelto dal catalogo.

## Per orizzonti più lunghi: i BTP

Il BOT è lo strumento ideale per **orizzonte temporale fino a 12 mesi**. Se vuoi investire per periodi più lunghi, dovresti considerare i **BTP** (Buoni del Tesoro Poliennali), che pagano cedole semestrali e hanno scadenze da 3 a 50 anni. Più lungo è l'orizzonte, maggiore è in genere il rendimento offerto (curva dei tassi crescente in condizioni normali di mercato).

---

Ora che sai cos'è un BOT, torna alla guida **[Sei Nuovo? Inizia Qui](/guides/inizia-qui)** per i passi pratici.
