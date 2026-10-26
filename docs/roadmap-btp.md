# Roadmap tecnica — Supporto BTP a tasso fisso

> Ambito: solo BTP a **tasso fisso** (cedola costante, `Tipo Obbl. = "Cedola Fissa"` nel foglio
> `Emissioni`). BTP Valore, BTP Italia, BTP Più e ogni titolo a cedola *STEP* sono **esclusi**
> da questa fase e restano nella Milestone 4 di [`ROADMAP.md`](../ROADMAP.md).

**Riferimento di calcolo**: `ObbligazioniTF v5.0.ods` (foglio `Bond` per la logica finanziaria,
foglio `Emissioni` per l'anagrafica titoli). I riferimenti a celle/colonne in questo documento
sono presi da quel file e servono solo da guida concettuale: l'implementazione in Python non deve
replicare le formule cella per cella, ma il comportamento che rappresentano.

---

## Punto di partenza — cosa esiste già

`BondDAO` / `BondDTO` ([bond.py](../src/intelligent_investor/models/bond.py),
[bond.py](../src/intelligent_investor/dtos/bond.py)) sono già generici e pronti ad ospitare un
BTP a tasso fisso senza modifiche allo schema:

- `bond_type` accetta già `"BTP"`
- `nominal_rate` (cedola annua %) e `coupon_frequency` (1 = annuale, 2 = semestrale) esistono già
  (oggi sempre 0 per i BOT)
- `tax_rate` (12,5% default) e `redemption_price` esistono già

Quello che **manca** è tutta la logica di calcolo (cedole, rateo, capital gain, TIR a flussi
multipli) e l'anagrafica dei titoli in DB. Il calcolatore BOT attuale
([bot_calculator_service.py](../src/intelligent_investor/services/bot_calculator_service.py))
gestisce solo titoli zero-coupon a 2 flussi (acquisto/rimborso): un BTP ha invece N cedole
intermedie, quindi la sua *logica* (non il suo codice) va generalizzata per gestire flussi
multipli.

In pratica questo significa scrivere un **nuovo** servizio (`BtpCalculatorService`, Fase 4) che
implementa quella logica generalizzata, senza modificare `bot_calculator_service.py`: il codice
BOT esistente resta intatto finché non è dimostrata la parità di risultati descritta nella nota
di design a fine Fase 4. `bot_calculator_service.py` non va quindi "esteso" nel senso di
modificato in place, ma preso come riferimento/modello per la struttura del nuovo servizio.

---

## Fase 1 — Utility: scadenzario cedole e rateo (🔴) ✅

Implementata in [coupon_schedule.py](../src/intelligent_investor/utils/coupon_schedule.py)
(classe `CouponSchedule`, sullo stile stateful di `YieldCalculator`), con test in
[test_coupon_schedule.py](../test/unit/test_coupon_schedule.py).

Nuovo modulo, es. `utils/coupon_schedule.py`, riusabile sia dal calcolatore che dal catalogo.

- **Generazione date cedola**: dato `issue_date`, `maturity_date`, `coupon_frequency`, calcolare
  tutte le date di stacco cedola tra emissione e scadenza (equivalente a `COUPNCD` di
  Excel/LibreOffice, viste nel foglio `Bond` colonna `T`/`U`). Le cedole sono ancorate alla data
  di scadenza e vanno a ritroso (es. scadenza 15/07, semestrale → 15/01 e 15/07 ogni anno).
- **Rateo cedolare (accrued interest)**: quota di cedola maturata tra l'ultima data di stacco e
  una data di regolamento, in ACT/ACT — stessa convenzione già implementata in
  [yield_calculator.py](../src/intelligent_investor/utils/yield_calculator.py) (`yearfrac`,
  basis `ACT_ACT`). Riusare quella funzione, non riscriverla.
- **Cedola lorda/netta per data**: `cedola_lorda = nominal_rate / coupon_frequency` (per 100 di
  nominale), `cedola_netta = cedola_lorda * (1 - tax_rate/100)` — vedi colonne `V`/`W`/`X` del
  foglio `Bond` (rateo cedolare lordo/netto).

## Fase 2 — TIR a flussi multipli (🔴) ✅

Implementata in [yield_calculator.py](../src/intelligent_investor/utils/yield_calculator.py)
(funzione `xirr`), con test in
[test_yield_calculator.py](../test/unit/test_yield_calculator.py).

`YieldCalculator.compound()` era una formula chiusa a 2 flussi (capitale investito →
incasso finale), valida per i BOT ma **non corretta** per un BTP con cedole intermedie: serve un
vero XIRR su una serie di flussi datati (uscita all'acquisto, cedole nette periodiche, incasso
finale a vendita/scadenza).

- Aggiunta a `yield_calculator.py` una funzione `xirr(cashflows: list[tuple[date, float]]) ->
  float` con Newton-Raphson (fallback a bisezione `_xirr_bisection` se non converge), stesso
  criterio di giorni/365 già documentato per l'XIRR dei BOT (ancorato al flusso più vecchio;
  coincide con `YieldCalculator.compound()` nel caso a 2 flussi).
