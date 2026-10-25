# Roadmap — Investitore Intelligente

## Priority legend
- 🔴 High — core feature or frequently requested
- 🟡 Medium — significantly improves user experience
- 🟢 Low — nice-to-have, completes the offering

---

## Order of work

Milestone numbers are stable identifiers (other documents refer to them), not the order of work.

1. **Now — Milestone 3** (fixed-rate BTP): see [`docs/roadmap-btp.md`](docs/roadmap-btp.md) for phases and status.
2. **Next** — Milestones 4 to 8, in the order listed below.
3. **Deferred — Milestone 1** (more bank profiles): listed last.

---

## Milestone 3 — BTP support (fixed-rate)
> Goal: support standard fixed-coupon BTPs in the catalogue and the calculator, with results
> matching the reference spreadsheet (`docs/ObbligazioniTF v5.0.ods`).
>
> Phases, status and technical details live only in [`docs/roadmap-btp.md`](docs/roadmap-btp.md).

**Status:**
- ✅ Done (phases 1–8): coupon schedule and accrued interest, multi-flow XIRR, BTP catalogue with
  yields, import of 108 fixed-rate BTPs, MOT quote sync, single BOT/BTP calculator with the issue
  discount (checked against the spreadsheet).
- 🔴 Next (phases 9–10): accrued interest convention and taxes, irregular first coupon.
- 🟡 Then (phases 11–14): BTP calculator page, modified duration, yield comparison (formerly
  item 4.5), refinements.
- Phases are numbered in execution order. User guides and tests are updated with every phase.

---

## Milestone 4 — Step-up BTP (BTP Valore / BTP Italia / BTP Più)
> Goal: support BTPs with increasing or inflation-linked coupons.

| # | Feature | Notes | Priority |
|---|---|---|---|
| 4.1 | BTP Valore | Step-up coupon (increasing each semester), loyalty bonus at maturity | 🔴 |
| 4.2 | BTP Italia | Semi-annual coupon + FOIEX capital revaluation, loyalty bonus | 🟡 |
| 4.3 | BTP Più | Step-up coupon with early redemption option at year 4 | 🟡 |
| 4.4 | Future coupon calculator | Table of expected coupons per year/semester with net amounts | 🔴 |

> Item 4.5 (BOT vs BTP comparison) moved to Milestone 3 as phase 13 of [`docs/roadmap-btp.md`](docs/roadmap-btp.md);
> step-up BTPs will be added to that comparison when this milestone is done.

---

## Milestone 5 — Corporate bonds
> Goal: support Italian and foreign corporate bonds listed on MOT/EuroTLX.

