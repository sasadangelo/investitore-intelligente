# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
"""
Unit tests for the day-count conventions in utils/day_count.py.

Covers:
  - DayCountConvention: YEARFRAC mapping, year fraction, accrual share, accrued coupon
  - BOND_CONVENTIONS / conventions_for: the conventions of BOTs and BTPs
  - the calculator really reads the conventions table (changing it changes the result)
"""
from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from intelligent_investor.dtos.bond import BondDTO
from intelligent_investor.dtos.bond_transaction import BondTransactionDTO
from intelligent_investor.services.bond_calculator_service import BondCalculatorService
from intelligent_investor.utils import day_count
from intelligent_investor.utils.day_count import DayCountConvention, YearfracBasis, conventions_for, yearfrac

# ------------------------------------------------------------------
# DayCountConvention
# ------------------------------------------------------------------


def test_values_are_the_spreadsheet_labels() -> None:
    assert [c.value for c in DayCountConvention] == ["act/act", "act/360", "act/365", "30/360"]


@pytest.mark.parametrize(
    "convention, basis",
    [
        (DayCountConvention.ACT_ACT, YearfracBasis.ACT_ACT),
        (DayCountConvention.ACT_360, YearfracBasis.ACT_360),
        (DayCountConvention.ACT_365, YearfracBasis.ACT_365),
        (DayCountConvention.THIRTY_360, YearfracBasis.US_30_360),
    ],
)
def test_year_fraction_is_yearfrac_with_the_mapped_basis(convention: DayCountConvention, basis: YearfracBasis) -> None:
    d1, d2 = date(2025, 1, 31), date(2026, 3, 15)
    assert convention.yearfrac_basis is basis
    assert convention.year_fraction(d1, d2) == yearfrac(d1, d2, basis)


@pytest.mark.parametrize("convention", [DayCountConvention.ACT_360, DayCountConvention.ACT_365])
def test_accrual_fraction_with_fixed_year_is_the_exact_ratio_of_days(convention: DayCountConvention) -> None:
    start, d, end = date(2025, 1, 1), date(2025, 4, 2), date(2025, 7, 2)  # 91 of 182 days
    assert convention.accrual_fraction(start, d, end) == Decimal("0.5")


def test_accrual_fraction_act_act_is_the_ratio_of_year_fractions() -> None:
    start, d, end = date(2022, 5, 3), date(2025, 12, 1), date(2032, 12, 1)
    expected = yearfrac(start, d) / yearfrac(start, end)
    assert float(DayCountConvention.ACT_ACT.accrual_fraction(start, d, end)) == pytest.approx(expected)


def test_accrued_coupon_act_act_is_icma_floored_to_six_decimals() -> None:
    # 3.6% semi-annual: 1.8 × 90 days / 181 days of the period = 0.8950276... → 0.895027
    accrued = DayCountConvention.ACT_ACT.accrued_coupon(
        nominal_rate=3.6,
        coupon_frequency=2,
        period_start=date(2025, 1, 15),
        period_end=date(2025, 7, 15),
        accrual_start=date(2025, 1, 15),
        settlement_date=date(2025, 4, 15),
    )
    assert accrued == 0.895027


def test_accrued_coupon_other_conventions_use_the_year_fraction() -> None:
    # Spreadsheet F36 when F21 ≠ act/act: YEARFRAC(accrual start; settlement; basis) × rate
    accrued = DayCountConvention.ACT_365.accrued_coupon(
        nominal_rate=3.6,
        coupon_frequency=2,
        period_start=date(2025, 1, 15),
        period_end=date(2025, 7, 15),
        accrual_start=date(2025, 1, 15),
        settlement_date=date(2025, 4, 15),
    )
    assert accrued == pytest.approx(90 / 365 * 3.6)


# ------------------------------------------------------------------
# Conventions per bond type
# ------------------------------------------------------------------


def test_bot_conventions() -> None:
    bot = conventions_for("BOT")
    assert bot.issue_discount is DayCountConvention.ACT_365  # ratio of actual days
    assert bot.simple_yield is DayCountConvention.ACT_ACT
    assert bot.compound_yield is DayCountConvention.ACT_365  # XIRR: days / 365


def test_btp_conventions() -> None:
    btp = conventions_for("BTP")
    assert btp.accrued_interest is DayCountConvention.ACT_ACT
    assert btp.issue_discount is DayCountConvention.ACT_ACT
    assert btp.simple_yield is DayCountConvention.ACT_ACT
    assert btp.compound_yield is DayCountConvention.ACT_365


def test_unsupported_bond_type_is_rejected() -> None:
    with pytest.raises(ValueError, match="CORPORATE"):
        conventions_for("CORPORATE")


# ------------------------------------------------------------------
# The calculator reads the table
# ------------------------------------------------------------------


def test_calculator_uses_the_configured_accrued_interest_convention(monkeypatch: pytest.MonkeyPatch) -> None:
    bond = BondDTO(
        name="BTP TF 2032",
        isin="IT0005494239",
        bond_type="BTP",
        issue_date=date(2022, 5, 3),
        maturity_date=date(2032, 12, 1),
        issue_price=97.66,
        nominal_rate=2.5,
        coupon_frequency=2,
    )
    tx = BondTransactionDTO(
        bond_id=0, purchase_venue="mot", purchase_date=date(2026, 2, 16), purchase_price=97.0, face_value=10000.0
    )
    act_act = BondCalculatorService().calculate(tx, bond).purchase.accrued_interest

    act_365 = replace(day_count.BOND_CONVENTIONS["BTP"], accrued_interest=DayCountConvention.ACT_365)
    monkeypatch.setitem(day_count.BOND_CONVENTIONS, "BTP", act_365)
    configured = BondCalculatorService().calculate(tx, bond).purchase.accrued_interest

    assert act_act == pytest.approx(1.25 * 77 / 182, abs=1e-6)  # ICMA: 77 of 182 days of the period
    assert configured == pytest.approx(77 / 365 * 2.5)  # act/365: year fraction × annual rate
