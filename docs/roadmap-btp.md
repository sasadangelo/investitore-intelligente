# Roadmap tecnica — Supporto BTP a tasso fisso

> Ambito: solo BTP a **tasso fisso** (cedola costante, `Tipo Obbl. = "Cedola Fissa"` nel foglio
> `Emissioni`). BTP Valore, BTP Italia, BTP Più e ogni titolo a cedola *STEP* sono **esclusi**
> da questa fase e restano nella Milestone 4 di [`ROADMAP.md`](ROADMAP.md).

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

Colonne **non** mappate in questa fase: `E` (Data prima cedola — vuota per tutti i BTP, vedi
Fase 10), `N` (Premio Fedeltà, solo BTP Valore/Futura), `R`–`AK`
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
- ✅ [catalogo.md](../docs/guides/catalogo.md) — ora "Catalogo Obbligazioni": BOT e BTP, filtro per
  tipo, ordinamento, colonne spiegate per entrambi, parametri avanzati, "Aggiorna Quotazioni" e
  "Gestisci". Rinominata anche `calcolatore.md` in "Calcolatore Obbligazioni" (campi comuni ed
  esempio BOT; i BTP restano in `calcolatore-btp.md`) e "Approfondimenti sul Calcolatore"; stessi
  nomi nei titoli delle pagine del sito.
- ✅ **Una sola guida del calcolatore**: `calcolatore-btp.md` (Fase 11) è stata unita in
  [calcolatore.md](../docs/guides/calcolatore.md), perché il calcolatore è uno solo: campi del form
  una volta sola, risultati comuni, sezione "Righe in più per un BTP", esempio BOT ed esempio BTP
  (a scadenza e con vendita anticipata), indice delle sezioni in cima (`[TOC]`, solo titoli `##`).
  Corrette alcune frasi rimaste dalla versione solo BOT (capital gain anche a scadenza, prezzo
  teorico, base del bollo, guadagno lordo, acquisto in asta). Le citazioni di `calcolatore-btp.md`
  nelle fasi precedenti sono storiche.
- ✅ **Pagine di esempi**: gli esempi completi sono passati da `calcolatore.md` a due pagine in fondo
  all'indice, [esempi-bot.md](../docs/guides/esempi-bot.md) (BOT Feb24 sul MOT a scadenza, con il
  rimborso corretto: a scadenza nessuna "imposta disaggio rimborsata", come la ricevuta della
  banca) ed [esempi-btp.md](../docs/guides/esempi-btp.md) (BTP Lug29 a scadenza e con vendita
  anticipata); `calcolatore.md` vi rimanda. Altri esempi da aggiungere.
- ✅ **Form e modello della transazione**: il form del calcolatore è diviso in Acquisto, Vendita
  anticipata (facoltativa) e Banca e tasse (le commissioni di vendita compaiono solo con la
  vendita). Nel codice `BondTransactionDTO` non è più piatto: contiene `buy: BuyTransactionDTO`,
  `sell: SellTransactionDTO | None` (None = tenuto a scadenza) e `account: AccountDTO` (bollo,
  spesa per cedola, zainetto). `BuyTransactionDTO` e `SellTransactionDTO` sono sottoclassi di
  `TransactionDTO` (data, prezzo, commissioni) e definiscono ciascuna la base della commissione
  (`commission_base`: nominale in asta, importo secco sul MOT e in vendita). `from_flat` costruisce
  la transazione dai nomi piatti del form e dei casi di test JSON, rimasti invariati. Nessun
  risultato cambiato: tutti i test passano con gli stessi valori attesi.
- ✅ **Profili banca verificati sui fogli informativi** (31/10/2026): spesa per cedola sui titoli di
  Stato 0 € in tutte le 10 banche (segnata nelle note); link aggiornati per BPER, Directa e MPS;
  Directa sul MOT 6 € per eseguito con ogni profilo (non 5 €; l'1,9‰ "Variabile" vale solo per MTA
  e SEDEX; il profilo "Dinamico" non è modellabile, degressivo per ordini nella giornata).