- Il rendimento semplice (non composto) può restare basato su `YEARFRAC`, sommando i flussi netti
  totali sul capitale investito (come oggi in `SummaryResultDTO`, ma con `net_gain` che include
  anche le cedole) — da collegare in Fase 3/4, non ancora integrato in `SummaryResultDTO`.

## Fase 3 — DTO: transazione e `BtpCalculationResultDTO` (🔴) ✅

Implementata in [btp_calculation_result.py](../src/intelligent_investor/dtos/btp_calculation_result.py),
sul modello di [bot_calculation_result.py](../src/intelligent_investor/dtos/bot_calculation_result.py).

Transazione: nata come `BtpTransactionDTO`, copia di `BotTransactionDTO`; i due sono stati poi
unificati in [`BondTransactionDTO`](../src/intelligent_investor/dtos/bond_transaction.py) (vedi la
decisione "Un solo calcolatore per BOT e BTP"). Lo stesso per il riepilogo, ora un solo `SummaryResultDTO`.

`BtpCalculationResultDTO` — sezioni aggiuntive rispetto al BOT:

| Sezione | Contenuto | Riferimento foglio `Bond` |
|---|---|---|
| **Acquisto** | corso secco (clean) + rateo cedolare a carico compratore = prezzo **tel quel** pagato al venditore; nessuna imposta sul rateo stesso (è un semplice trasferimento tra privati) | colonne `Q`/`R` (rateo cedolare acquisto) |
| **Piano cedole** | tabella data/cedola lorda/cedola netta per ogni stacco tra acquisto e vendita/scadenza | righe 3–112 colonne `U`/`V`/`W`/`X` |
| **Capital gain** | plus/minusvalenza sul **solo scarto di prezzo** (prezzo di carico/scarico *al netto* del rateo, che è già tassato come reddito da cedola) — stessa logica di riduzione 48,08% e "zainetto" già implementata per i BOT in `_calc_capital_gain` | colonne `AF`–`AI` |
| **Bollo** | invariato, riuso 1:1 di `_calc_stamp_duty` | — |
| **Riepilogo** | rendimento semplice/composto lordo e netto, ora calcolato sui flussi multipli (Fase 2) invece che a 2 punti | `J4`/`K4` (TIR), `J5`/`K5` (guadagno netto totale) |

## Fase 4 — `BtpCalculatorService` (🔴) ✅

> Dalla Fase 8 questo servizio, quello BOT e `bond_calculator_common.py` sono confluiti in
> [bond_calculator_service.py](../src/intelligent_investor/services/bond_calculator_service.py).
> Il testo sotto descrive la fase come era stata implementata.

Implementata in
[btp_calculator_service.py](../src/intelligent_investor/services/btp_calculator_service.py), con
test in [test_btp_calculator_service.py](../test/unit/test_btp_calculator_service.py).

Le parti realmente comuni con il BOT (commissioni, bollo) sono state estratte in
[bond_calculator_common.py](../src/intelligent_investor/services/bond_calculator_common.py)
(`calc_commission`, `calc_stamp_duty`), usato solo dal nuovo servizio: `bot_calculator_service.py`
non è stato toccato, come richiesto in testa a questo documento, e mantiene la propria copia
privata di `_calc_commission`.

Struttura a metodi privati speculare a `BotCalculatorService`:

1. `_calc_purchase` — prezzo tel quel (clean + rateo), commissioni via `calc_commission` del
   modulo condiviso.
2. `_calc_coupon_schedule` — usa Fase 1 per generare le cedole nette incassate durante il possesso
   (stacchi in `(purchase_date, sale_date]`).
3. `_calc_sale` — prezzo di vendita/rimborso tel quel (clean + rateo a favore del venditore).
4. `_calc_capital_gain` — riuso concettuale della logica BOT (riduzione TdS, zainetto), applicata
   allo scarto di prezzo *clean* (al netto delle commissioni per unità). Per il BTP il capital gain
   è sempre calcolato (mai `None`, anche per acquisti in asta).

   > ⚠️ **Corretto in Fase 8.** L'implementazione originale assumeva che per un BTP non servisse il
   > prezzo teorico. È vero solo per i BTP emessi alla pari o sopra: per quelli emessi **sotto la
   > pari** il foglio `Bond` tratta lo scarto di emissione come per i BOT (prezzo teorico, corso
   > super secco, 12,5% sul disaggio maturato) e calcola il capital gain al netto del disaggio.
   > Al 25/10/2026 sono 86 dei 108 BTP in vita nel DB.
5. `_calc_stamp_duty` — riuso diretto di `calc_stamp_duty` del modulo condiviso (stessa base di
   calcolo, stessa aliquota 0,20%/anno).
6. `_calc_summary` — rendimento semplice/composto con XIRR multi-flusso (Fase 2).

## Fase 5 — Catalogo BTP (🟡) ✅

Estesa la pagina/servizio di catalogo esistente per includere i BTP. Dopo la separazione tra
voci di menù e CRUD, il codice vive in
[catalogue_controller.py](../src/intelligent_investor/controllers/catalogue_controller.py)
(parametri HTTP), [catalogue_service.py](../src/intelligent_investor/services/catalogue_service.py)
(filtro, abbinamento quotazioni, ordinamento), [bond_yields.py](../src/intelligent_investor/services/bond_yields.py)
(rendimenti) e [pagination.py](../src/intelligent_investor/utils/pagination.py), con test in
[test_catalogue_service.py](../test/unit/test_catalogue_service.py),
[test_bond_yields.py](../test/unit/test_bond_yields.py) e
[test_pagination.py](../test/unit/test_pagination.py):

