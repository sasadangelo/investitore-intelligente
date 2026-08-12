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

## Fase 3 — DTO: `BtpTransactionDTO` e `BtpCalculationResultDTO` (🔴) ✅

Implementata in [btp_transaction.py](../src/intelligent_investor/dtos/btp_transaction.py) e
[btp_calculation_result.py](../src/intelligent_investor/dtos/btp_calculation_result.py).

Nuovi file in `dtos/`, sul modello di
[bot_transaction.py](../src/intelligent_investor/dtos/bot_transaction.py) e
[bot_calculation_result.py](../src/intelligent_investor/dtos/bot_calculation_result.py).

`BtpTransactionDTO` — stessi campi di `BotTransactionDTO` (venue, date/prezzo acquisto e vendita,
commissioni, bollo, minusvalenze pregresse); non serve duplicare quella parte.

`BtpCalculationResultDTO` — sezioni aggiuntive rispetto al BOT:

| Sezione | Contenuto | Riferimento foglio `Bond` |
|---|---|---|
| **Acquisto** | prezzo tel quel (clean) + rateo cedolare a carico compratore = prezzo **corso secco** pagato al venditore; nessuna imposta sul rateo stesso (è un semplice trasferimento tra privati) | colonne `Q`/`R` (rateo cedolare acquisto) |
| **Piano cedole** | tabella data/cedola lorda/cedola netta per ogni stacco tra acquisto e vendita/scadenza | righe 3–112 colonne `U`/`V`/`W`/`X` |
| **Capital gain** | plus/minusvalenza sul **solo scarto di prezzo** (prezzo di carico/scarico *al netto* del rateo, che è già tassato come reddito da cedola) — stessa logica di riduzione 48,08% e "zainetto" già implementata per i BOT in `_calc_capital_gain` | colonne `AF`–`AI` |
| **Bollo** | invariato, riuso 1:1 di `_calc_stamp_duty` | — |
| **Riepilogo** | rendimento semplice/composto lordo e netto, ora calcolato sui flussi multipli (Fase 2) invece che a 2 punti | `J4`/`K4` (TIR), `J5`/`K5` (guadagno netto totale) |

## Fase 4 — `BtpCalculatorService` (🔴) ✅

Implementata in
[btp_calculator_service.py](../src/intelligent_investor/services/btp_calculator_service.py), con
test in [test_btp_calculator_service.py](../test/unit/test_btp_calculator_service.py).

Le parti realmente comuni con il BOT (commissioni, bollo) sono state estratte in
[bond_calculator_common.py](../src/intelligent_investor/services/bond_calculator_common.py)
(`calc_commission`, `calc_stamp_duty`), usato solo dal nuovo servizio: `bot_calculator_service.py`
non è stato toccato, come richiesto in testa a questo documento, e mantiene la propria copia
privata di `_calc_commission`.

Struttura a metodi privati speculare a `BotCalculatorService`:

1. `_calc_purchase` — prezzo corso secco (clean + rateo), commissioni via `calc_commission` del
   modulo condiviso.
2. `_calc_coupon_schedule` — usa Fase 1 per generare le cedole nette incassate durante il possesso
   (stacchi in `(purchase_date, sale_date]`).
3. `_calc_sale` — prezzo di vendita/rimborso corso secco (clean + rateo a favore del venditore).
4. `_calc_capital_gain` — riuso concettuale della logica BOT (riduzione TdS, zainetto), applicata
   allo scarto di prezzo *clean* invece che al disaggio. A differenza del BOT non serve il prezzo
   teorico: il prezzo clean di un BTP non è vincolato a una retta di accrescimento
   emissione→scadenza, quindi `load_price`/`unload_price` sono lo scarto di prezzo diretto (al
   netto delle commissioni per unità), senza alcuna correzione. Di conseguenza, a differenza del
   BOT, per il BTP il capital gain è sempre calcolato (mai `None`, anche per acquisti in asta).
5. `_calc_stamp_duty` — riuso diretto di `calc_stamp_duty` del modulo condiviso (stessa base di
   calcolo, stessa aliquota 0,20%/anno).
6. `_calc_summary` — rendimento semplice/composto con XIRR multi-flusso (Fase 2).

## Fase 5 — Catalogo BTP (🟡) ✅

