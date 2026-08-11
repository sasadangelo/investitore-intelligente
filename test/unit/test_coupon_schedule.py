# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
"""
Unit tests for coupon_schedule.py.

All tests are pure (no DB, no I/O) — they only exercise:
  - CouponSchedule.dates (COUPNCD-style backward anchoring and day clamping)
  - CouponSchedule.previous_coupon_date()
  - CouponSchedule.gross_coupon_amount / net_coupon_amount
  - CouponSchedule.accrued_interest() / net_accrued_interest()
  - CouponSchedule.schedule
"""

from datetime import date

import pytest

from intelligent_investor.utils.coupon_schedule import (
    CouponPayment,
    CouponSchedule,
    _days_in_month,
    _subtract_months,
)
from intelligent_investor.utils.yield_calculator import YearfracBasis, yearfrac

# ------------------------------------------------------------------
# CouponSchedule.dates: basic generation, anchored to maturity, going backward
# ------------------------------------------------------------------


def test_dates_semiannual_multi_year() -> None:
    cs = CouponSchedule(date(2028, 3, 1), date(2030, 7, 15), coupon_frequency=2, nominal_rate=3.6)
    assert cs.dates == [
        date(2028, 7, 15),
        date(2029, 1, 15),
        date(2029, 7, 15),
        date(2030, 1, 15),
        date(2030, 7, 15),
    ]


def test_dates_annual() -> None:
    cs = CouponSchedule(date(2027, 6, 1), date(2030, 6, 1), coupon_frequency=1, nominal_rate=3.6)
    assert cs.dates == [date(2028, 6, 1), date(2029, 6, 1), date(2030, 6, 1)]


def test_dates_last_entry_is_maturity() -> None:
    maturity = date(2032, 9, 1)
    cs = CouponSchedule(date(2025, 1, 1), maturity, coupon_frequency=2, nominal_rate=3.6)
    assert cs.dates[-1] == maturity


def test_dates_ascending_order() -> None:
    cs = CouponSchedule(date(2025, 1, 1), date(2032, 9, 1), coupon_frequency=2, nominal_rate=3.6)
    assert cs.dates == sorted(cs.dates)


def test_dates_issue_on_anchor_date_excluded() -> None:
    # issue_date itself coincides with a coupon anchor: it must NOT appear
    # in the schedule (no coupon accrues from day zero to itself).
    issue = date(2028, 1, 15)
    cs = CouponSchedule(issue, date(2030, 7, 15), coupon_frequency=2, nominal_rate=3.6)
    assert issue not in cs.dates
    assert cs.dates[0] == date(2028, 7, 15)


def test_dates_single_coupon_left() -> None:
    cs = CouponSchedule(date(2030, 2, 1), date(2030, 7, 15), coupon_frequency=2, nominal_rate=3.6)
    assert cs.dates == [date(2030, 7, 15)]


def test_dates_cached_same_object() -> None:
    """Accessing dates twice returns the same cached list (lazy cache)."""
    cs = CouponSchedule(date(2025, 1, 1), date(2030, 1, 1), coupon_frequency=2, nominal_rate=3.6)
    d1 = cs.dates
    d2 = cs.dates
    assert d1 is d2


def test_dates_zero_frequency_returns_empty() -> None:
    cs = CouponSchedule(date(2025, 1, 1), date(2026, 1, 1), coupon_frequency=0, nominal_rate=0.0)
    assert cs.dates == []


def test_zero_frequency_skips_date_validation() -> None:
    # coupon_frequency=0 (BOT) must not raise even with degenerate/reversed dates,
    # since no coupon schedule is ever generated for it.
    cs = CouponSchedule(date(2026, 1, 1), date(2025, 1, 1), coupon_frequency=0, nominal_rate=0.0)
    assert cs.dates == []


def test_issue_not_before_maturity_raises() -> None:
    with pytest.raises(ValueError):
        CouponSchedule(date(2026, 1, 1), date(2025, 1, 1), coupon_frequency=2, nominal_rate=3.6)


def test_unsupported_frequency_raises() -> None:
    with pytest.raises(ValueError):
        CouponSchedule(date(2025, 1, 1), date(2030, 1, 1), coupon_frequency=5, nominal_rate=3.6)


# ------------------------------------------------------------------
# Backward stepping: day-of-month clamping
# ------------------------------------------------------------------


def test_subtract_months_clamps_to_shorter_month() -> None:
    # May 31 minus 3 months → Feb 29 2024 (leap year, clamped from 31)
    assert _subtract_months(date(2024, 5, 31), 3) == date(2024, 2, 29)


def test_subtract_months_clamps_non_leap_february() -> None:
    assert _subtract_months(date(2025, 5, 31), 3) == date(2025, 2, 28)


def test_subtract_months_crosses_year_boundary() -> None:
    assert _subtract_months(date(2025, 2, 15), 3) == date(2024, 11, 15)


def test_days_in_month_leap_and_non_leap_february() -> None:
    assert _days_in_month(2024, 2) == 29
    assert _days_in_month(2025, 2) == 28


def test_days_in_month_december_rolls_to_next_year() -> None:
    assert _days_in_month(2025, 12) == 31


# ------------------------------------------------------------------
# previous_coupon_date
# ------------------------------------------------------------------


def test_previous_coupon_date_before_first_coupon_returns_issue_date() -> None:
    issue = date(2028, 3, 1)
    cs = CouponSchedule(issue, date(2030, 7, 15), coupon_frequency=2, nominal_rate=3.6)
    assert cs.previous_coupon_date(date(2028, 5, 1)) == issue