- Filtro per `bond_type` (dropdown "Tutte"/"BOT"/"BTP Tasso Fisso" in
  [catalogue/index.html](../src/intelligent_investor/templates/catalogue/index.html), query param
  `?bond_type=`; opzioni limitate ai tipi realmente in uso per ora, vedi `CATALOG_FILTERS`).
- Rendimento corrente stimato (`btp_yields`): scadenzario cedole (Fase 1) sui flussi
  residui da oggi a scadenza, ancorati all'ultima quotazione MOT (`BondQuoteDAO`) come esborso
  odierno (prezzo tel quel = corso secco + rateo), risolto con XIRR multi-flusso (Fase 2). Il netto
  applica anche un'imposta indicativa di capital gain sullo scarto di prezzo clean, coerente con
  la semplificazione già usata per il rendimento BOT del catalogo (nessuna commissione/bollo,
  ignoti a livello di catalogo).
- `bond_yields` fa da dispatcher tra la formula BTP e quella BOT (`bot_yields`), usato sia dal
  catalogo sia dal dettaglio del bond (`bonds.detail`).
- Paginazione (`?page=&per_page=`, opzioni 10/20/50/100, default 20 — `paginate`) e ordinamento
  (`?sort=maturity|yield_gross|yield_net&dir=asc|desc`, header di colonna cliccabili — `sort_entries`,
  `_toggle_sort_dir`) aggiunti dopo l'import reale dei 108 BTP (Fase 6), necessari per una tabella
  di quella dimensione. I titoli senza rendimento calcolato (nessuna quotazione MOT — vedi Fase 7)
  vanno sempre in fondo quando si ordina per rendimento, indipendentemente dalla direzione.

## Fase 6 — Import anagrafica BTP a tasso fisso dal foglio `Emissioni` (🔴) ✅

Eseguito un import una-tantum tramite uno script (`scripts/import_btp_emissioni.py`, rimosso dal
repository dopo l'uso: era un bulk-load pensato per popolare l'anagrafica una sola volta, non uno
strumento ricorrente — i BTP futuri arriveranno via sync automatico, vedi Fase 7, e verranno
rifiniti a mano dalle pagine CRUD esistenti, esattamente come già avviene oggi per i BOT).

Il foglio `Emissioni` del file di riferimento contiene l'elenco di tutti i titoli censiti
(BOT, BTP a tasso fisso, BTP Valore/Futura a cedola STEP, CCT, ecc.). L'import ha selezionato
**solo** il sottoinsieme:

```
Tipo Obbl. (col. L) = "Cedola Fissa"  AND  Tasso (col. C) ≠ "STEP"
```

(gli STEP, es. BTP Valore/Futura, restano fuori — vedi Milestone 4).

Mappatura colonne `Emissioni` → `BondDAO`/`BondDTO`:

| Colonna `Emissioni` | Campo | Note |
|---|---|---|
| A — NOME | `name` | |
| B — ISIN | `isin` | |
| C — TASSO | `nominal_rate` | valore percentuale → float (es. `3,600%` → `3.6`) |
| D — NUMERO CEDOLE ANNUALI | `coupon_frequency` | 1 o 2 |
| F — DATA EMISSIONE | `issue_date` | |
| G — PREZZO EMISSIONE | `issue_price` | |
| H — SCADENZA | `maturity_date` | |
| I — PREZZO A SCADENZA | `redemption_price` | tipicamente 100 |
| M — TASSAZIONE | `tax_rate` | tipicamente 12,5% |
| — | `bond_type` | costante `"BTP"` |