Estesa la pagina/servizio di catalogo esistente
([bond_controller.py](../src/intelligent_investor/controllers/bond_controller.py)) per includere
i BTP, con test in
[test_bond_controller.py](../test/unit/test_bond_controller.py):

- Filtro per `bond_type` (dropdown "Tutte"/"BOT"/"BTP Tasso Fisso" in
  [bonds/index.html](../src/intelligent_investor/templates/bonds/index.html), query param
  `?bond_type=`; opzioni limitate ai tipi realmente in uso per ora, vedi `CATALOG_FILTERS`).
- Rendimento corrente stimato (`_calc_btp_yields`): scadenzario cedole (Fase 1) sui flussi
  residui da oggi a scadenza, ancorati all'ultima quotazione MOT (`BondQuoteDAO`) come esborso
  odierno (prezzo corso secco = clean + rateo), risolto con XIRR multi-flusso (Fase 2). Il netto
  applica anche un'imposta indicativa di capital gain sullo scarto di prezzo clean, coerente con
  la semplificazione già usata per il rendimento BOT del catalogo (nessuna commissione/bollo,
  ignoti a livello di catalogo).
- `_calc_bond_yields` fa da dispatcher tra la formula BTP e quella BOT esistente (`_calc_yields`),
  usato sia dalla pagina lista (`index`) sia dal dettaglio (`detail`).
