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
  - CouponSchedule.first_coupon_amount (irregular first coupon)
  - coupon_count() (COUPNUM)
"""

from datetime import date

import pytest

from intelligent_investor.utils.coupon_schedule import (
    CouponPayment,
    CouponSchedule,
    _days_in_month,
    _subtract_months,
    coupon_count,
)

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
    """ICMA, as in the reference spreadsheet (F36): coupon of the period (1.8) × 90 days
    elapsed (15/01→15/04) / 181 days of the period (15/01→15/07), floored to 6 decimals."""
    settlement = date(2025, 4, 15)
    cs = CouponSchedule(date(2025, 1, 15), date(2030, 1, 15), coupon_frequency=2, nominal_rate=3.6)
    assert cs.accrued_interest(settlement) == 0.895027  # 1.8 × 90 / 181 = 0.8950276...


def test_accrued_interest_exact_value_is_not_floored_down() -> None:
    """2.5% semi-annual, half of a 184-day period: exactly 0.625, not 0.624999."""
    cs = CouponSchedule(date(2025, 6, 1), date(2032, 12, 1), coupon_frequency=2, nominal_rate=2.5)
    assert cs.accrued_interest(date(2026, 3, 2)) == 0.625  # 1.25 × 92 / 184


def test_accrued_interest_before_first_coupon_counts_from_issue_date() -> None:
    """Issued in the middle of a regular period: days are counted from the issue date,
    but the denominator is still the whole regular period (15/01→15/07, 181 days)."""
    issue = date(2025, 3, 1)
    settlement = date(2025, 4, 1)
    cs = CouponSchedule(issue, date(2030, 7, 15), coupon_frequency=2, nominal_rate=3.6)
    assert cs.accrued_interest(settlement) == 0.308287  # 1.8 × 31 / 181 = 0.3082872...


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


def test_schedule_constant_gross_net_amounts_after_first() -> None:
    cs = CouponSchedule(date(2028, 3, 1), date(2030, 7, 15), coupon_frequency=2, nominal_rate=3.6, tax_rate=12.5)
    assert all(p.gross_amount == pytest.approx(cs.gross_coupon_amount) for p in cs.schedule[1:])
    assert all(p.net_amount == pytest.approx(cs.net_coupon_amount) for p in cs.schedule[1:])


# ------------------------------------------------------------------
# Irregular first coupon (cell W4 of the `Bond` sheet)
# ------------------------------------------------------------------


def test_first_coupon_short_is_prorated() -> None:
    # Issued 01/03 inside the regular period 15/01 → 15/07: only 136 of its 182 days accrue
    cs = CouponSchedule(date(2028, 3, 1), date(2030, 7, 15), coupon_frequency=2, nominal_rate=3.6, tax_rate=12.5)
    assert cs.first_coupon_amount == pytest.approx(1.8 * 136 / 182)
    first = cs.schedule[0]
    assert first.payment_date == date(2028, 7, 15)
    assert first.gross_amount == pytest.approx(1.8 * 136 / 182)
    assert first.net_amount == pytest.approx(1.8 * 136 / 182 * 0.875)


def test_first_coupon_full_when_issued_on_coupon_date() -> None:
    cs = CouponSchedule(date(2028, 1, 15), date(2030, 7, 15), coupon_frequency=2, nominal_rate=3.6)
    assert cs.first_coupon_amount == pytest.approx(1.8)
    assert all(p.gross_amount == pytest.approx(1.8) for p in cs.schedule)


def test_first_coupon_date_equal_to_regular_date_changes_nothing() -> None:
    default = CouponSchedule(date(2028, 3, 1), date(2030, 7, 15), coupon_frequency=2, nominal_rate=3.6)
    explicit = CouponSchedule(
        date(2028, 3, 1), date(2030, 7, 15), coupon_frequency=2, nominal_rate=3.6, first_coupon_date=date(2028, 7, 15)
    )
    assert explicit.schedule == default.schedule
    assert explicit.accrued_interest(date(2028, 5, 1)) == default.accrued_interest(date(2028, 5, 1))


def test_first_coupon_long_skips_first_regular_date() -> None:
    # Issued 01/06/2028, first coupon on 15/01/2029: the regular date 15/07/2028 is skipped
    cs = CouponSchedule(
        date(2028, 6, 1), date(2030, 7, 15), coupon_frequency=2, nominal_rate=3.6, first_coupon_date=date(2029, 1, 15)
    )
    assert cs.dates == [date(2029, 1, 15), date(2029, 7, 15), date(2030, 1, 15), date(2030, 7, 15)]
    # Period 15/01/2028 → 15/01/2029 is one act/act year: its coupon is the annual 3.6,
    # of which 228 of its 366 days accrue from issue
    assert cs.first_coupon_amount == pytest.approx(3.6 * 228 / 366)
    assert [p.gross_amount for p in cs.schedule[1:]] == pytest.approx([1.8, 1.8, 1.8])


def test_accrued_interest_before_long_first_coupon() -> None:
    cs = CouponSchedule(
        date(2028, 6, 1), date(2030, 7, 15), coupon_frequency=2, nominal_rate=3.6, first_coupon_date=date(2029, 1, 15)
    )
    # 122 days from issue over the 366 of the long period, on its 3.6 coupon (cell F36)
    assert cs.accrued_interest(date(2028, 10, 1)) == pytest.approx(1.2)
    # After the skipped regular date the rateo keeps growing towards the long coupon
    assert cs.accrued_interest(date(2029, 1, 1)) == pytest.approx(3.6 * 214 / 366, abs=1e-6)
    assert cs.accrued_interest(date(2029, 1, 1)) > cs.gross_coupon_amount
    # On the first coupon date the period restarts
    assert cs.accrued_interest(date(2029, 1, 15)) == 0.0


def test_accrued_interest_reaches_first_coupon_on_coupon_date() -> None:
    cs = CouponSchedule(date(2028, 3, 1), date(2030, 7, 15), coupon_frequency=2, nominal_rate=3.6)
    # The day before the first coupon, the rateo is the short first coupon minus one day
    assert cs.accrued_interest(date(2028, 7, 14)) == pytest.approx(1.8 * 135 / 182, abs=1e-6)


@pytest.mark.parametrize("first_coupon_date", [date(2028, 3, 1), date(2028, 1, 1), date(2030, 8, 1)])
def test_first_coupon_date_out_of_range_raises(first_coupon_date: date) -> None:
    with pytest.raises(ValueError, match="first_coupon_date"):
        CouponSchedule(
            date(2028, 3, 1),
            date(2030, 7, 15),
            coupon_frequency=2,
            nominal_rate=3.6,
            first_coupon_date=first_coupon_date,
        )


def test_first_coupon_amount_zero_frequency() -> None:
    cs = CouponSchedule(date(2025, 1, 1), date(2026, 1, 1), coupon_frequency=0, nominal_rate=0.0)
    assert cs.first_coupon_amount == 0.0


def test_schedule_zero_frequency_returns_empty() -> None:
    cs = CouponSchedule(date(2025, 1, 1), date(2026, 1, 1), coupon_frequency=0, nominal_rate=0.0, tax_rate=12.5)
    assert cs.schedule == []


def test_coupon_payment_is_frozen_dataclass() -> None:
    payment = CouponPayment(payment_date=date(2025, 1, 1), gross_amount=1.8, net_amount=1.575)
    with pytest.raises(AttributeError):
        payment.gross_amount = 2.0  # type: ignore[misc]


# ------------------------------------------------------------------
# coupon_count (COUPNUM)
# ------------------------------------------------------------------


@pytest.mark.parametrize(
    "settlement,expected",
    [
        (date(2026, 10, 29), 6),  # 01/01/2027 ... 01/07/2029
        (date(2027, 1, 1), 5),  # on a coupon date: that coupon is not counted
        (date(2029, 6, 30), 1),  # last period
        (date(2029, 7, 1), 0),  # on maturity
    ],
)
def test_coupon_count(settlement: date, expected: int) -> None:
    assert coupon_count(settlement, date(2029, 7, 1), 2) == expected


def test_coupon_count_zero_frequency() -> None:
    assert coupon_count(date(2026, 1, 1), date(2029, 7, 1), 0) == 0
