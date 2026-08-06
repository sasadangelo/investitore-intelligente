# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
"""
Unit tests for BondDTO.

Pure Pydantic validation — no DB, no I/O.
Covers:
  - check_dates validator
  - default field values
  - mef_auction_result_url property (BOT semiannual, BOT annual, non-BOT, stored URL)
"""
from datetime import date, timedelta

import pytest

from intelligent_investor.dtos.bond import BondDTO

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

TODAY = date(2025, 6, 1)


def _make_bot(
    issue_date: date = date(2025, 1, 15),
    maturity_date: date = date(2026, 1, 14),
    bond_type: str = "BOT",
    auction_result_url: str | None = None,
) -> BondDTO:
    return BondDTO(
        name="BOT Test",
        isin="IT0005000001",
        bond_type=bond_type,
        issue_date=issue_date,
        maturity_date=maturity_date,
        issue_price=98.5,
        auction_result_url=auction_result_url,
    )


# ------------------------------------------------------------------
# check_dates validator
# ------------------------------------------------------------------


def test_issue_date_before_maturity_is_valid() -> None:
    bond = _make_bot(issue_date=date(2025, 1, 1), maturity_date=date(2026, 1, 1))
    assert bond.issue_date < bond.maturity_date


def test_issue_date_equal_maturity_raises() -> None:
    d = date(2025, 6, 1)
    with pytest.raises(ValueError, match="issue_date"):
        _make_bot(issue_date=d, maturity_date=d)


def test_issue_date_after_maturity_raises() -> None:
    with pytest.raises(ValueError, match="issue_date"):
        _make_bot(issue_date=date(2025, 12, 1), maturity_date=date(2025, 1, 1))


# ------------------------------------------------------------------
# Default field values
# ------------------------------------------------------------------


def test_default_redemption_price() -> None:
    bond = _make_bot()
    assert bond.redemption_price == 100.0


def test_default_nominal_rate_zero() -> None:
    bond = _make_bot()
    assert bond.nominal_rate == 0.0


def test_default_coupon_frequency_zero() -> None:
    bond = _make_bot()
    assert bond.coupon_frequency == 0


def test_default_tax_rate() -> None:
    bond = _make_bot()
    assert bond.tax_rate == 12.5


def test_default_id_is_none() -> None:
    bond = _make_bot()
    assert bond.id is None


# ------------------------------------------------------------------
# mef_auction_result_url — non-BOT returns None
# ------------------------------------------------------------------


def test_mef_url_non_bot_returns_none() -> None:
    bond = _make_bot(bond_type="BTP")
    assert bond.mef_auction_result_url is None


def test_mef_url_stored_url_wins() -> None:
    stored = "https://example.com/risultato.pdf"
    bond = _make_bot(auction_result_url=stored)
    assert bond.mef_auction_result_url == stored


# ------------------------------------------------------------------
# mef_auction_result_url — semiannual BOT (duration <= 200 days)
# ------------------------------------------------------------------


def test_mef_url_semiannual_contains_6_mesi() -> None:
    # 180-day BOT
    issue = date(2025, 6, 2)
    maturity = date(2025, 11, 29)  # 180 days
    bond = _make_bot(issue_date=issue, maturity_date=maturity)
    url = bond.mef_auction_result_url
    assert url is not None
    assert "6_mesi" in url
    assert "6-Mesi" in url


def test_mef_url_semiannual_auction_date_in_filename() -> None:
    issue = date(2025, 6, 2)      # settlement = issue_date
    maturity = date(2025, 11, 29)
    bond = _make_bot(issue_date=issue, maturity_date=maturity)
    url = bond.mef_auction_result_url
    assert url is not None
    # d2 = issue - 1 = 2025-06-01 → "01"
    # d1 = issue - 2 = 2025-05-31 → "31"
    assert "31-01.06.2025" in url


# ------------------------------------------------------------------
# mef_auction_result_url — annual BOT (duration > 200 days)
# ------------------------------------------------------------------


def test_mef_url_annual_contains_annuali() -> None:
    # 365-day BOT
    issue = date(2025, 1, 15)
    maturity = date(2026, 1, 14)
    bond = _make_bot(issue_date=issue, maturity_date=maturity)
    url = bond.mef_auction_result_url
    assert url is not None
    assert "annuali" in url
    assert "Annuale" in url


def test_mef_url_annual_auction_date_in_filename() -> None:
    issue = date(2025, 1, 15)
    maturity = date(2026, 1, 14)
    bond = _make_bot(issue_date=issue, maturity_date=maturity)
    url = bond.mef_auction_result_url
    assert url is not None
    # d2 = 2025-01-14, d1 = 2025-01-13
    assert "13-14.01.2025" in url


def test_mef_url_base_domain() -> None:
    bond = _make_bot()
    url = bond.mef_auction_result_url
    assert url is not None
    assert url.startswith("https://www.dt.mef.gov.it")