- Paginazione (`?page=&per_page=`, opzioni 10/20/50/100, default 20 — `_paginate`) e ordinamento
  (`?sort=maturity|yield_gross|yield_net&dir=asc|desc`, header di colonna cliccabili — `_sort_bonds`,
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

Colonne **non** mappate in questa fase: `N` (Premio Fedeltà, solo BTP Valore/Futura), `R`–`AK`
(scadenzario STEP), `J`/`K` (quotazione MOT — va nel catalogo quotazioni esistente, non
nell'anagrafica).

**Import reale eseguito**: 108 BTP a tasso fisso importati in `data/investor.db` da
`ObbligazioniTF v5.0.ods` (non presente in questo repository). Durante l'import è emerso un ISIN
duplicato nel file sorgente (due titoli diversi condividevano lo stesso ISIN, corretto a mano
prima dell'import reale) — evidenzia perché il passo sotto resta necessario prima di considerare
i dati affidabili in produzione.

**Resta da fare**: validazione manuale di un campione contro il sito MEF prima di considerare i
dati affidabili per l'uso in produzione.

## Fase 7 — Sync quotazioni MOT per BTP (🟡, pianificata)

Dopo l'import dell'anagrafica (Fase 6), i 108 BTP importati non hanno alcuna quotazione
(`BondQuoteDAO`): il catalogo (Fase 5) mostra correttamente "—" al posto di rendimento
lordo/netto perché `_calc_bond_yields` richiede un `last_price` che oggi non esiste per nessun
BTP. Per i BOT esiste già un sync (`teleborsa_bot_client.py` + `BondSyncService`, bottone
"Aggiorna Quotazioni" nel catalogo); per i BTP manca l'equivalente.

Lavoro previsto:
1. Un nuovo client (es. `teleborsa_btp_client.py` o sorgente equivalente) che recuperi l'ultimo
   prezzo MOT per ISIN, sullo stile di `teleborsa_bot_client.py` (stesso parsing prezzo/data,
   `ClientRegistry`).
2. Registrazione del nuovo client in `ClientRegistry` con una sorgente dedicata (es.
   `"teleborsa_btp"`), riusando `BondSyncService.sync()` così com'è (già generico per
   `(BondDTO, BondQuoteDTO)`, non serve toccarlo).
3. UI: un secondo bottone "Aggiorna Quotazioni BTP" in
   [bonds/index.html](../src/intelligent_investor/templates/bonds/index.html) accanto a quello
   BOT esistente, o un'estensione del bottone attuale per sincronizzare entrambi i tipi in un'unica
   passata (da valutare in base a quanto è comune la fonte dati).
4. Test sul modello di [test_bond_sync_service.py](../test/unit/test_bond_sync_service.py).

## Fase 8 — Controller e UI (🟡)

- Nuova rotta calcolatore BTP (route dedicata o parametro `bond_type` sulla rotta esistente in
  [bond_controller.py](../src/intelligent_investor/controllers/bond_controller.py), da valutare
  in base a quanto diverge il template).
- Template: stessa struttura della pagina calcolatore BOT, con l'aggiunta della tabella "Piano
  cedole" (Fase 3) sotto i risultati di acquisto.
- Riuso del profilo bancario esistente (`bank_profile` / `bank_commission`) per le commissioni,
  nessuna modifica allo schema: le commissioni MOT sono le stesse indipendentemente dallo
  strumento.

## Fase 9 — Documentazione utente (🟡)

In `docs/guides/` (seguendo lo stile di
[cosa-e-un-bot.md](../docs/guides/cosa-e-un-bot.md) e
[calcolatore.md](../docs/guides/calcolatore.md)):
- `cosa-e-un-btp.md` — spiegazione BTP, cedola, corso secco/tel quel, rateo.
- `calcolatore-btp.md` — guida al calcolatore BTP, con esempio completo come quello già presente
  per il BOT.
- Aggiornare `catalogo.md` per menzionare i BTP in catalogo.

## Fase 10 — Test (🔴, trasversale a tutte le fasi precedenti)

Sul modello di `test/unit/test_bot_calculator_service.py` e delle fixture in
`test/unit/fixtures/`:
- Fixture parametriche per `BtpCalculatorService` con casi noti (titolo tenuto a scadenza,
  vendita anticipata prima/dopo uno stacco cedola, titolo acquistato sopra/sotto la pari).
- Test dedicati per lo scadenzario cedole (Fase 1) e per l'XIRR multi-flusso (Fase 2), inclusi
  casi limite (acquisto lo stesso giorno di uno stacco, scadenza con un'unica cedola residua).
- Valori attesi calcolati a mano o cross-verificati contro il foglio `Bond` del file di
  riferimento per almeno 2–3 titoli reali.

---

### Nota di design — il BOT come caso speciale di BTP (🟢, valutazione successiva)

Un BOT è, matematicamente, un BTP con `coupon_frequency = 0`: nessuna cedola, nessun rateo, un
solo flusso all'acquisto e uno a scadenza/vendita. `BondDAO`/`BondDTO` sono già unificati e non
richiedono modifiche per rappresentare questo caso. In linea di principio, quindi,
`BtpCalculatorService` potrebbe assorbire anche la logica oggi in `BotCalculatorService`,
eliminando la duplicazione tra i due servizi.

Non conviene però anticipare questa unificazione: `BotCalculatorService` è già testato e in
produzione, e usa una specializzazione precisa del caso zero-coupon (formula chiusa a 2 flussi,
"imposta scarto" invece di cedola + capital gain separati) che sarebbe rischioso alterare prima
che il calcolatore BTP generalizzato esista e sia collaudato. Sequenza consigliata, da eseguire
solo a valle della Fase 10:

1. Costruire `BtpCalculatorService` gestendo `coupon_frequency = 0` come caso limite dello
   scadenzario cedole (Fase 1) e dell'XIRR multi-flusso (Fase 2).
2. Far girare la fixture di test del BOT esistenti (`test_bot_calculator_service.py`) anche
   contro `BtpCalculatorService` con `coupon_frequency = 0`, e verificare parità **esatta** dei
   risultati con `BotCalculatorService`.
3. Solo dopo aver dimostrato questa parità, valutare se trasformare `BotCalculatorService` in un
   thin wrapper su `BtpCalculatorService` (o ritirarlo del tutto), senza mai toccare il
   calcolatore BOT in produzione prima che l'equivalenza sia provata.


## Ordine di esecuzione consigliato

Le fasi 1–4 sono sequenziali e bloccanti (la logica di calcolo è un prerequisito per tutto il
resto). Le fasi 5–9 possono procedere in parallelo una volta completata la Fase 4. Le fasi 5
(catalogo) e 6 (import anagrafica) sono già complete. La Fase 7 (sync quotazioni MOT) dipende dai
dati importati in Fase 6 ed è il passo che sblocca il rendimento nel catalogo per i BTP reali. Le
fasi 8 (Controller e UI calcolatore) e 9 (Documentazione) possono procedere in autonomia rispetto
alla 7, dato che non dipendono dalle quotazioni.
