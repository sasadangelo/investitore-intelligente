# Investitore Intelligente

**Investitore Intelligente** is a Python/Flask web application for managing and analysing investments in Italian government bonds, with a focus on BOT (Buoni Ordinari del Tesoro — short-term Treasury bills).

It lets you track a bond catalogue, monitor market prices, plan upcoming auctions, and calculate net yields with precision — accounting for bank commissions, withholding tax, and inflation.

---

## Features

- **Bond catalogue** — Create, update and delete BTP, BOT and other government bonds; automatic quote synchronisation from Teleborsa.
- **BOT auction calendar** — Manage upcoming auctions with settlement dates, duration, issue price and estimated yields.
- **BOT price forecast** — Estimate the issue price for future auctions using a weighted average of implied yields from active BOTs of the same duration group.
- **BOT calculator** — Full gross/net yield calculation (simple and compound/XIRR) for primary-market (asta) or secondary-market (MOT) purchases, with support for bank-specific commission schedules.
- **Bank profiles** — Library of commission structures for the main Italian banks (asta and MOT venues), with automatic resolution of the applicable commission given venue and holding period.
- **Guides** — Integrated Markdown documentation on calculation logic and financial concepts.

---

## Requirements

- Python >= 3.10, < 3.15
- [uv](https://github.com/astral-sh/uv) (package manager and virtualenv tool)

---

## Running locally

```bash
# 1. Clone the repository
git clone https://github.com/sasadangelo/investitore-intelligente.git
cd investitore-intelligente

# 2. Install dependencies (creates .venv/ automatically)
uv sync

# 3. Start the application
./app.sh
```

The application will be available at **http://localhost:5001**.

Alternatively, without the shell script:

```bash
uv run python app.py
```

---

## Unit tests

```bash
# Run all tests
uv run pytest

# Verbose output
uv run pytest -v
```

### Coverage

```bash
# Text report with missing lines
uv run pytest --cov

# HTML report (open htmlcov/index.html in a browser)
uv run pytest --cov --cov-report=html
```

Coverage configuration lives in [`pyproject.toml`](pyproject.toml). The source root is `src/`; tests run against an in-memory SQLite database and never touch `data/investor.db`.

---

## Project structure

```
investitore-intelligente/
├── app.py                          # Flask entry point (application factory)
├── app.sh                          # Startup script (activates .venv, launches app.py)
├── pyproject.toml                  # Dependencies, ruff/mypy/pytest/coverage config
│
├── src/intelligent_investor/
│   ├── clients/                    # HTTP client for Teleborsa scraping
│   ├── controllers/                # Flask blueprints (bond, bot_auction, bank, guide)
│   ├── core/                       # Configuration (config.yaml) and logging (loguru)
│   ├── db/                         # SQLAlchemy engine and session manager
│   ├── dtos/                       # Pydantic models (data transfer between layers)
│   ├── models/                     # SQLAlchemy ORM (DAOs: BondDAO, BotAuctionDAO, …)
│   ├── services/                   # Business logic
│   │   ├── bank_profile_service.py # CRUD bank profiles + commission resolution
│   │   ├── bond_service.py         # CRUD bond catalogue
│   │   ├── bond_quote_service.py   # CRUD bond quotes
│   │   ├── bond_sync_service.py    # Quote synchronisation from Teleborsa
│   │   ├── bot_auction_service.py  # CRUD BOT auction calendar
│   │   ├── bot_calculator_service.py # BOT yield calculator
│   │   ├── bot_forecast_service.py # Issue price forecast for future auctions
│   │   └── guide_service.py        # Markdown guide loader
│   ├── templates/                  # Jinja2 HTML templates
│   ├── static/                     # Static assets (SVG, CSS)
│   └── utils/
│       └── yield_calculator.py     # YEARFRAC and yield computation (simple/XIRR)
│
├── docs/guides/                    # Markdown guides (served inside the app)
├── data/investor.db                # SQLite database (real data, excluded from tests)
├── logs/                           # Runtime log files
│
└── test/
    ├── conftest.py                 # Shared in-memory SQLite engine for all tests
    └── unit/
        ├── test_bank_profile_service.py
        ├── test_bond_service.py
        ├── test_bond_quote_service.py
        ├── test_bot_auction_service.py
        ├── test_bot_calculator_service.py
        ├── test_bot_forecast_service.py
        ├── test_yield_calculator.py
        └── fixtures/               # JSON fixtures for parametric calculator tests
```

---

## License

Distributed under the **MIT** License. See [LICENSE.md](LICENSE.md) for details.

© 2026 Salvatore D'Angelo, Code4Projects
