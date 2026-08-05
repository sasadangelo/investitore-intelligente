# Roadmap — Investitore Intelligente

## Priority legend
- 🔴 High — core feature or frequently requested
- 🟡 Medium — significantly improves user experience
- 🟢 Low — nice-to-have, completes the offering

---

## Milestone 1 — Bank profile data completion
> Goal: cover the banks most used by Italian retail investors for BOT purchases.

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

## Milestone 3 — BTP support (fixed-rate)
> Goal: extend the calculator to standard fixed-coupon BTPs.

| # | Feature | Notes | Priority |
|---|---|---|---|
| 3.1 | BTP data model | Extend `BondDTO` / new entity with coupon, frequency, maturity | 🔴 |
| 3.2 | BTP calculator | Dirty price, accrued interest, YTM gross/net, modified duration | 🔴 |
| 3.3 | BTP catalogue | Active BTPs with MOT quotes and current yield | 🔴 |
| 3.4 | Discount/premium tax | 12.5% withholding on discount; coupon not subject to capital gain tax | 🟡 |
| 3.5 | Capital gain on early sale | Purchase load price vs sale price, 26% tax | 🟡 |
| 3.6 | Bank commissions for BTP | Reuse existing bank profiles (government bond section) | 🟡 |

---

## Milestone 4 — Step-up BTP (BTP Valore / BTP Italia / BTP Più)
> Goal: support BTPs with increasing or inflation-linked coupons.

| # | Feature | Notes | Priority |
|---|---|---|---|
| 4.1 | BTP Valore | Step-up coupon (increasing each semester), loyalty bonus at maturity | 🔴 |
| 4.2 | BTP Italia | Semi-annual coupon + FOIEX capital revaluation, loyalty bonus | 🟡 |
| 4.3 | BTP Più | Step-up coupon with early redemption option at year 4 | 🟡 |
| 4.4 | Future coupon calculator | Table of expected coupons per year/semester with net amounts | 🔴 |
| 4.5 | BOT vs BTP comparison | Net annualised yield on the same time horizon | 🟡 |

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

## Cross-cutting technical items

| Topic | Description | Priority |
|---|---|---|
| **DB migrations** | Introduce Alembic for controlled schema migrations | 🔴 |
| **Unit tests** | pytest coverage for all calculation services | 🔴 |
| **REST API** | JSON API endpoints for future mobile clients or external integrations | 🟡 |
| **Production deploy** | gunicorn + nginx + HTTPS, environment variables, Docker image | 🟡 |
| **i18n** | Optional multilingual support (Italian / English) | 🟢 |