- ✅ **Commissioni per tipo di titolo**: nuova colonna `bond_type` sulle righe di commissione
  (`all` | `BOT` | `BTP`, default `all`); `resolve_commission` e il JavaScript del calcolatore
  provano prima le righe del tipo del titolo, poi quelle `all`. Dati corretti: le fasce d'asta
  per durata sono quelle di legge dei BOT (righe `BOT`), quindi un BTP in asta non paga
  commissione, come dicono Fineco ("Sottoscrizione BTP 0,00"), Webank ("Gratuito") e Poste
  ("Nessuna"); Unicredit e MPS Filiale/Phone hanno una tariffa MOT propria per i BTP (Unicredit
  0,90/0,60/0,40%, MPS 0,85/0,60%); le righe MPS trimestrale/semestrale/annuale non avevano i
  giorni e il calcolatore usava sempre la prima; Intesa Filiale aveva le tariffe MOT sulle righe
  d'asta; Poste aveva il minimo di 5,16 € in asta e fasce MOT dei BOT sbagliate. Corretto anche
  l'arrotondamento a 2 decimali della percentuale nel form (0,215% → 0,22%). **BPER**: l'avviso
  titoli di Stato del 26/10/2026 conferma l'asta (solo BOT, BTP "non applicabili") e indica 0,50%
  "per transazioni successive al collocamento" senza distinguere il canale; le tariffe MOT del
  profilo restano quelle del contratto 12/2024 (per canale), con una nota che segnala la
  differenza, finché un eseguito reale non chiarisce quale si applica.
- **Prossimo — spese di custodia dei titoli di Stato**: BPER, Unicredit e Poste 10 € a semestre,
  Intesa 10 € più un canone mensile in alcuni conti. Vanno nel profilo come costo del conto e
  nel calcolatore come campo **modificabile**, proposto dal profilo ma azzerabile: non tutti la
  pagano (es. Intesa con alcuni conti XME), come per la spesa per cedola.
- ✅ **Capital gain dei BOT comprati in asta**: il calcolatore lo saltava (`_calc_capital_gain`
  restituiva `None` per ogni BOT in asta), ma nel foglio `K26`/`K38`/`K46`–`K53` non guardano il
  mercato: in asta il prezzo teorico è quello di emissione, ma le commissioni entrano nel prezzo
  di carico. Ora si calcola per ogni acquisto (`BondCalculationResultDTO.capital_gain` non è più
  opzionale). Casi 003 e 004 aggiornati con i valori del foglio rifatti cella per cella (a
  scadenza minusvalenza −7,50 € = commissioni; vendita a 99,70 sotto il teorico 99,877:
  −31,81 €); verificati anche i casi MOT 001, 002, 005 (scarto massimo 7e-13). Guide aggiornate
  (`calcolatore.md`, `calcolatore-approfondimenti.md`). Si può ora aggiungere l'esempio "BOT in
  asta venduto prima".
- ✅ **Indice delle guide**: `Cos'è un BOT` e `Cos'è un BTP` non sono più nell'indice (campo
  `listed: false` nell'intestazione, gestito da `GuideService.list_all`), ma si aprono dai due
  riquadri in evidenza in `cosa-e-un-obbligazione.md` e dai link delle altre guide.
- ✅ [cosa-e-un-obbligazione.md](../docs/guides/cosa-e-un-obbligazione.md) — guida di partenza: cos'è
  un'obbligazione, parole chiave, rischi, tasse, dove si compra, e la mappa delle famiglie (BOT, BTP a
  tasso fisso, BTP a cedole crescenti e indicizzati, CCTeu, titoli esteri, corporate). Le guide BOT e
  BTP partono da lì. **Regola**: quando il sito gestirà una nuova famiglia (Milestone 4 step-up,
  Milestone 5 corporate, ...), la sua guida si collega dalla tabella "Le famiglie di obbligazioni",
  dove "non ancora" diventa ✅.
- ✅ [cosa-e-un-btp.md](../docs/guides/cosa-e-un-btp.md) — creata in Fase 8: cedola, corso secco e
  tel quel, rateo, tasse, prima cedola irregolare (Fase 10), scarto di emissione con esempio
  numerico.
- ✅ [inizia-qui.md](../docs/guides/inizia-qui.md) — riscritta per le obbligazioni (BOT e BTP): "Catalogo
  Obbligazioni" e "Calcolatore Obbligazioni", scelta per orizzonte e poi rendimento netto, parametri
  avanzati, calcolatore su MOT, asta BOT (Previsioni + BOT manuale) e riaperture BTP; corretti il
  capital gain (12,5%, non 26%) e i "prezzi in tempo reale".

**Aiuto sui campi** ✅: ogni campo del calcolatore (form e risultato) e ogni intestazione del
catalogo, pannello "Parametri avanzati" compreso, ha un'icona ⓘ che al clic apre un popover con
una spiegazione breve. I testi stanno in un solo posto,
[_help.html](../src/intelligent_investor/templates/_help.html) (dizionario `HELP` e macro
`info('chiave')`); la spiegazione completa resta nelle guide. **Regola**: un campo o una colonna
nuova si aggiunge insieme al suo testo; `test_field_help.py` fallisce se una chiave usata non ha
testo o se un testo non è più usato.