| # | Feature | Notes | Priority |
|---|---|---|---|
| 5.1 | Corporate bond data model | Rating, issuer, ISIN, coupon, maturity, subordination level | 🔴 |
| 5.2 | Corporate bond calculator | YTM, spread vs BTP, 26% taxation (no 12.5% relief) | 🔴 |
| 5.3 | Corporate bond catalogue | With MOT/EuroTLX quotes | 🟡 |
| 5.4 | Issuer risk indicator | Credit rating display (S&P / Moody's / Fitch) | 🟢 |

---

## Milestone 6 — Macroeconomic data dashboard
> Goal: provide key macro context to help users interpret bond yields.

| # | Indicator | Source | Priority |
|---|---|---|---|
| 6.1 | **ECB interest rate** (deposit facility) | ECB Data Portal API | 🔴 |
| 6.2 | **Fed Funds Rate** | FRED (Federal Reserve St. Louis) API | 🔴 |
| 6.3 | **Italian inflation (IPCA / FOI)** | ISTAT / Eurostat | 🔴 |
| 6.4 | **US inflation (CPI)** | FRED API | 🟡 |
| 6.5 | **Italian GDP growth (YoY)** | ISTAT / Eurostat | 🟡 |
| 6.6 | **US GDP growth (YoY)** | FRED / BEA API | 🟡 |
| 6.7 | **EUR/USD exchange rate** | ECB or open exchange rates | 🟡 |
| 6.8 | **10Y BTP yield** | MOT / MTS data | 🟡 |
| 6.9 | **BTP-Bund spread** | Derived from 10Y BTP and 10Y Bund | 🟡 |
| 6.10 | **Real yield** (BTP yield − inflation) | Derived | 🟢 |
| 6.11 | Macro dashboard page | Cards with current values, trend arrows, last-updated timestamp | 🔴 |
| 6.12 | Historical charts | 1Y / 3Y / 5Y chart for each indicator | 🟢 |

---

## Milestone 7 — Authentication and user profiles
> Goal: make the service multi-user with distinct roles.

| # | Feature | Notes | Priority |
|---|---|---|---|
| 7.1 | Authentication | Flask session login/logout, bcrypt password hashing | 🔴 |
| 7.2 | User registration | Registration form with email confirmation | 🔴 |
| 7.3 | Admin role | Full CRUD on bonds, banks, auctions, users | 🔴 |
| 7.4 | User role | Calculator access, personal portfolio, read-only catalogue | 🔴 |
| 7.5 | Password reset | Via email (time-limited token) | 🟡 |
| 7.6 | User management (admin) | User list, enable/disable, role change | 🟡 |

---

## Milestone 8 — Portfolio management
> Goal: allow users to track their purchases and monitor their portfolio.

| # | Feature | Notes | Priority |
|---|---|---|---|
| 8.1 | Record a purchase | Save BOT transaction (date, price, lot, commissions, bank) | 🔴 |
| 8.2 | Active portfolio | Open positions with current value, accrued yield, days to maturity | 🔴 |
| 8.3 | Transaction history | All closed trades with realised net gain | 🔴 |
| 8.4 | Summary dashboard | Total invested, expected return, upcoming maturities, asset allocation | 🔴 |
| 8.5 | Maturity alerts | In-app or email notification N days before a BOT matures | 🟡 |
| 8.6 | CSV / Excel export | Portfolio and history export for tax return preparation | 🟡 |
| 8.7 | Multi-instrument portfolio | BOT + BTP + Corporate Bond in a single view | 🟢 |

---

## Milestone 1 — Bank profile data completion (deferred)
> Goal: cover the banks most used by Italian retail investors for BOT purchases.
> **Deferred**: the existing bank profiles are enough to use the calculators. Resume after
> Milestone 3; the BTP work only reuses the existing profiles (government bond section).

### 1.1 — Banks to add

| #    | Bank | Profiles | Priority | Notes |
|------|---|---|---|---|
| 1.1  | **Banca Sella** | Internet Banking | 🟡 | Well-regarded by digital investors |
| 1.2  | **CheBanca! (Mediobanca)** | Internet Banking | 🟡 | Similar target audience to Fineco |
| 1.3  | **Mediolanum** | Internet Banking | 🟡 | Wide customer base via financial advisors |
| 1.4  | **Credem (Credito Emiliano)** | Filiale, Internet Banking | 🟡 | Strong in Emilia-Romagna |
| 1.5  | **Banco di Sardegna** | Filiale, Internet Banking | 🟢 | Relevant in Sardinia |
| 1.6  | **Cassa Depositi e Prestiti / CDP** | — | 🟢 | Issues BTP but no retail brokerage |
| 1.7 | **Trade Republic** | App | 🟢 | Growing among younger investors; BOT support limited |
| 1.8 | **Revolut** | App | 🟢 | Large user base but limited Italian government bond support |
| 1.9 | **Degiro** | Online | 🟢 | Popular discount broker; MOT access available |
| 1.10 | **Flatex** | Online | 🟢 | German broker with Italian MOT access |

> **Note:** for each profile, collect the official information sheet and set `info_url`.

---

## Cross-cutting technical items

| Topic | Description | Priority |
|---|---|---|
| **DB migrations** | Introduce Alembic for controlled schema migrations | 🔴 |
| **REST API** | JSON API endpoints for future mobile clients or external integrations | 🟡 |
| **Production deploy** | gunicorn + nginx + HTTPS, environment variables, Docker image | 🟡 |
| **i18n** | Optional multilingual support (Italian / English) | 🟢 |
