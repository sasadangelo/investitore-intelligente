# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
"""
Unit tests for yield_calculator.py.

All tests are pure (no DB, no I/O) — they only exercise:
  - yearfrac() for all five bases
  - YieldCalculator.simple()
  - YieldCalculator.compound()
  - _yearfrac_act_act() edge cases (leap year, multi-year)
  - _yearfrac_30_360() US and European variants
"""
from datetime import date

import pytest

from intelligent_investor.utils.yield_calculator import (
    YearfracBasis,
    YieldCalculator,
    _yearfrac_30_360,
    _yearfrac_act_act,
    yearfrac,
)

# ------------------------------------------------------------------
# yearfrac: identical dates
# ------------------------------------------------------------------


def test_yearfrac_same_date_returns_zero() -> None:
    d = date(2025, 1, 1)
    assert yearfrac(d, d) == 0.0


def test_yearfrac_swapped_dates_same_result() -> None:
    d1 = date(2025, 1, 1)
    d2 = date(2025, 7, 1)
    assert yearfrac(d1, d2) == yearfrac(d2, d1)


# ------------------------------------------------------------------
# yearfrac: ACT/360 and ACT/365
# ------------------------------------------------------------------


def test_yearfrac_act_360() -> None:
    d1 = date(2025, 1, 1)
    d2 = date(2025, 7, 1)
    days = (d2 - d1).days  # 181
    assert yearfrac(d1, d2, YearfracBasis.ACT_360) == pytest.approx(days / 360.0)


def test_yearfrac_act_365() -> None:
    d1 = date(2025, 1, 1)
    d2 = date(2025, 7, 1)
    days = (d2 - d1).days
    assert yearfrac(d1, d2, YearfracBasis.ACT_365) == pytest.approx(days / 365.0)


# ------------------------------------------------------------------
# yearfrac: US 30/360 and EUR 30/360
# ------------------------------------------------------------------


def test_yearfrac_us_30_360_full_year() -> None:
    # Jan 1 → Jan 1 next year = exactly 1.0
    d1 = date(2024, 1, 1)
    d2 = date(2025, 1, 1)
    assert yearfrac(d1, d2, YearfracBasis.US_30_360) == pytest.approx(1.0)


def test_yearfrac_eur_30_360_full_year() -> None:
    d1 = date(2024, 1, 1)
    d2 = date(2025, 1, 1)
    assert yearfrac(d1, d2, YearfracBasis.EUR_30_360) == pytest.approx(1.0)


def test_yearfrac_30_360_d1_31_normalised_to_30() -> None:
    # d1=Jan 31, d2=Feb 28 → d1 becomes 30 in both conventions
    d1 = date(2025, 1, 31)
    d2 = date(2025, 2, 28)
    yf_us = _yearfrac_30_360(d1, d2, european=False)
    yf_eu = _yearfrac_30_360(d1, d2, european=True)
    # Both should equal (0*360 + 1*30 + (28-30)) / 360 = (30-2)/360
    assert yf_us == pytest.approx((30 - 2) / 360.0)
    assert yf_eu == pytest.approx((30 - 2) / 360.0)


def test_yearfrac_eur_30_360_d2_31_normalised_to_30() -> None:
    d1 = date(2025, 1, 1)
    d2 = date(2025, 3, 31)
    yf_eu = _yearfrac_30_360(d1, d2, european=True)
    # d2.day 31 → 30; days = 0*360 + 2*30 + (30-1) = 89
    assert yf_eu == pytest.approx(89 / 360.0)


def test_yearfrac_unsupported_basis_raises() -> None:
    d1 = date(2025, 1, 1)
    d2 = date(2025, 6, 1)
    with pytest.raises(ValueError):
        yearfrac(d1, d2, basis=99)  # type: ignore[arg-type]


# ------------------------------------------------------------------
# yearfrac: ACT/ACT — short period (<=1 year), leap year effect
# ------------------------------------------------------------------


def test_yearfrac_act_act_non_leap_short() -> None:
    # 2025 is not a leap year; 180 days / 365
    d1 = date(2025, 1, 1)
    d2 = date(2025, 6, 30)  # 180 days, no Feb 29
    assert _yearfrac_act_act(d1, d2) == pytest.approx(180 / 365.0)