**Guide di ogni fase** (dettagli nella voce "Guide" della fase):

| Fase | Guida |
|---|---|
| 8 — Scarto di emissione | ✅ `cosa-e-un-btp.md` (la parte per `calcolatore-btp.md` passa alla Fase 11) |
| 9 — Rateo: convenzione e imposte | ✅ `cosa-e-un-btp.md`, `calcolatore.md`, `calcolatore-approfondimenti.md` (la parte per `calcolatore-btp.md` passa alla Fase 11) |
| 10 — Prima cedola irregolare | ✅ `cosa-e-un-btp.md` |
| 11 — Calcolatore BTP in pagina | ✅ `calcolatore-btp.md` (nuova), con esempio completo |
| 12 — Duration modificata | ✅ `cosa-e-un-btp.md`, `catalogo.md` (anche una riga in `calcolatore-btp.md`) |
| 13 — Costi reali nel catalogo | ✅ `catalogo.md` (sezione "Parametri avanzati") |
| 14 — Rifiniture | ✅ `calcolatore-btp.md`, `calcolatore.md`, `catalogo.md` (spesa per cedola) |
| 15 — Calendario aste BTP | ✅ `calendario.md`, `inizia-qui.md` |

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

## Decisione di design — convenzioni di calcolo dei giorni ✅

Ogni calcolo che dipende dal tempo trascorso prende la sua convenzione da un unico posto,
[day_count.py](../src/intelligent_investor/utils/day_count.py), anche quando per BOT e BTP non
cambia mai: così le regole sono scritte una volta sola e con il loro perché.

- `DayCountConvention`: le convenzioni del file di riferimento (`act/act`, `act/360` =
  "Effettiva/360", `act/365` = "Effettiva/365", `30/360`), ciascuna con frazione d'anno (YEARFRAC),
  quota di periodo trascorsa e calcolo del rateo. Per il rateo `act/act` è la regola ICMA (giorni
  trascorsi / giorni del periodo cedolare), come nel foglio `Bond` (`F36`).
- `BOND_CONVENTIONS`: la convenzione di ogni calcolo per tipo di titolo.

| Calcolo | BOT | BTP | Perché |
|---|---|---|---|
| Rateo cedolare | act/act (non usato: niente cedole) | act/act | foglio `Emissioni`, colonna Q, per tutti i BTP |
| Maturazione dello scarto | act/365 | act/act | BOT: quota di giorni effettivi (`F29` con `F6=3`), che con act/365 è esattamente il rapporto tra giorni; BTP: colonna P |
| Durata del rendimento semplice | act/act | act/act | cella `K15`, YEARFRAC base 1 |
| Rendimento composto (XIRR) | act/365 | act/365 | XIRR conta sempre giorni / 365 |
| Duration modificata | 30/360 (non usata: niente cedole) | 30/360 | cella `K16`: `MDURATION` senza base, cioè base 0 (Fase 12) |

Verifica: tutti i casi del foglio `Bond` coincidono come prima; su 5.000 casi casuali i BTP danno
risultati identici bit per bit a prima, i BOT differiscono di al più 2,6e-11 € negli importi
intermedi (la quota di vita trascorsa ora passa dalla convenzione).

- **Solo BOT e BTP a tasso fisso**: `BondDTO.bond_type` accetta solo `"BOT"` e `"BTP"`, e il form
  di gestione propone solo questi due tipi.
- **Rimandato — convenzioni per singolo titolo**: nel foglio `Emissioni` la convenzione è scelta
  titolo per titolo, ma per tutti i BOT e i BTP è act/act (l'unica eccezione è un corporate a
  30/360). Salvarla per titolo richiederebbe due colonne nel database, una migrazione e due campi
  nel form per avere sempre lo stesso valore: si farà solo se entreranno titoli con convenzioni
  diverse.
- **Da verificare — base 360 per i BOT**: il rendimento BOT del catalogo e la previsione delle aste
  ([bot_forecast_service.py](../src/intelligent_investor/services/bot_forecast_service.py), che usa
  ancora giorni / 365 scritti nel codice) andrebbero confrontati con la convenzione con cui il MEF
  pubblica i rendimenti dei BOT, che potrebbe essere su base 360.

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

## Fase 10 — Prima cedola irregolare (🟡) ✅

**Fatto:**
- La colonna `E — DATA PRIMA CEDOLA` di `Emissioni` è **vuota per tutti i BTP** del foglio (è
  compilata solo per alcuni titoli esteri: Bobl, Bund, EU, Romania, Messico). Il foglio in quel
  caso usa `COUPNCD(emissione)` (cella `AH32`), quindi la prima cedola corta è ridotta comunque:
  la correzione vera era in `CouponSchedule`, non nei dati. Nessun dato da importare per i 108 BTP.
