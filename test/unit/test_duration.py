# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
"""
Unit tests for duration.py (MDURATION, cell K16 of the `Bond` sheet).

The expected values of the real BTPs are the modified duration by definition,
−(dP/dy) / P on the tel quel price P, with P from PRICE and COUPDAYBS/COUPDAYS of
a spreadsheet (Apple Numbers, basis 0) and dP/dy as a central difference with a
step of 1e-6 on the yield. PRICE discounts the flows with the same exponents as
MDURATION, so the two coincide; Numbers has no MDURATION to compare with directly.
"""
from datetime import date

import pytest

from intelligent_investor.utils.day_count import DayCountConvention
from intelligent_investor.utils.duration import macaulay_duration, modified_duration

_ABS = 1e-6


@pytest.mark.parametrize(
    "settlement,maturity,nominal_rate,yield_pct,expected",
    [
        # BTP 3,35% Lug29, mid-period (accrued 118/180 of the period in 30/360)
        (date(2026, 10, 29), date(2029, 7, 1), 3.35, 3.004, 2.514291),
        # BTP 2,5% Dc32, settlement on a coupon date
        (date(2025, 12, 1), date(2032, 12, 1), 2.5, 2.27003, 6.397353),
        # BTP 1,35% Ap30, low coupon bought below par
        (date(2026, 10, 29), date(2030, 4, 1), 1.35, 3.1, 3.298884),
    ],
    ids=["btp-lug29-mid-period", "btp-dc32-coupon-date", "btp-ap30-low-coupon"],
)
def test_modified_duration_of_real_btps(
    settlement: date, maturity: date, nominal_rate: float, yield_pct: float, expected: float
) -> None:
    assert modified_duration(settlement, maturity, nominal_rate, yield_pct, 2) == pytest.approx(expected, abs=_ABS)


def test_par_bond_on_coupon_date_matches_closed_form() -> None:
    # At par on a coupon date: modified duration = (1 − (1 + y/2)^−n) / y
    expected = (1 - 1.04**-20) / 0.08
    assert modified_duration(date(2026, 1, 1), date(2036, 1, 1), 8.0, 8.0, 2) == pytest.approx(expected, abs=1e-9)


def test_modified_is_macaulay_over_one_plus_periodic_yield() -> None:
    args = (date(2026, 10, 29), date(2029, 7, 1), 3.35, 3.004, 2)
    assert modified_duration(*args) == pytest.approx(macaulay_duration(*args) / (1 + 0.03004 / 2))


def test_last_period_duration_is_time_to_maturity() -> None:
    # One flow left: the Macaulay duration is the time to it (90 days of 30/360 = 0.25 years)
    assert macaulay_duration(date(2029, 4, 1), date(2029, 7, 1), 3.35, 3.0, 2) == pytest.approx(0.25)


def test_annual_coupon_bond() -> None:
    # Annual coupon at par on a coupon date: (1 − 1.05^−5) / 0.05
    expected = (1 - 1.05**-5) / 0.05
    assert modified_duration(date(2026, 3, 1), date(2031, 3, 1), 5.0, 5.0, 1) == pytest.approx(expected, abs=1e-9)


def test_convention_changes_the_period_fraction() -> None:
    # Same bond, act/act instead of 30/360: only the fraction of the first period changes
    thirty = modified_duration(date(2026, 10, 29), date(2029, 7, 1), 3.35, 3.004, 2)
    act_act = modified_duration(date(2026, 10, 29), date(2029, 7, 1), 3.35, 3.004, 2, DayCountConvention.ACT_ACT)
    assert act_act == pytest.approx(thirty, abs=0.01)
    assert act_act != thirty


@pytest.mark.parametrize(
    "settlement,coupon_frequency",
    [
        (date(2026, 1, 1), 0),  # no coupons (BOT)
        (date(2029, 7, 1), 2),  # settlement on maturity
        (date(2029, 8, 1), 2),  # settlement after maturity
    ],
)
def test_invalid_inputs_raise(settlement: date, coupon_frequency: int) -> None:
    with pytest.raises(ValueError):
        modified_duration(settlement, date(2029, 7, 1), 3.35, 3.0, coupon_frequency)
