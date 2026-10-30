# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
"""
Indicative gross/net yields for bonds quoted on the MOT, and the modified
duration shown on the bond detail page.

Shared by the bond catalogue and the bond detail page. Yields are computed per
100 of nominal; commissions and stamp duty are not modelled (unknown at
catalogue level). BTP yields come from BondCalculatorService, so the catalogue
and the calculator page agree.
"""
from datetime import date

from intelligent_investor.dtos import BondDTO
from intelligent_investor.dtos.bond_transaction import BondTransactionDTO
from intelligent_investor.services.bond_calculator_service import BondCalculatorService, calc_modified_duration
from intelligent_investor.utils.day_count import conventions_for
from intelligent_investor.utils.yield_calculator import YieldCalculator

_calculator = BondCalculatorService()


def bot_yields(bond: BondDTO, last_price: float, today: date) -> tuple[float | None, float | None]:
    """
    Compute gross and net annualised compound yield for a zero-coupon BOT.

    Uses YieldCalculator in the BOT conventions (utils/day_count.py), qty=1:
        gross = compound(redemption_price, last_price)
        net   = compound(redemption_price - imposta_disaggio, last_price)
    where imposta_disaggio is the tax on the discount still to accrue until maturity.

    Args:
        bond: The BOT to evaluate
        last_price: Last MOT price per 100 of nominal
        today: Valuation date

    Returns:
        (gross_pct, net_pct) as percentage values, or (None, None) if the data is insufficient
    """
    if bond.maturity_date <= today or bond.maturity_date <= bond.issue_date or last_price <= 0:
        return None, None

    conventions = conventions_for(bond.bond_type)
    residual = 1 - float(conventions.issue_discount.accrual_fraction(bond.issue_date, today, bond.maturity_date))
    disaggio_lordo = (bond.redemption_price - bond.issue_price) * residual
    imposta_disaggio = disaggio_lordo * (bond.tax_rate / 100)

    yc = YieldCalculator(
        today,
        bond.maturity_date,
        simple_convention=conventions.simple_yield,
        compound_convention=conventions.compound_yield,
    )
    gross = yc.compound(bond.redemption_price, last_price)
    net = yc.compound(bond.redemption_price - imposta_disaggio, last_price)

    return gross, net


def btp_yields(bond: BondDTO, last_price: float, today: date) -> tuple[float | None, float | None]:
    """
    Compute an indicative gross/net yield-to-maturity for a fixed-rate BTP.

    Runs the bond calculator on a purchase of 100 of nominal today at last_price,
    held to maturity, with no commissions: gross and net figures therefore include
    the coupons, the accrued interest paid today, the tax on the issue discount and
    the capital gain tax exactly as the calculator page computes them. Stamp duty is
    left out (it depends on the holding, not on the bond).

    Args:
        bond: The BTP to evaluate
        last_price: Last MOT clean price per 100 of nominal
        today: Valuation date

    Returns:
        (gross_pct, net_pct) as percentage values (compound, annualised), or
        (None, None) if the bond has already matured or the quote is invalid
    """
    if bond.maturity_date <= today or last_price <= 0:
        return None, None

    transaction = BondTransactionDTO(
        bond_id=bond.id or 0,
        purchase_venue="mot",
        purchase_date=today,
        purchase_price=last_price,
        face_value=100.0,
    )
    try:
        summary = _calculator.calculate(transaction, bond).summary
    except ValueError:  # e.g. XIRR not converging on a nonsensical quote
        return None, None
    return summary.compound_gross_yield, summary.compound_net_yield_before_duty


def bond_yields(bond: BondDTO, last_price: float, today: date) -> tuple[float | None, float | None]:
    """
    Dispatch to the yield formula matching the bond's type.

    Args:
        bond: The bond to evaluate
        last_price: Last MOT price per 100 of nominal
        today: Valuation date

    Returns:
        (gross_pct, net_pct) as percentage values, or (None, None) if not computable
    """
    if bond.bond_type == "BTP":
        return btp_yields(bond=bond, last_price=last_price, today=today)
    return bot_yields(bond=bond, last_price=last_price, today=today)


def bond_modified_duration(bond: BondDTO, net_yield: float | None, today: date) -> float | None:
    """
    Modified duration of a bond bought today and held to maturity, at its indicative net yield.

    Same rule as the calculator (cell K16): None for a bond without coupons (BOT), with
    less than 365 days to maturity or without a positive yield. The indicative net yield
    leaves stamp duty out, unlike K4: the difference on the duration is negligible.

    Args:
        bond: The bond to evaluate
        net_yield: Its indicative net yield in %, None when not computable (no quote)
        today: Valuation date

    Returns:
        The modified duration, or None when not computable
    """
    if net_yield is None or bond.maturity_date <= today:
        return None
    return calc_modified_duration(bond, today, bond.maturity_date, net_yield)


def bond_yields_with_costs(
    bond: BondDTO, last_price: float, today: date, transaction: BondTransactionDTO
) -> tuple[float | None, float | None, float | None]:
    """
    Gross/net yield and net gain of a real purchase: today at last_price, held to maturity.

    Unlike bond_yields, BOTs and BTPs both go through the bond calculator, with the lot,
    commissions and zainetto of *transaction*: the net yield is the calculator's final one
    (commissions, taxes and stamp duty included).

    Args:
        bond: The bond to evaluate
        last_price: Last MOT clean price per 100 of nominal
        today: Valuation date, used as purchase date
        transaction: Lot, commissions and portfolio losses; venue, dates and price are overridden

    Returns:
        (gross_pct, net_pct, net_gain_eur), or (None, None, None) if not computable
    """
    if bond.maturity_date <= today or last_price <= 0:
        return None, None, None
    tx = transaction.model_copy(
        update={
            "bond_id": bond.id or 0,
            "purchase_venue": "mot",
            "purchase_date": today,
            "purchase_price": last_price,
            "sale_date": None,
            "sale_price": None,
        }
    )
    try:
        summary = _calculator.calculate(tx, bond).summary
    except ValueError:  # e.g. XIRR not converging on a nonsensical quote
        return None, None, None
    return summary.compound_gross_yield, summary.compound_net_yield, summary.net_gain