- Nuovo campo opzionale `first_coupon_date` in `BondDAO`/`BondDTO` (validato tra emissione e
  scadenza), modificabile dal form e mostrato nel dettaglio. Vuoto = prima data regolare dopo
  l'emissione; va compilato solo per una prima cedola **lunga** (il Tesoro salta il primo stacco).
  Il sync Teleborsa non lo valorizza (la scheda non lo espone).
- Migrazione: `DatabaseInitializer._migrate` aggiunge le colonne nullable elencate in
  `_ADDED_COLUMNS` che mancano alle tabelle esistenti (`create_all` non altera le tabelle).
  Idempotente; verificata su una copia di `data/investor.db`.
- `CouponSchedule.first_coupon_amount` (cella `W4`): cedola del periodo che va da
  `COUPPCD(emissione)` (`F34`) alla prima cedola, × giorni dall'emissione alla prima cedola /
  giorni del periodo. Per una prima cedola lunga la cedola del periodo è
  `tasso × YEARFRAC(F34; prima cedola)` nella convenzione del rateo (`AJ32`). `schedule` usa
  questo importo per la prima cedola; le altre restano regolari.
- Rateo prima del primo stacco (`F36`): stesso periodo e stessa cedola della prima cedola. Per la
  prima cedola corta il risultato non cambia rispetto a prima; cambia solo per quella lunga.
  `DayCountConvention.accrued_coupon` accetta la cedola del periodo (`period_coupon`) quando non è
  quella regolare.
- `_generate_dates` ora fa i passi indietro dalla scadenza (come `next_coupon_date`) invece che
  dalla data precedente, così il troncamento del giorno nei mesi corti non si propaga.
- Test: prima cedola corta, regolare, lunga, rateo prima della prima cedola lunga, validazione;
  due casi del calcolatore (asta con prima cedola corta, acquisto prima di una prima cedola lunga).
- Guide: paragrafo "Perché la prima cedola può essere più piccola" in
  [cosa-e-un-btp.md](../docs/guides/cosa-e-un-btp.md).

**Resta da fare:** una fixture `btp_calculator_case_*` cross-verificata sul foglio `Bond` per un
acquisto in asta con prima cedola irregolare (vedi "Per ogni fase — Test"): i valori attesi dei
test nuovi sono calcolati a mano dalle formule `W4`/`F36`/`AJ32`.


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

## Fase 11 — Calcolatore BTP in pagina (🟡) ✅

