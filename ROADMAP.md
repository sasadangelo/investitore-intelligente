# Roadmap — Investitore Intelligente

> Stato attuale (baseline): applicazione Flask con supporto **BOT** (emissioni,
> quotazioni Teleborsa, calcolatore acquisto/vendita, profili commissioni banca).

---

## Fase 1 — Ampliamento dati di mercato BOT *(breve termine)*

### 1.1 Aggiunta nuove banche
- Aggiungere profili commissioni preconfigurati per le principali banche italiane
  (es. Intesa Sanpaolo, UniCredit, Fineco, Banca Mediolanum, ING, Widiba, …).
- Validazione automatica delle fasce commissioni (es. min ≤ max).

### 1.2 Forecast prezzo BOT in emissione
- Dato un nuovo BOT in asta (ISIN, data emissione, scadenza, prezzo nominale 100),
  stimare il **prezzo di emissione atteso** interpolando la curva dei rendimenti
  dei BOT già quotati a scadenze comparabili.
- Input: durata residua, curve tassi attuali.
- Output: rendimento stimato, prezzo teorico di emissione, confronto con aste precedenti della stessa scadenza.

---

## Fase 2 — Supporto BTP a cedola fissa *(medio termine)*

### 2.1 Modello dati BTP
- Estendere `BondDAO` / `BondDTO` con i campi cedola: `nominal_rate`,
  `coupon_frequency` (semestrale per BTP standard), `first_coupon_date`.
- Nuovo `bond_type = "BTP"`.
- Scraper (o import manuale) delle quotazioni BTP da Teleborsa / Borsa Italiana.

### 2.2 Calcolatore BTP
- Nuovo `BtpCalculatorService` che calcola:
  - Prezzo secco + rateo cedola → **prezzo tel quel**.
  - Rendimento a scadenza (**YTM**) con Newton-Raphson o scipy.
  - Rendimento netto (aliquota 12,5 % su cedole e capital gain TdS).
  - Durata finanziaria (Duration di Macaulay e Modified Duration).
  - Imposta di bollo e tasse sul capital gain (logica analoga a BOT).
- UI: form calcolatore dedicato BTP, riuso template `bonds/calculator.html`.

---

## Fase 3 — Autenticazione e ruoli *(medio termine)*

### 3.1 Sistema di login
- Integrare **Flask-Login** con due ruoli: `admin` e `user`.
- Registrazione/login con email + password (hash bcrypt).
- Protezione delle route sensibili con `@login_required`.

### 3.2 Ruolo admin
- Gestione utenti (lista, blocco, reset password).
- Avvio manuale sync quotazioni (attualmente esposto a tutti).
- Visualizzazione log applicazione.

### 3.3 Ruolo utente normale
- Accesso al proprio portafoglio (vedi Fase 4).
- Sola lettura su dati di mercato e calcolatori.

---

## Fase 4 — Gestione portafoglio *(medio termine)*

- Nuovo modello `PortfolioPosition`: utente, bond, quantità, prezzo di carico,
  data acquisto, banca/profilo commissioni.
- Dashboard portafoglio con:
  - Valore corrente (mark-to-market usando ultima quotazione).
  - Guadagno/perdita latente (lordo e netto tasse + bollo).
  - Rendimento medio ponderato del portafoglio.
  - Scadenzario (BOT/BTP in scadenza nei prossimi 30/90/180 giorni).
- Storico operazioni (acquisti, vendite, cedole incassate).
- Export portafoglio in CSV/PDF.

---

## Fase 5 — BTP Valore e BTP a step *(medio-lungo termine)*

- Supporto per BTP con struttura cedola crescente a gradini (es. BTP Valore):
  - Modello `CouponSchedule`: lista di `(data_inizio, data_fine, tasso)`.
  - Calcolo YTM con flussi cedolari non uniformi.
  - Calcolo del **premio fedeltà** (extra % a scadenza per chi detiene dall'emissione).
- Scraper dedicato alle schede BTP Valore su Borsa Italiana / MEF.
- Calcolatore con timeline cedole e simulazione reinvestimento.

---

## Fase 6 — Dati macroeconomici *(lungo termine)*

### 6.1 Inflazione
- Fonte dati: **ISTAT** (Italia) e **BLS / FRED** (USA) via API pubblica o scraping.
- Storico mensile CPI Italia e USA.
- Visualizzazione grafico inflazione vs rendimento netto BOT/BTP → rendimento
  **reale** al netto dell'inflazione.

### 6.2 PIL
- Fonte dati: **ISTAT** (Italia) e **BEA / FRED** (USA).
- Storico PIL reale YoY.
- Dashboard macro: PIL + Inflazione + Tassi su unico grafico.

### 6.3 Tassi di interesse
- Tassi BCE (refi rate, deposit facility) da **BCE Statistical Data Warehouse** API.
- Tassi Fed Funds da **FRED** API.
- Curva dei rendimenti (yield curve) italiana da MEF/Banca d'Italia.
- Visualizzazione curva e storico tassi → contesto per valutare convenienza BOT/BTP rispetto ai tassi risk-free.

---

## Fase 7 — Corporate Bond *(lungo termine)*

- Nuovo `bond_type = "Corporate"` con campi aggiuntivi:
  - Emittente, settore, rating (S&P / Moody's / Fitch).
  - Aliquota fiscale 26 % (no agevolazione TdS).
  - Eventuale clausola callable/putable.
- Scraper quotazioni obbligazioni corporate da MOT/ExtraMOT (Borsa Italiana).
- Calcolatore con spread rispetto al BTP benchmark (Z-spread).
- Filtro per rating, scadenza, rendimento minimo.

---

## Suggerimenti tecnici aggiuntivi (Bob's recommendations)

| Area | Proposta |
|---|---|
| **API REST** | Esporre i calcolatori come endpoint JSON (`/api/v1/bonds/{isin}/calculate`) per integrazioni future (app mobile, spreadsheet). |
| **Task scheduler** | Sostituire il sync manuale con **APScheduler** o **Celery** per aggiornare quotazioni ogni giorno in automatico. |
| **Cache quotazioni** | Aggiungere TTL cache (Redis o `cachetools`) per evitare scraping eccessivo verso Teleborsa. |
| **Test coverage** | Aumentare la copertura unitaria di `BotCalculatorService` e futura `BtpCalculatorService` con `pytest-parametrize` su casi edge. |
| **Alert scadenze** | Notifica email/Telegram quando un BOT/BTP in portafoglio scade entro N giorni. |
| **Benchmark** | Sezione comparativa: rendimento netto BOT/BTP vs conto deposito, ETF obbligazionario, inflazione. |

---

## Priorità riepilogativa

```
Fase 1  ████████████████████  (quick wins, estende funzionalità esistenti)
Fase 2  ████████████████      (valore alto per l'utente medio)
Fase 3  ████████████          (necessaria prima di Fase 4)
Fase 4  ████████████          (feature differenziante)
Fase 5  ████████              (nicchia BTP Valore)
Fase 6  ██████                (contesto macro)
Fase 7  ████                  (mercato più complesso)
```