def test_previous_coupon_date_on_exact_stacco_date() -> None:
    cs = CouponSchedule(date(2028, 3, 1), date(2030, 7, 15), coupon_frequency=2, nominal_rate=3.6)
    assert cs.previous_coupon_date(date(2029, 1, 15)) == date(2029, 1, 15)


def test_previous_coupon_date_mid_period() -> None:
    cs = CouponSchedule(date(2028, 3, 1), date(2030, 7, 15), coupon_frequency=2, nominal_rate=3.6)
    assert cs.previous_coupon_date(date(2029, 4, 15)) == date(2029, 1, 15)


def test_previous_coupon_date_zero_frequency_returns_issue_date() -> None:
    issue = date(2025, 1, 1)
    cs = CouponSchedule(issue, date(2026, 1, 1), coupon_frequency=0, nominal_rate=0.0)
    assert cs.previous_coupon_date(date(2025, 6, 1)) == issue


# ------------------------------------------------------------------
# gross_coupon_amount / net_coupon_amount
# ------------------------------------------------------------------


def test_gross_coupon_amount_semiannual() -> None:
    cs = CouponSchedule(date(2025, 1, 1), date(2030, 1, 1), coupon_frequency=2, nominal_rate=3.6)
    assert cs.gross_coupon_amount == pytest.approx(1.8)


def test_gross_coupon_amount_annual() -> None:
    cs = CouponSchedule(date(2025, 1, 1), date(2030, 1, 1), coupon_frequency=1, nominal_rate=3.6)
    assert cs.gross_coupon_amount == pytest.approx(3.6)


def test_gross_coupon_amount_zero_frequency() -> None:
    cs = CouponSchedule(date(2025, 1, 1), date(2026, 1, 1), coupon_frequency=0, nominal_rate=3.6)
    assert cs.gross_coupon_amount == 0.0


def test_net_coupon_amount_applies_tax_rate() -> None:
    cs = CouponSchedule(date(2025, 1, 1), date(2030, 1, 1), coupon_frequency=2, nominal_rate=3.6, tax_rate=12.5)
    expected = cs.gross_coupon_amount * (1 - 12.5 / 100)
    assert cs.net_coupon_amount == pytest.approx(expected)


def test_net_coupon_amount_default_tax_rate() -> None:
    cs = CouponSchedule(date(2025, 1, 1), date(2030, 1, 1), coupon_frequency=2, nominal_rate=3.6)
    assert cs.net_coupon_amount == pytest.approx(1.8 * (1 - 12.5 / 100))


# ------------------------------------------------------------------
# accrued_interest / net_accrued_interest
# ------------------------------------------------------------------


def test_accrued_interest_zero_on_stacco_date() -> None:
    cs = CouponSchedule(date(2025, 1, 15), date(2030, 1, 15), coupon_frequency=2, nominal_rate=3.6)
    assert cs.accrued_interest(date(2025, 1, 15)) == pytest.approx(0.0)


def test_accrued_interest_known_value_mid_period() -> None:
    settlement = date(2025, 4, 15)
    cs = CouponSchedule(date(2025, 1, 15), date(2030, 1, 15), coupon_frequency=2, nominal_rate=3.6)
    expected = 3.6 * yearfrac(date(2025, 1, 15), settlement, YearfracBasis.ACT_ACT)
    assert cs.accrued_interest(settlement) == pytest.approx(expected)


def test_accrued_interest_before_first_coupon_uses_issue_date() -> None:
    issue = date(2025, 1, 15)
    settlement = date(2025, 3, 1)
    cs = CouponSchedule(issue, date(2030, 7, 15), coupon_frequency=2, nominal_rate=3.6)
    expected = 3.6 * yearfrac(issue, settlement, YearfracBasis.ACT_ACT)
    assert cs.accrued_interest(settlement) == pytest.approx(expected)


def test_accrued_interest_zero_frequency() -> None:
    cs = CouponSchedule(date(2025, 1, 1), date(2026, 1, 1), coupon_frequency=0, nominal_rate=0.0)
    assert cs.accrued_interest(date(2025, 6, 1)) == 0.0


def test_net_accrued_interest_applies_tax_rate() -> None:
    settlement = date(2025, 4, 15)
    cs = CouponSchedule(date(2025, 1, 15), date(2030, 1, 15), coupon_frequency=2, nominal_rate=3.6, tax_rate=12.5)
    gross = cs.accrued_interest(settlement)
    assert cs.net_accrued_interest(settlement) == pytest.approx(gross * (1 - 12.5 / 100))


# ------------------------------------------------------------------
# schedule
# ------------------------------------------------------------------


def test_schedule_matches_dates() -> None:
    cs = CouponSchedule(date(2028, 3, 1), date(2030, 7, 15), coupon_frequency=2, nominal_rate=3.6, tax_rate=12.5)
    assert [p.payment_date for p in cs.schedule] == cs.dates


def test_schedule_constant_gross_net_amounts() -> None:
    cs = CouponSchedule(date(2028, 3, 1), date(2030, 7, 15), coupon_frequency=2, nominal_rate=3.6, tax_rate=12.5)
    assert all(p.gross_amount == pytest.approx(cs.gross_coupon_amount) for p in cs.schedule)
    assert all(p.net_amount == pytest.approx(cs.net_coupon_amount) for p in cs.schedule)


def test_schedule_zero_frequency_returns_empty() -> None:
    cs = CouponSchedule(date(2025, 1, 1), date(2026, 1, 1), coupon_frequency=0, nominal_rate=0.0, tax_rate=12.5)
    assert cs.schedule == []


def test_coupon_payment_is_frozen_dataclass() -> None:
    payment = CouponPayment(payment_date=date(2025, 1, 1), gross_amount=1.8, net_amount=1.575)
    with pytest.raises(AttributeError):
        payment.gross_amount = 2.0  # type: ignore[misc]