**Fatto:**
- [calculator/index.html](../src/intelligent_investor/templates/calculator/index.html): menu
  "Titolo" con i BOT e i BTP in due gruppi, cedola nella striscia del titolo (es. "3,35%
  semestrale"), titolo pagina "Calcolatore BOT e BTP".
- Per un titolo con cedole (`coupon_frequency > 0`) il risultato mostra:
  - Acquisto: corso secco, rateo lordo, prezzo tel quel, rateo pagato al venditore, importo tel
    quel, disaggio maturato, "Credito imposta disaggio" e "Credito imposta sul rateo";
  - nuova sezione Piano cedole: data, lorda per 100, lorda e netta in € per il lotto, totali;
    se è vuota spiega che la vendita avviene prima del prossimo stacco;
  - Vendita/Rimborso: corso secco, e solo per una vendita a metà periodo rateo, tel quel, rateo
    incassato e "Imposta sul rateo incassato"; "Imposta disaggio trattenuta" al posto di
    "rimborsata".
  Le righe del BOT restano identiche. Gli importi sono quelli del DTO, con il loro segno.
- [calculator_controller.py](../src/intelligent_investor/controllers/calculator_controller.py):
  solo testi ("Seleziona un titolo", "Titolo non trovato"); profilo bancario e schema invariati.
- Verificato col client di test Flask su una copia di `data/investor.db` (BTP 3,35% Lug29 a
  scadenza e con vendita anticipata, BOT invariato). Nessun test di pagina: i controller sono
  esclusi dalla copertura.
- Guide: nuova [calcolatore-btp.md](../docs/guides/calcolatore-btp.md) con l'esempio completo sul
  BTP 3,35% Lug29 (acquisto MOT, piano cedole, capital gain, rimborso, bollo, rendimenti) e la
  variante con vendita anticipata; collegata da `calcolatore.md` e `cosa-e-un-btp.md`.

**Piano originale:**

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

## Fase 12 — Duration modificata (🟡) ✅

**Fatto:**
- [duration.py](../src/intelligent_investor/utils/duration.py): `macaulay_duration` e
  `modified_duration`, come `DURATION`/`MDURATION` di LibreOffice (`GetDuration`): flussi residui
  (cedole + rimborso a 100), il primo a una frazione di periodo dal regolamento,
  `frazione d'anno × frequenza − numero cedole`. Nuova `coupon_count` (COUPNUM) in
  `coupon_schedule.py`. Convenzione nella tabella `BOND_CONVENTIONS` (campo `duration`, 30/360).
- Regola della cella `K16`, in `calc_modified_duration` del calcolatore: settlement = acquisto,
  flussi sempre fino alla scadenza anche con vendita anticipata, rendimento = netto composto
  (`K4`); vuota senza cedole, con rendimento ≤ 0 o se il possesso (`M15`) è sotto i 365 giorni.
- Esposta in `SummaryResultDTO.modified_duration` (riepilogo del calcolatore), nel dettaglio bond
  e come colonna "Duration mod." del catalogo. Catalogo e dettaglio usano il loro rendimento
  netto, che esclude il bollo (`K6` invece di `K4`): sul BTP 3,35% Lug29 2,52 contro 2,51.
- Test: niente LibreOffice sulla macchina e Numbers non ha `MDURATION`, quindi i valori attesi di
  3 BTP reali (Lug29 a metà periodo, Dc32 a data cedola, Ap30 sotto la pari) sono
  `−(dP/dy)/P` con `PRICE` e `COUPDAYBS/COUPDAYS` di Numbers (base 0): coincidono a 1e-9, perché
  `PRICE` sconta con gli stessi esponenti. Più formula chiusa per un titolo alla pari, cedola
  annuale, ultimo periodo, regola dei 365 giorni nel calcolatore e nel catalogo.
- Differenza nota: in base act/act la frazione di periodo di LibreOffice (da YEARFRAC) differisce
  da Excel (giorni cedola): sull'esempio di Excel 5,7339 contro 5,7357. Non tocca il foglio, che
  usa base 0.
- Guide: sezione "Quanto si muove il prezzo: la duration" in `cosa-e-un-btp.md` con BTP reali a
  3, 27 e 45 anni; colonna e paragrafo in `catalogo.md`; una riga in `calcolatore-btp.md`.

**Rivisto dopo la Fase 13:** la colonna del catalogo è stata tolta. Chi sceglie un titolo parte
dall'orizzonte, che legge già nella data di scadenza; la duration conta solo per chi vende prima
ed era vuota per tutti i BOT e i BTP sotto l'anno. Resta nella scheda dettaglio e nel riepilogo
del calcolatore, con la frase "se i tassi salgono dell'1%, il prezzo scende di circa il X%";
`CatalogueEntry` non la calcola più (`bond_modified_duration` serve solo il dettaglio).

**Piano originale:**

Il foglio `Bond` la calcola con `MDURATION` (`K16`, solo per durate residue ≥ 1 anno) e la
mostra anche in `ConfrontoRendimenti`.

- Funzione pura in `utils/` (Macaulay → modificata, sui flussi cedolari residui), testata contro
  `MDURATION` per 2–3 titoli.
- Esposta in `SummaryResultDTO`, nel dettaglio bond e come colonna del catalogo.
- **Guide**: spiegare la duration senza formule, come misura del rischio: "se i tassi salgono
  dell'1%, il prezzo scende circa del X%". In `cosa-e-un-btp.md` e nella colonna del catalogo
  (`catalogo.md`).

## Fase 13 — Costi reali nel catalogo (🟡) ✅

**Fatto:**
- Pannello "Parametri avanzati" nel catalogo, chiuso di default (aperto se i parametri sono
  attivi): lotto, profilo bancario o commissioni manuali (%, min, max, fissa), minusvalenze. I
  parametri stanno nella query string e passano a ordinamento, paginazione, filtro e "Per pagina";
  un riquadro sopra la tabella dice quali sono attivi, "Rimuovi" li toglie. Valori non validi:
  avviso e rendimenti di default.
- Solo **MOT**: il catalogo parte dall'ultimo prezzo di titoli già emessi, quindi l'asta non ha
  senso qui (resta nel calcolatore). Bollo trimestrale, tenuta a scadenza.
- `CatalogueService.list_entries(costs=PurchaseCosts(...))`: ogni titolo, BOT compresi, passa dal
  calcolatore (`bond_yields_with_costs`); rendimento netto = netto finale del calcolatore (`K4`),
  nuova colonna "Guadagno netto". Con un profilo la riga MOT è risolta titolo per titolo sui giorni
  emissione–scadenza, come fa il JavaScript del calcolatore (alcune banche, es. Unicredit, hanno
  fasce per durata). Duration sul nuovo rendimento netto.
- Il test "BOT via calcolatore uguale a `bot_yields`" del piano non regge: anche a commissioni zero
  il calcolatore aggiunge il bollo e paga l'imposta sul disaggio all'acquisto invece che a scadenza.
  Il test verifica che la differenza sia circa il bollo (0,20 punti).
- Test: costi che abbassano il netto e lasciano il lordo, commissione che pesa ~0,34 punti su un
  titolo a 6 mesi e meno di un quinto su uno a 5 anni, minimo su lotto piccolo, profilo risolto per
  titolo (campi manuali ignorati), profilo senza riga MOT, parsing e validazione dei parametri.
- Verificato col client di test su una copia di `data/investor.db`: pagina sotto 0,05 s.
- Guide: sezione "Parametri avanzati" in `catalogo.md` con numeri reali (BOT Apr27, BTP Lug29,
  BTP Ot53; lotto da 10.000 € e da 1.000 €) e colonna "Guadagno netto".

**Piano:**

**Decisione:** niente pagina separata come il foglio `ConfrontoRendimenti`. L'utente sceglie il
titolo nel catalogo in base alla durata e al rendimento, poi usa il calcolatore per i numeri
esatti: tra titoli di scadenza simile le commissioni pesano quasi allo stesso modo e la classifica
cambia poco. Il catalogo resta com'è di default e offre i costi reali come opzione avanzata.

**Perché serve comunque:** la commissione si paga una volta ma il rendimento è annuale, quindi
pesa di più sui titoli brevi (0,19% vale circa −0,38 punti/anno su un BOT a 6 mesi, −0,02 su un
BTP a 10 anni) e sui lotti piccoli, dove scatta il minimo. Lo zainetto favorisce i titoli comprati
sotto la pari. Il confronto con i costi reali conta quindi tra durate diverse ("BOT a 6 mesi o
BTP a 2 anni?") e per importi piccoli.

- **Pannello "Parametri avanzati"** nel catalogo, chiuso di default: lotto nominale, profilo
  bancario (riuso di `bank_profile` / `bank_commission`, commissione risolta per mercato e durata
  come nel calcolatore), minusvalenze (mercato: solo MOT, vedi sopra). Valori nella query string, così
  il link si può condividere e l'ordinamento/paginazione li conserva.
- Senza parametri: rendimenti come oggi (100 nominale, nessuna commissione, nessun bollo).
- Con i parametri: ogni titolo passa dal calcolatore unico con acquisto oggi all'ultimo prezzo e
  tenuta a scadenza; il rendimento netto include commissioni, bollo e zainetto, e compare la
  colonna **Guadagno netto (€)**. L'ordinamento per rendimento resta, così si vede se la classifica
  cambia. Un'etichetta sopra la tabella dice quali parametri sono attivi.
- I BOT del catalogo oggi usano una formula a parte (`bot_yields`): con i parametri passano anch'essi
  dal calcolatore (stessi risultati a commissioni zero, da verificare con un test).
- Niente colonne intermedie del foglio (netto al lordo del capital gain, al lordo del bollo,
  minusvalenza, importo pagato): restano nel calcolatore.
- Sostituisce la vecchia voce 4.5 di [`ROADMAP.md`](ROADMAP.md) (spostata dalla Milestone 4,
  step-up, perché è utile già con soli BOT e BTP a tasso fisso).
- **Test**: catalogo con e senza parametri; con commissioni il titolo breve perde più rendimento
  di quello lungo; il minimo di commissione su un lotto piccolo; BOT via calcolatore uguale a
  `bot_yields` a commissioni zero.
- **Guide**: in `catalogo.md` una sezione "Parametri avanzati": quando usarli, perché il rendimento
  cambia rispetto a quello di default (commissioni, bollo, zainetto) e perché pesano di più su
  titoli brevi e importi piccoli. Nessuna guida nuova.

## Fase 14 — Rifiniture (🟢) ✅

**Fatto:**
- **Spesa fissa per cedola** (`K44`): campo `coupon_fee` nel profilo banca (form, dettaglio,
  migrazione `REAL NOT NULL DEFAULT 0`, tutte le banche esistenti a 0) e in `BondTransactionDTO`.
  Si toglie da ogni cedola incassata, compresa l'ultima a scadenza e quella di una vendita in data
  di stacco (`K41`), non da una vendita a metà periodo, dove si incassa il rateo. Entra nel
  guadagno netto e nei rendimenti netti; il lordo resta senza, come il foglio con "Lordo senza
  Commissioni" (`C15`, colonna `AD`). Campo nel calcolatore (precompilato dal profilo) e nei
  parametri avanzati del catalogo (dal profilo, o a mano); il piano cedole mostra le nette già al
  netto della spesa. Corretto anche un difetto vecchio: `create_profile`/`update_profile` non
  salvavano `info_url`.
- **Bollo nei flussi dell'XIRR netto** (colonna `R`): `spread_stamp_duty` divide il bollo sugli
  anni solari tra acquisto e fine (`M17`) e toglie ogni quota dal primo flusso del nuovo anno; se
  acquisto e fine cadono nello stesso anno lo toglie tutto dall'ultimo flusso. Cambia solo il
  rendimento netto composto: sul BTP 3,35% Lug29 della guida 3,004% → 2,995% (a scadenza) e
  3,671% → 3,664% (vendita); per i BOT nulla, con due soli flussi è identico.
- Test: spesa per cedola su tenuta a scadenza (6 cedole) e su vendita tra due stacchi (2 cedole),
  lordo invariato, XIRR netto confrontato con la colonna `R` rifatta a mano, profilo banca che
  salva `coupon_fee` e `info_url`, spesa dal profilo nel catalogo.
- Guide: spesa per cedola in `calcolatore-btp.md`, `calcolatore.md` (profilo bancario e parametri)
  e `catalogo.md`; rendimenti dell'esempio aggiornati. Non esiste una guida delle banche: la spesa
  è spiegata nella sezione "Profilo bancario" di `calcolatore.md`.

**Scartato — book di negoziazione** (foglio `QuotazioneIsin`): nemmeno il foglio lo usa. La macro
`AggiornaQuotazRigaSelect` (`Module3`) scarica in `QuotazioneIsin` la pagina "dati completi" di
Borsa Italiana, che contiene anche il book a 5 livelli (righe 1–7), ma in `Emissioni` colonna `J`
copia solo il "Prezzo ultimo contratto" (riga 16) o, senza contratti, il "Prezzo ufficiale" (riga
31); nessuna formula legge il book. La pagina di dettaglio Teleborsa, già letta dal sync, espone il
miglior denaro/lettera, ma resta l'ultimo prezzo, come nel foglio. Sui BTP liquidi lo
spread è di pochi centesimi (BTP Lug29 al 30/10/2026: denaro 99,28, lettera 99,31, ultimo 99,34),
meno della commissione; il book cambia di continuo mentre noi lo leggeremmo solo a "Aggiorna
Quotazioni", e a mercato chiuso non è significativo. Per i titoli poco scambiati il book si guarda
comunque dalla banca al momento dell'ordine.

**Scartato — rendimenti aggiuntivi del foglio**: netto al lordo del capital gain e del bollo
(`K8`) e ROI totale lordo/netto (`K11`–`K14`). `K8` è un rendimento intermedio che non aiuta a
scegliere; nel foglio il ROI è il rendimento annuo × la durata in anni (`K15`), quindi
un'approssimazione lineare del guadagno totale, che il calcolatore mostra già esatto in euro.
Stessa linea della Fase 13 (niente colonne intermedie di `ConfrontoRendimenti`).

**Piano originale:**

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

## Fase 15 — Calendario aste anche per i BTP (🟡) ✅

**Fatto:**
- Colonna `session` in `bot_auction` (`bot` | `medium_long` | `short`, migrazione
  `VARCHAR(20) NOT NULL DEFAULT 'bot'`: le 23 aste BOT esistenti restano BOT). La tabella tiene il
  suo nome: rinominarla in SQLite vuol dire ricostruirla, senza vantaggi.
- Le sessioni del calendario MEF 2026, lette dalle pagine del PDF: **medio-lungo a metà mese e
  spesso anche a fine mese** (es. 13/10 e 29/10, 12/11 e 27/11), **BTP Short sempre a fine mese**.
  Il DTO lo verifica (BTP Short solo `end_month`); un'asta BTP non ha durata né scadenza proprie
  (`duration_type = 'tbd'`).
- Nuova tabella `auction_offering` (ISIN, nome, scadenza) per i titoli offerti, da inserire dopo il
  comunicato. Il collegamento al catalogo si risolve per ISIN quando si mostra il calendario, così
  una riapertura punta al titolo in archivio e un titolo nuovo non richiede di crearlo; per una
  riapertura basta l'ISIN, nome e scadenza si prendono dal catalogo. Cancellando un'asta si
  cancellano anche i suoi titoli.
- Pagina: titolo "Calendario Aste", filtro **Asta** (BOT, BTP medio-lungo, BTP Short), per le aste
  BTP i titoli offerti o "Titoli dal comunicato del …"; accanto a una riapertura l'icona del
  calcolatore apre `/calculator/?bond_id=…&venue=asta&purchase_date=<regolamento>`. Form con la
  sessione: per i BTP spariscono durata e scadenza (e il periodo per le BTP Short); sezione
  "Titoli offerti" nella modifica di un'asta BTP. Link al calendario MEF 2026 tra le fonti.
- Le Previsioni restano solo BOT (filtro esplicito sulla sessione).
- Dati: inserite nel DB le 4 aste BTP 2026 ancora da tenere (medio-lungo 12/11, 27/11 e 11/12,
  BTP Short 25/11), con presentazione il giorno lavorativo prima dell'asta come per i BOT.
  L'estrazione automatica dal PDF non è affidabile (calendario grafico): le date sono lette dalle
  pagine renderizzate in immagine.
- Test: sessione di default, aste BTP salvate e validate, medio-lungo anche a fine mese, titoli
  offerti (normalizzazione ISIN, ordine per scadenza, cancellazione, cascata), previsioni senza BTP.
  Verificato col client di test su una copia del DB e in Chrome (campi del form per sessione).
- Guide: `calendario.md` riscritta per BOT e BTP (sessioni, comunicato, riaperture e rateo, come
  leggere il calendario); `inizia-qui.md` (tabella e Passo 3).

**Piano originale:**

Oggi il [Calendario Aste](../src/intelligent_investor/templates/auctions/index.html) contiene solo
i BOT (tabella `bot_auction`, 23 aste 2026 inserite a mano): per ogni asta comunicazione,
presentazione, asta, regolamento, durata (annuale/semestrale) e scadenza, che per i BOT si
conoscono già dal calendario annuale.

Il [Calendario Emissioni Titoli di Stato 2026](https://www.dt.mef.gov.it/export/sites/sitodt/modules/documenti_it/debito_pubblico/calendario/Calendario-Emissioni-Titoli-di-Stato-2026.pdf)
del MEF dà per ogni famiglia i giorni di **comunicazione**, **asta** e **regolamento**:
- **BOT** (metà e fine mese);
- **medio-lungo** (metà mese, e spesso anche fine mese): BTP a tasso fisso da 3 a 30/50 anni (BTP Green compresi), insieme
  ai CCTeu;
- **BTP Short e BTP€i** (fine mese): BTP Short Term, cioè BTP a tasso fisso a circa 2–3 anni
  (es. BTP Fx 2.2% Feb28, emesso il 28/02/2026), insieme ai BTP€i.

Medio-lungo e BTP Short sono **sessioni d'asta**, non tipi di titolo: i BTP a tasso fisso gestiti
dal sito escono da entrambe. CCTeu e BTP€i non sono gestiti (cedola variabile o indicizzata).

Differenza chiave: per i BTP il calendario **non dice quali titoli** vanno in asta. Titoli, importi
e se sono nuovi o riaperture si sanno solo dal **comunicato** del giorno di comunicazione (e, a
grandi linee, dal programma trimestrale di emissione). Quindi una riga di calendario BTP nasce con
le sole date e si completa dopo il comunicato.

Proposta (da confermare prima di scrivere codice):
- **Una sola tabella** per tutte le aste: rinominare `bot_auction` in `auction` (o aggiungere una
  colonna) con `session` = `bot` | `medium_long` | `short` (la sessione del calendario MEF, non il
  tipo di titolo). I campi BOT (`duration_type`,
  `maturity_date`) restano validi solo per `bot`; i BOT esistenti diventano `family = bot` con una
  migrazione.
- **Titoli offerti** di un'asta BTP: tabella figlia con un riferimento al titolo del catalogo
  (`bond_id`, per le riaperture) oppure ISIN, nome e scadenza per un titolo nuovo non ancora in
  archivio. Vuota finché non esce il comunicato; si registrano solo i BTP a tasso fisso (non
  CCTeu e BTP€i, che il sito non gestisce).
- **Inserimento**: come per i BOT, a mano dal form, per le date dell'anno (circa 12 aste
  medio-lungo e 12 BTP Short); i titoli dopo ogni comunicato. L'estrazione automatica dal PDF non è
  affidabile: è un calendario grafico e il testo estratto perde l'allineamento giorno/evento.
- **Pagina**: filtro per sessione (BOT, BTP medio-lungo, BTP Short) come nel catalogo; per un BTP in riapertura un link al
  calcolatore con il titolo già selezionato e il mercato Asta.
- **Previsioni**: restano solo BOT. Stimare il prezzo d'asta di un BTP in riapertura dal suo
  ultimo prezzo di mercato è possibile, ma è un'altra fase.
- **Guide**: `calendario.md` (oggi "Calendario Aste BOT") per BOT e BTP, cosa sono comunicazione e
  riapertura; `inizia-qui.md`, tabella "Cosa trovi" e Passo 3.
