# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
"""
Unit tests for BotForecastService.

The service depends on BondService, BondQuoteService and BotAuctionService.
We mock them so tests are pure, fast, and DB-free.
"""
from datetime import date, timedelta
from unittest.mock import MagicMock

import pytest

from intelligent_investor.dtos.bond import BondDTO
from intelligent_investor.dtos.bond_quote import BondQuoteDTO
from intelligent_investor.dtos.bot_auction import BotAuctionDTO
from intelligent_investor.services.bot_forecast_service import (
    ANNUAL_MIN_DAYS,
    MIN_BONDS,
    BotForecastService,
    _duration_group,
    _implied_gross_yield,
)

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

TODAY = date(2025, 6, 1)


def _auction(
    auction_date: date,
    settlement_date: date,
    maturity_date: date | None,
    duration_type: str = "annual",
    days: int | None = 365,
) -> BotAuctionDTO:
    return BotAuctionDTO(
        auction_date=auction_date,
        settlement_date=settlement_date,
        maturity_date=maturity_date,
        duration_type=duration_type,
        days=days,
    )


def _bond(
    bond_id: int,
    issue_date: date,
    maturity_date: date,
    name: str = "BOT Test",
) -> BondDTO:
    return BondDTO(
        id=bond_id,
        name=name,
        isin=f"IT000{bond_id:07d}",
        bond_type="BOT",
        issue_date=issue_date,
        maturity_date=maturity_date,
        issue_price=98.0,
    )


def _quote(bond_id: int, last_price: float) -> BondQuoteDTO:
    return BondQuoteDTO(bond_id=bond_id, last_price=last_price)


def _service_with_mocks(
    auctions: list[BotAuctionDTO],
    bonds: list[BondDTO],
    quotes: list[BondQuoteDTO],
) -> BotForecastService:
    svc = BotForecastService.__new__(BotForecastService)
    svc._bond_svc = MagicMock()
    svc._quote_svc = MagicMock()
    svc._auction_svc = MagicMock()
    svc._bond_svc.list_all.return_value = bonds
    svc._quote_svc.list_all.return_value = quotes
    svc._auction_svc.list_all.return_value = auctions
    return svc


# ------------------------------------------------------------------
# Pure function tests
# ------------------------------------------------------------------


def test_implied_gross_yield_positive_price_and_days() -> None:
    # 365 days, price 98.0: yield ≈ (100/98)^1 - 1 ≈ 2.04%
    y = _implied_gross_yield(98.0, 365)
    assert pytest.approx(y, rel=1e-4) == (100.0 / 98.0) - 1.0


def test_implied_gross_yield_zero_days_returns_zero() -> None:
    assert _implied_gross_yield(98.0, 0) == 0.0


def test_implied_gross_yield_zero_price_returns_zero() -> None:
    assert _implied_gross_yield(0.0, 180) == 0.0


def test_duration_group_annual() -> None:
    assert _duration_group(ANNUAL_MIN_DAYS) == "annual"
    assert _duration_group(365) == "annual"


def test_duration_group_semiannual() -> None:
    assert _duration_group(ANNUAL_MIN_DAYS - 1) == "semiannual"
    assert _duration_group(180) == "semiannual"


# ------------------------------------------------------------------
# _forecast_one: tbd auction
# ------------------------------------------------------------------


def test_forecast_tbd_auction_returns_unavailable() -> None:
    svc = _service_with_mocks([], [], [])
    a = _auction(
        auction_date=TODAY + timedelta(days=10),
        settlement_date=TODAY + timedelta(days=12),
        maturity_date=None,
        duration_type="tbd",
        days=None,
    )
    result = svc._forecast_one(a, [], {}, TODAY)
    assert result.available is False
    assert result.estimated_price is None


def test_forecast_maturity_none_returns_unavailable() -> None:
    svc = _service_with_mocks([], [], [])
    a = _auction(
        auction_date=TODAY + timedelta(days=5),
        settlement_date=TODAY + timedelta(days=7),
        maturity_date=None,
        duration_type="annual",
        days=None,
    )
    result = svc._forecast_one(a, [], {}, TODAY)
    assert result.available is False


# ------------------------------------------------------------------
# _forecast_one: not enough bonds
# ------------------------------------------------------------------


def test_forecast_insufficient_bonds_returns_unavailable() -> None:
    svc = _service_with_mocks([], [], [])
    a = _auction(
        auction_date=TODAY + timedelta(days=10),
        settlement_date=TODAY + timedelta(days=12),
        maturity_date=TODAY + timedelta(days=377),
        duration_type="annual",
        days=365,
    )
    # only 1 annual bond — below MIN_BONDS=2
    bond = _bond(1, TODAY - timedelta(days=10), TODAY + timedelta(days=355))
    quotes = {1: _quote(1, 98.0)}
    result = svc._forecast_one(a, [bond], quotes, TODAY)
    assert result.available is False
    assert len(result.data_points) == MIN_BONDS - 1