def test_yearfrac_act_act_leap_year_feb29_in_range() -> None:
    # 2024 is a leap year; Feb 29 falls strictly between d1 and d2
    d1 = date(2024, 1, 1)
    d2 = date(2024, 6, 30)  # 181 days, includes Feb 29 → denom 366
    assert _yearfrac_act_act(d1, d2) == pytest.approx(181 / 366.0)


def test_yearfrac_act_act_multi_year() -> None:
    # 2 full calendar years spanning 2024 (leap) and 2025 (non-leap)
    # avg year length = (366 + 365) / 2 = 365.5
    d1 = date(2024, 1, 1)
    d2 = date(2026, 1, 1)
    days = (d2 - d1).days  # 731
    expected = days / 365.5
    assert _yearfrac_act_act(d1, d2) == pytest.approx(expected, rel=1e-6)


# ------------------------------------------------------------------
# YieldCalculator: constructor validation
# ------------------------------------------------------------------


def test_yield_calculator_end_before_start_raises() -> None:
    with pytest.raises(ValueError):
        YieldCalculator(date(2025, 6, 1), date(2025, 1, 1))


def test_yield_calculator_same_date_raises() -> None:
    with pytest.raises(ValueError):
        YieldCalculator(date(2025, 1, 1), date(2025, 1, 1))


# ------------------------------------------------------------------
# YieldCalculator: year_fraction properties
# ------------------------------------------------------------------


def test_year_fraction_act_act_365_days() -> None:
    yc = YieldCalculator(date(2025, 1, 1), date(2026, 1, 1))
    # 365 days, no Feb 29 in 2025 → fraction = 365/365 = 1.0
    assert yc.year_fraction == pytest.approx(1.0)


def test_year_fraction_xirr_always_days_over_365() -> None:
    d1 = date(2024, 1, 1)
    d2 = date(2024, 7, 1)
    days = (d2 - d1).days
    yc = YieldCalculator(d1, d2)
    assert yc.year_fraction_xirr == pytest.approx(days / 365.0)


def test_year_fraction_cached() -> None:
    """Calling year_fraction twice returns the same object (lazy cached)."""
    yc = YieldCalculator(date(2025, 1, 1), date(2025, 7, 1))
    f1 = yc.year_fraction
    f2 = yc.year_fraction
    assert f1 is f2


# ------------------------------------------------------------------
# YieldCalculator.simple()
# ------------------------------------------------------------------


def test_simple_yield_known_value() -> None:
    # 365-day BOT: price 98, gain = 2, capital = 98, yf = 1.0 → 2/98 * 100 ≈ 2.0408%
    d1 = date(2025, 1, 1)
    d2 = date(2026, 1, 1)
    yc = YieldCalculator(d1, d2)
    result = yc.simple(gain=2.0, capital=98.0)
    assert result == pytest.approx(2.0 / 98.0 * 100, rel=1e-4)


# ------------------------------------------------------------------
# YieldCalculator.compound()
# ------------------------------------------------------------------


def test_compound_yield_known_value() -> None:
    # 365 days, price 98, redeem 100: XIRR = (100/98)^(365/365) - 1 ≈ 2.0408%
    d1 = date(2025, 1, 1)
    d2 = date(2026, 1, 1)
    yc = YieldCalculator(d1, d2)
    result = yc.compound(final_proceeds=100.0, capital=98.0)
    assert result == pytest.approx((100.0 / 98.0 - 1.0) * 100, rel=1e-4)


def test_compound_yield_half_year() -> None:
    # 182-day BOT, price 99.0
    d1 = date(2025, 1, 1)
    d2 = date(2025, 7, 2)  # 182 days
    days = (d2 - d1).days
    yc = YieldCalculator(d1, d2)
    expected = ((100.0 / 99.0) ** (365.0 / days) - 1.0) * 100
    assert yc.compound(100.0, 99.0) == pytest.approx(expected, rel=1e-5)


def test_simple_less_than_compound_for_discount_bond() -> None:
    """For a zero-coupon bond bought at discount, compound > simple (compounding effect)."""
    d1 = date(2025, 1, 1)
    d2 = date(2025, 7, 1)
    yc = YieldCalculator(d1, d2)
    gain = 100.0 - 98.5
    assert yc.simple(gain, 98.5) < yc.compound(100.0, 98.5)