Colonne **non** mappate in questa fase: `E` (Data prima cedola — serve per la prima cedola
irregolare, vedi Fase 10), `N` (Premio Fedeltà, solo BTP Valore/Futura), `R`–`AK`
(scadenzario STEP), `J`/`K` (quotazione MOT — va nel catalogo quotazioni esistente, non
nell'anagrafica).

**Import reale eseguito**: 108 BTP a tasso fisso importati in `data/investor.db` da
`ObbligazioniTF v5.0.ods` (non presente in questo repository). Durante l'import è emerso un ISIN
duplicato nel file sorgente (due titoli diversi condividevano lo stesso ISIN, corretto a mano
prima dell'import reale) — evidenzia perché il passo sotto resta necessario prima di considerare
i dati affidabili in produzione.

**Resta da fare**: validazione manuale di un campione contro il sito MEF prima di considerare i
dati affidabili per l'uso in produzione.

## Fase 7 — Sync quotazioni MOT per BTP (🟡) ✅

Dopo l'import dell'anagrafica (Fase 6), i 108 BTP importati non avevano alcuna quotazione
(`BondQuoteDAO`): il catalogo (Fase 5) mostrava correttamente "—" al posto di rendimento
lordo/netto perché `_calc_bond_yields` richiede un `last_price` che non esisteva per nessun BTP.

Lavoro svolto:
1. [`teleborsa_btp_client.py`](../src/intelligent_investor/clients/teleborsa_btp_client.py) —
   sullo stile di `teleborsa_bot_client.py`, scarica la lista da
   `https://www.teleborsa.it/Quotazioni/BTP` e visita la pagina di dettaglio di ogni riga
   (`https://www.teleborsa.it/obbligazioni-titoli-di-stato/<slug>`). Filtra solo i BTP a tasso
   fisso: il campo "Tipo bond" della pagina di dettaglio deve valere "Tasso Fisso" **e** il nome
   non deve iniziare per "Btpi" né contenere "Italia" — Teleborsa etichetta "Tasso Fisso" anche i
   BTP€i e i BTP Italia, che in realtà sono indicizzati all'inflazione e non hanno un flusso
   cedolare nominale fisso rappresentabile da `BondDTO.nominal_rate`. Step-rate e zero-coupon
   (Futura, Più, Valore, Coupon Strip, ...) sono esclusi dallo stesso campo "Tipo bond". Il tasso
   nominale annuo è risolto con una catena di priorità: campo "Cedola annuale" (se valorizzato) →
   "Cedola in corso" moltiplicato per la frequenza cedolare → parsing dal nome del titolo
   (copre la nomenclatura legacy tipo "Btp-1Ag34 5", dove nessuno dei due campi è popolato).
2. Registrato in `ClientRegistry` con la sorgente `"teleborsa_btp"`; `BondSyncService.sync()`
   riusato così com'è, nessuna modifica necessaria.
3. UI: un solo bottone "Aggiorna Quotazioni" in
   [catalogue/index.html](../src/intelligent_investor/templates/catalogue/index.html) sincronizza sia BOT
   che BTP in un'unica passata SSE (rotta `catalogue.refresh_quotes_stream`); il progresso di ciascuna
   sorgente è scalato nella propria metà della barra 0-100%.
4. Test in [test_teleborsa_btp_client.py](../test/unit/test_teleborsa_btp_client.py) sui parse
   helper e sul filtraggio end-to-end di `fetch()` (rete mockata).

Verificato in locale con un sync live completo: 107 dei 108 BTP già in anagrafica hanno ricevuto
una quotazione, il catalogo mostra ora prezzo e rendimento lordo/netto invece di "—".

Nota: quando Teleborsa non fornisce il prezzo di emissione di un BTP nuovo, il client usa la pari
come segnaposto (`teleborsa_btp_client.py`). Con la Fase 8 questo diventa rilevante: un BTP
emesso sotto la pari ma salvato a 100 risulterebbe senza scarto di emissione. Vedi Fase 8.

---

# Da fare

Le fasi da 8 in poi sono numerate **nell'ordine in cui vanno eseguite** e riguardano solo i BTP a
tasso fisso. Sono emerse dal confronto tra il servizio e il foglio `Bond` del file di riferimento.
Le due sezioni "Per ogni fase" valgono per tutte, comprese quelle già completate.

## Per ogni fase — Guide utente

Le guide in `docs/guides/` si aggiornano **insieme** alla fase che cambia ciò che l'utente vede o
i numeri che legge, non in un unico blocco alla fine. Una fase che tocca la UI o i calcoli non è
completa finché la guida corrispondente non è aggiornata.

**Lettore di riferimento**: chi arriva sul sito per la prima volta e vuole capire se e quale
titolo di Stato comprare, senza conoscere il gergo. Quindi:
- partire dalla domanda pratica ("quanto guadagno davvero?", "perché il netto è più basso del
  lordo?"), non dalla formula;
- spiegare ogni termine tecnico la prima volta che compare (cedola, rateo, corso secco/tel quel,
  scarto di emissione, zainetto, duration), con un rimando alla guida che lo approfondisce;
- un esempio numerico completo con un titolo reale, come quello già presente per il BOT in
  [calcolatore.md](../docs/guides/calcolatore.md);
- stile coerente con [cosa-e-un-bot.md](../docs/guides/cosa-e-un-bot.md) e
  [inizia-qui.md](../docs/guides/inizia-qui.md).

**Arretrato da recuperare subito**, in parallelo alle fasi (le fasi 5–7 sono complete ma le guide
sono ferme ai soli BOT):
- [catalogo.md](../docs/guides/catalogo.md) — si intitola ancora "Catalogo BOT": aggiungere i BTP,
  il filtro per tipo, l'ordinamento per rendimento, il bottone "Aggiorna Quotazioni" e il
  bottone "Gestisci" (lista CRUD separata dal catalogo).
- ✅ [cosa-e-un-obbligazione.md](../docs/guides/cosa-e-un-obbligazione.md) — guida di partenza: cos'è
  un'obbligazione, parole chiave, rischi, tasse, dove si compra, e la mappa delle famiglie (BOT, BTP a
  tasso fisso, BTP a cedole crescenti e indicizzati, CCTeu, titoli esteri, corporate). Le guide BOT e
  BTP partono da lì. **Regola**: quando il sito gestirà una nuova famiglia (Milestone 4 step-up,
  Milestone 5 corporate, ...), la sua guida si collega dalla tabella "Le famiglie di obbligazioni",
  dove "non ancora" diventa ✅.
- ✅ [cosa-e-un-btp.md](../docs/guides/cosa-e-un-btp.md) — creata in Fase 8: cedola, corso secco e
  tel quel, rateo, tasse, scarto di emissione con esempio numerico.
- [inizia-qui.md](../docs/guides/inizia-qui.md) — percorso di lettura che includa i BTP.

**Guide di ogni fase** (dettagli nella voce "Guide" della fase):

| Fase | Guida |
|---|---|
| 8 — Scarto di emissione | ✅ `cosa-e-un-btp.md` (la parte per `calcolatore-btp.md` passa alla Fase 11) |
| 9 — Rateo: convenzione e imposte | ✅ `cosa-e-un-btp.md`, `calcolatore.md`, `calcolatore-approfondimenti.md` (la parte per `calcolatore-btp.md` passa alla Fase 11) |
| 10 — Prima cedola irregolare | `cosa-e-un-btp.md` |
| 11 — Calcolatore BTP in pagina | `calcolatore-btp.md` (nuova), con esempio completo |
| 12 — Duration modificata | `cosa-e-un-btp.md`, `catalogo.md` |
| 13 — Confronto rendimenti | `confronto-rendimenti.md` (nuova) |
| 14 — Rifiniture | `calcolatore-btp.md`, guida banche |

## Per ogni fase — Test

Sul modello di `test/unit/test_bot_calculator_service.py` e delle fixture in
`test/unit/fixtures/`:
- Fixture parametriche per il calcolatore con casi noti (titolo tenuto a scadenza, vendita
  anticipata prima/dopo uno stacco cedola, titolo acquistato sopra/sotto la pari).
- Test dedicati per lo scadenzario cedole (Fase 1) e per l'XIRR multi-flusso (Fase 2), inclusi
  casi limite (acquisto lo stesso giorno di uno stacco, scadenza con un'unica cedola residua).
- Valori attesi calcolati a mano o cross-verificati contro il foglio `Bond` del file di
  riferimento per almeno 2–3 titoli reali, tra cui obbligatoriamente:
  - un BTP emesso **sotto la pari**, tenuto a scadenza e comprato sia sotto sia sopra il prezzo
    teorico (Fase 8);
  - una **vendita anticipata** a metà periodo cedolare (Fase 9);
  - un acquisto in asta di un BTP con **prima cedola irregolare** (Fase 10).

## Decisione di design — un solo calcolatore per BOT e BTP

Un BOT è, matematicamente, un BTP con `coupon_frequency = 0`: nessuna cedola, nessun rateo, un
solo flusso all'acquisto e uno a scadenza/vendita. `BondDAO`/`BondDTO` sono già unificati.

Finché il calcolo BTP ignorava lo scarto di emissione, le due logiche fiscali sembravano diverse
(disaggio per il BOT, capital gain sul prezzo clean per il BTP). La Fase 8 aggiunge al BTP
proprio la logica del BOT (prezzo teorico, disaggio maturato, 12,5% sul disaggio): da lì in poi il
calcolo BOT è il caso senza cedole del calcolo BTP, come nel foglio `Bond`, che usa un solo foglio
per tutti i tipi (selettore `F6`).

**Decisione**: un solo servizio e un solo set di DTO. L'unificazione si fa **dentro la Fase 8**,
non dopo, per non scrivere la logica del disaggio due volte.

- **Già fatto** ✅ — `BotTransactionDTO` e `BtpTransactionDTO` avevano gli stessi campi e sono
  diventati un solo `BondTransactionDTO`; `BtpSummaryResultDTO` è stato sostituito da
  `SummaryResultDTO`. Rinomina pura, nessun calcolo è cambiato.
- **Fatto in Fase 8** ✅ — servizio e risultato unici, con prova di parità con il BOT (vedi Fase 8).

Unico punto che dipende dal tipo di titolo: la **maturazione del disaggio**, che nel foglio `Bond`
segue regole diverse (BOT: lineare in giorni dall'emissione, `F29` con `F6=3`; BTP: YEARFRAC
ACT/ACT dalla data fiscale di emissione con la regola del 1997, `F6=2`; zero coupon: composta,
`F6=1`). Va isolata in una piccola funzione scelta per tipo. Restano inoltre i due casi
particolari già noti del BOT: capital gain `None` per acquisti in asta e `bond_id = 0` per i BOT
inseriti a mano.

## Fase 8 — Calcolatore unico e scarto di emissione (🔴) ✅

**Fatto:**
- [bond_calculator_service.py](../src/intelligent_investor/services/bond_calculator_service.py)
  (`BondCalculatorService`) e
  [bond_calculation_result.py](../src/intelligent_investor/dtos/bond_calculation_result.py)
  (`BondCalculationResultDTO`) sostituiscono i servizi e i DTO BOT e BTP, e
  `bond_calculator_common.py`. La regola dello scarto è isolata in `_BotDiscountRule` e
  `_CouponBondDiscountRule`; `discount_tax` ha segno (+ pagata/rimborsata per il BOT, − credito/
  trattenuta per il BTP), come nelle celle `K27`/`K39`.
- **Parità con il BOT**: i 5 casi di `test_bot_calculator_service.py` passano sul nuovo servizio,
  e un confronto su 5.000 transazioni BOT casuali ha dato risultati **identici bit per bit** a
  quelli del vecchio `BotCalculatorService` prima di rimuoverlo.
- **Confronto con il foglio `Bond`**: 5 casi reali in `test/unit/fixtures/btp_calculator_case_*.json`
  (Dc32 comprato sopra e sotto il prezzo teorico e venduto prima della scadenza, Mg33 emesso sopra
  la pari, Nv26 emesso nel 1996), con valori attesi ricavati replicando le formule cella per
  cella; le chiavi riportano la cella. Tutti i campi coincidono.
- Commissioni calcolate sull'importo secco anche per i BTP (`A26`/`A44`; prima sul tel quel), e
  bollo sull'importo secco (`K17`; prima sul tel quel).
- `btp_yields` del catalogo ora usa il calcolatore (100 di nominale, nessuna commissione, prima
  del bollo): catalogo e calcolatore danno lo stesso rendimento. `bond_yields.py` è passato da
  `utils/` a `services/`.
- Lista di gestione: badge "Prezzo emissione da verificare" sui BTP con prezzo di emissione uguale
  al rimborso (possibile segnaposto del sync).
- Guida [cosa-e-un-btp.md](../docs/guides/cosa-e-un-btp.md) creata; corretti i link delle guide
  rimasti ai vecchi indirizzi `/bonds/` e `/bonds/calculator`.

**Limiti noti:** i titoli zero coupon diversi dai BOT (CTZ, `F6=1`, maturazione composta) non
sono gestiti: non sono in catalogo. La pagina del calcolatore accetta già i BTP ma mostra solo i
campi del BOT (vedi Fase 11).

Correzione di calcolo emersa dal confronto con il foglio `Bond`: `BtpCalculatorService` e
`btp_yields` ignoravano lo scarto di emissione. Riguarda tutti i BTP con `issue_price` <
`redemption_price` (86 dei 108 in vita al 25/10/2026).

**Passi:**
1. Nasce `BondCalculatorService` (da `BtpCalculatorService`) con un `BondCalculationResultDTO`
   unico: per un BOT il piano cedole è vuoto e il rateo è 0.
2. Si aggiunge lo scarto di emissione (tabella sotto), con la maturazione del disaggio scelta per
   tipo di titolo.
3. **Parità con il BOT**: tutti i test di `test_bot_calculator_service.py` devono dare risultati
   **identici** sul nuovo servizio. Solo dopo si rimuove `BotCalculatorService`; fino ad allora
   il calcolatore BOT in produzione non cambia.

Comportamento da replicare (stessa logica dei BOT, con accrescimento lineare):

| Concetto | Formula | Riferimento foglio `Bond` |
|---|---|---|
| Scarto di emissione lordo | `redemption_price − issue_price` | `F15` |
| Prezzo teorico alla data *d* | `issue_price + scarto × yearfrac(data fiscale, d) / yearfrac(data fiscale, scadenza)`, ACT/ACT | `F29` (acquisto), `F45` (vendita) |
| Disaggio maturato alla data *d* | `prezzo teorico(d) − issue_price` | `F30`, `F46` |
| Corso super secco | `corso secco − disaggio maturato` | `F31`, `F47` |
| Imposta sul disaggio | 12,5% del disaggio maturato: a credito del compratore in acquisto, trattenuta al venditore in vendita | `K27`, `K39` |
| Rimborso netto a scadenza | `redemption_price − 12,5% × scarto` | `F16` |
| Prezzo di carico/scarico per il capital gain | al netto del disaggio maturato e delle commissioni | `K26`, `K38` |

- **Data fiscale di emissione**: per i titoli a cedola il disaggio matura da
  `max(issue_date, prima data cedola successiva all'1/1/1997)` (`AH7`); rilevante solo per i
  BTP più vecchi.
- **Effetto atteso**: il disaggio è tassato a parte e **non** è compensabile con lo zainetto,
  mentre il capital gain sullo scarto di prezzo sì. Un BTP comprato sopra il prezzo teorico paga
  comunque il 12,5% sul disaggio maturato nel periodo di possesso e genera una minusvalenza.
- Aggiornare anche `btp_yields` (catalogo), che oggi tassa l'intera differenza
  `redemption_price − last_price`.
- **Prerequisito sui dati**: il sync (Fase 7) usa la pari come segnaposto se Teleborsa non
  fornisce il prezzo di emissione. Va almeno segnalato (log + evidenza in pagina CRUD), perché
  un prezzo di emissione sbagliato azzera lo scarto senza che nessuno se ne accorga.
- **Guide**: in `cosa-e-un-btp.md` spiegare perché un BTP comprato a scadenza rende meno del
  previsto se è stato emesso sotto la pari (la tassa sullo scarto), con un esempio; in
  `calcolatore-btp.md` spiegare le nuove righe (prezzo teorico, disaggio, corso super secco).

## Fase 9 — Rateo: convenzione e imposte (🔴) ✅

**Fatto:**
- `CouponSchedule.accrued_interest` usa la convenzione del foglio (ICMA, `F36`/`F52`): cedola del
  periodo × giorni da `max(stacco precedente, emissione)` / giorni del periodo regolare, troncato
  alla sesta cifra decimale (con `Decimal`, così 0,625 resta 0,625). Alla scadenza il rateo è 0.
- Nuovo campo `accrued_interest_tax` su acquisto e vendita, con segno come `discount_tax`:
  credito del 12,5% sul rateo pagato (`K28`), trattenuta del 12,5% sul rateo incassato (`K40`).
- Zainetto: l'imposta sulla plusvalenza è `max(0, plus × 48,08% − minusvalenze) / 48,08% × 12,5%`
  e lo zainetto residuo è `max(0, minusvalenze − plus × 48,08%)` (`K49`–`K53`). Il fattore è ora
  esatto (`12,5% / 26%`, cella `C10`) invece di 0,4808.
- A scadenza non si applicano commissioni di vendita (`K36`). Verificato prima del cambiamento:
  la pagina del calcolatore svuota le commissioni di vendita quando la vendita non è spuntata,
  quindi nessun risultato BOT visibile in pagina cambia per questo.
- Effetto sui BOT misurato su 5.000 casi casuali contro il commit precedente: senza zainetto e
  senza commissioni a scadenza (il caso della pagina) cambiano solo "Riduzione imponibile TdS" e
  lo zainetto residuo, di al più 0,44 €, per il fattore esatto; imposte, totali e rendimenti no.
- Test: 4 nuovi casi del foglio `Bond` (`btp_calculator_case_006`–`009`: acquisto e vendita a
  metà periodo, zainetto parziale e totale) e i 5 della Fase 8 estesi con rateo, imposte sul rateo
  e zainetto residuo; 2 test BOT per zainetto e commissioni a scadenza.
- Guide: la sezione "Il rateo e le tasse" in [cosa-e-un-btp.md](../docs/guides/cosa-e-un-btp.md)
  (al posto di `calcolatore-btp.md`, che nascerà con la Fase 11); formula dello zainetto corretta
  in [calcolatore.md](../docs/guides/calcolatore.md) e
  [calcolatore-approfondimenti.md](../docs/guides/calcolatore-approfondimenti.md).

**Scelta da confermare:** in caso di **minusvalenza** `remaining_loss` resta "minus da aggiungere
allo zainetto" (`|minus| × 48,08%`), come mostra oggi la pagina, mentre il foglio (`K53`) riporta lo
zainetto totale (minusvalenze pregresse + nuova minus). I due coincidono quando non ci sono
minusvalenze pregresse.


Tre differenze sul rateo cedolare, emerse confrontando il servizio con il foglio `Bond` (le prime
due durante la Fase 8):

- **Convenzione di calcolo** (`F36`, `F52`): il foglio calcola il rateo come
  `cedola del periodo × giorni trascorsi / giorni del periodo` (ICMA), arrotondato per difetto alla
  sesta cifra decimale; `CouponSchedule.accrued_interest` usa `tasso × YEARFRAC ACT/ACT`. Su un
  BTP semestrale la differenza è dell'ordine dello 0,8% del rateo.
- **Credito sul rateo pagato all'acquisto** (`K28`): il foglio riconosce al compratore un credito
  del 12,5% sul rateo pagato al venditore (sulla cedola successiva il compratore è tassato per
  intero). Oggi il servizio non lo considera e sovrastima il costo d'acquisto.
- **Imposta sul rateo in vendita** (`K40`): il foglio trattiene il 12,5% sul rateo incassato dal
  venditore, che è reddito da cedola. `_calc_sale` oggi lo somma lordo a `total_received`,
  sovrastimando il netto delle vendite anticipate.

- Aggiungere al risultato di acquisto e di vendita le imposte sul rateo, con segno come per
  `discount_tax`.
- Il rendimento lordo resta invariato; cambiano netto, netto al lordo del bollo e XIRR netto.
- **Test**: casi del foglio `Bond` con acquisto e vendita **a metà periodo** (le fixture della
  Fase 8 usano date di stacco proprio per tenere fuori il rateo).

Altre due differenze fiscali emerse in Fase 8, valide anche per i BOT:

- **Zainetto nell'imposta sulla plusvalenza** (`K49`–`K52`): il foglio sottrae le minusvalenze
  pregresse dalla base imponibile prima di applicare l'imposta; il servizio calcola l'imposta sulla
  plusvalenza intera e usa lo zainetto solo per lo zainetto residuo.
- **Commissioni a scadenza** (`K36`): il foglio non applica commissioni di vendita al rimborso a
  scadenza; il servizio le applica se il form le passa (minimo compreso). Il cambiamento tocca i
  BOT già in produzione: va verificato contro i casi BOT prima di cambiarlo.
- **Guide**: in `calcolatore-btp.md` spiegare che vendendo prima della scadenza si incassa il
  rateo dal compratore e che anche su quello si paga il 12,5%.

## Fase 10 — Prima cedola irregolare (🟡)

Se la data di emissione non coincide con una data di stacco, la prima cedola copre un periodo
più corto (o più lungo) di quello standard. Il foglio `Bond` la riduce in proporzione
(`W4`: cedola × giorni dall'emissione al primo stacco / giorni del periodo), mentre
`CouponSchedule` la paga sempre intera.

- Importare/sincronizzare la colonna `E — DATA PRIMA CEDOLA` di `Emissioni` (oggi non mappata,
  vedi Fase 6): nuovo campo opzionale `first_coupon_date` in `BondDAO`/`BondDTO`, con migrazione.
- Usarla in `CouponSchedule` per la prima cedola e per il rateo prima del primo stacco.
- Impatta solo chi detiene il titolo al primo stacco (acquisti in asta o subito dopo
  l'emissione).
- **Guide**: in `cosa-e-un-btp.md` un paragrafo breve: perché la prima cedola di un BTP appena
  emesso può essere più piccola delle altre.

## Fase 11 — Calcolatore BTP in pagina (🟡)

Viene dopo le fasi 8–10 così l'utente vede da subito risultati corretti.

- Dalla Fase 8 la pagina usa il calcolatore unico, quindi un BTP selezionato viene già calcolato
  correttamente, ma la pagina mostra solo i campi del BOT: mancano rateo, prezzo tel quel e piano
  cedole, e "Imposta sul disaggio" per un BTP ha segno opposto (credito all'acquisto, trattenuta
  alla vendita) e va etichettata di conseguenza.
- Con il calcolatore unico (Fase 8) non serve una pagina nuova: si estende la pagina esistente
  ([calculator_controller.py](../src/intelligent_investor/controllers/calculator_controller.py),
  [calculator/index.html](../src/intelligent_investor/templates/calculator/index.html)) per
  accettare anche i BTP, mostrando rateo e piano cedole (Fase 3) solo quando il titolo ha cedole.
- Riuso del profilo bancario esistente (`bank_profile` / `bank_commission`) per le commissioni,
  nessuna modifica allo schema: le commissioni MOT sono le stesse indipendentemente dallo
  strumento.
- **Guide**: nuova `calcolatore-btp.md` con un esempio completo su un BTP reale (acquisto,
  piano cedole, rateo, capital gain, bollo, rendimenti) e cosa significa ogni riga del risultato,
  incluse le righe rimaste dalle fasi 8 e 9: prezzo teorico, disaggio e corso super secco; credito
  sul rateo pagato all'acquisto e imposta sul rateo incassato vendendo prima della scadenza.

## Fase 12 — Duration modificata (🟡)

Il foglio `Bond` la calcola con `MDURATION` (`K16`, solo per durate residue ≥ 1 anno) e la
mostra anche in `ConfrontoRendimenti`.

- Funzione pura in `utils/` (Macaulay → modificata, sui flussi cedolari residui), testata contro
  `MDURATION` per 2–3 titoli.
- Esposta in `SummaryResultDTO`, nel dettaglio bond e come colonna del catalogo.
- **Guide**: spiegare la duration senza formule, come misura del rischio: "se i tassi salgono
  dell'1%, il prezzo scende circa del X%". In `cosa-e-un-btp.md` e nella colonna del catalogo
  (`catalogo.md`).

## Fase 13 — Confronto rendimenti (🟡)

Equivalente del foglio `ConfrontoRendimenti`: tutti i titoli a confronto sullo **stesso importo**
e con **commissioni, spese fisse e minusvalenze reali**, mentre il catalogo calcola i rendimenti
senza commissioni né bollo.

- Colonne: nominale, importo pagato, rendimento lordo, netto al lordo del capital gain, netto al
  lordo del bollo, netto, durata, scadenza, guadagno netto, prezzo, duration modificata,
  minusvalenza.
- Usa il calcolatore unico (Fase 8) per ogni titolo, con un profilo banca scelto dall'utente.
- Sostituisce la vecchia voce 4.5 di [`ROADMAP.md`](../ROADMAP.md) (spostata dalla Milestone 4,
  step-up, perché è utile già con soli BOT e BTP a tasso fisso).
- **Guide**: nuova `confronto-rendimenti.md` — come scegliere tra più titoli: perché il
  rendimento del catalogo e quello del confronto differiscono (commissioni, bollo), come pesano
  le spese fisse su importi piccoli.

## Fase 14 — Rifiniture (🟢)

- **Spesa fissa per cedola** (`K44`): commissione che alcune banche addebitano a ogni stacco.
  Nuovo campo nel profilo banca e in `BondTransactionDTO`, dedotto da ogni cedola netta.
- **Rendimenti aggiuntivi del foglio**: netto al lordo del capital gain e del bollo (`K8`) e ROI
  totale lordo/netto (`K11`–`K14`).
- **Bollo nei flussi dell'XIRR netto** (colonna `R`): il foglio sottrae il bollo anno per anno dal
  flusso di ciascun anno; il servizio lo sottrae tutto dall'ultimo flusso. Cambia solo il
  rendimento netto composto (non quello al lordo del bollo).
- **Book di negoziazione** (foglio `QuotazioneIsin`): proporre come prezzo di acquisto il miglior
  prezzo in lettera invece dell'ultimo prezzo.
- **Guide**: aggiornare `calcolatore-btp.md` e la guida delle banche per la spesa per cedola.