# ------------------------------------------------------------------
# _forecast_one: successful forecast
# ------------------------------------------------------------------


def test_forecast_two_annual_bonds_returns_available() -> None:
    svc = _service_with_mocks([], [], [])
    a = _auction(
        auction_date=TODAY + timedelta(days=10),
        settlement_date=TODAY + timedelta(days=12),
        maturity_date=TODAY + timedelta(days=377),
        duration_type="annual",
        days=365,
    )
    # Two annual bonds (total duration >= ANNUAL_MIN_DAYS)
    b1 = _bond(1, TODAY - timedelta(days=30), TODAY + timedelta(days=335), name="BOT Annual A")
    b2 = _bond(2, TODAY - timedelta(days=20), TODAY + timedelta(days=345), name="BOT Annual B")
    quotes = {1: _quote(1, 98.5), 2: _quote(2, 98.0)}
    result = svc._forecast_one(a, [b1, b2], quotes, TODAY)
    assert result.available is True
    assert result.estimated_price is not None
    assert result.gross_yield_pct is not None
    assert result.net_yield_pct is not None
    assert result.avg_implied_yield_pct is not None
    # net yield must be lower than gross (tax reduces return)
    assert result.net_yield_pct < result.gross_yield_pct


def test_forecast_semiannual_ignores_annual_bonds() -> None:
    """Semiannual auction must not pick up annual-duration bonds."""
    svc = _service_with_mocks([], [], [])
    a = _auction(
        auction_date=TODAY + timedelta(days=5),
        settlement_date=TODAY + timedelta(days=7),
        maturity_date=TODAY + timedelta(days=187),
        duration_type="semiannual",
        days=180,
    )
    # Two annual bonds — should be excluded from semiannual forecast
    b1 = _bond(1, TODAY - timedelta(days=30), TODAY + timedelta(days=335))
    b2 = _bond(2, TODAY - timedelta(days=20), TODAY + timedelta(days=345))
    quotes = {1: _quote(1, 98.5), 2: _quote(2, 98.0)}
    result = svc._forecast_one(a, [b1, b2], quotes, TODAY)
    assert result.available is False  # no semiannual bonds → unavailable


def test_forecast_bond_without_quote_excluded() -> None:
    svc = _service_with_mocks([], [], [])
    a = _auction(
        auction_date=TODAY + timedelta(days=10),
        settlement_date=TODAY + timedelta(days=12),
        maturity_date=TODAY + timedelta(days=377),
        duration_type="annual",
        days=365,
    )
    b1 = _bond(1, TODAY - timedelta(days=30), TODAY + timedelta(days=335))
    b2 = _bond(2, TODAY - timedelta(days=20), TODAY + timedelta(days=345))
    # solo b1 ha una quote; b2 non ha quote → non abbastanza dati
    quotes = {1: _quote(1, 98.5)}
    result = svc._forecast_one(a, [b1, b2], quotes, TODAY)
    assert result.available is False


# ------------------------------------------------------------------
# forecast_all integration (via mocked services)
# ------------------------------------------------------------------


def test_forecast_all_skips_past_auctions() -> None:
    past_auction = _auction(
        auction_date=TODAY - timedelta(days=10),
        settlement_date=TODAY - timedelta(days=8),  # past
        maturity_date=TODAY + timedelta(days=357),
        duration_type="annual",
        days=365,
    )
    svc = _service_with_mocks([past_auction], [], [])
    results = svc.forecast_all()
    assert results == []


def test_forecast_all_returns_one_result_per_future_auction() -> None:
    a1 = _auction(TODAY + timedelta(days=5), TODAY + timedelta(days=7), TODAY + timedelta(days=372), days=365)
    a2 = _auction(TODAY + timedelta(days=12), TODAY + timedelta(days=14), TODAY + timedelta(days=194), duration_type="semiannual", days=180)
    b1 = _bond(1, TODAY - timedelta(days=30), TODAY + timedelta(days=335))
    b2 = _bond(2, TODAY - timedelta(days=20), TODAY + timedelta(days=345))
    b3 = _bond(3, TODAY - timedelta(days=10), TODAY + timedelta(days=170), name="BOT Semi A")
    b4 = _bond(4, TODAY - timedelta(days=5), TODAY + timedelta(days=160), name="BOT Semi B")
    qs = [_quote(1, 98.5), _quote(2, 98.0), _quote(3, 99.0), _quote(4, 99.1)]
    svc = _service_with_mocks([a1, a2], [b1, b2, b3, b4], qs)
    results = svc.forecast_all()
    assert len(results) == 2
