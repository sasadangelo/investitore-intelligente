# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
"""
Indicative gross/net yields for bonds quoted on the MOT.

Shared by the bond catalogue and the bond detail page. Yields are computed per
100 of nominal; commissions and stamp duty are not modelled (unknown at
catalogue level). BTP yields come from BondCalculatorService, so the catalogue
and the calculator page agree.
"""
from datetime import date

from intelligent_investor.dtos import BondDTO
from intelligent_investor.dtos.bond_transaction import BondTransactionDTO
from intelligent_investor.services.bond_calculator_service import BondCalculatorService
from intelligent_investor.utils.yield_calculator import YieldCalculator

_calculator = BondCalculatorService()


def bot_yields(bond: BondDTO, last_price: float, today: date) -> tuple[float | None, float | None]:
    """
    Compute gross and net annualised compound yield for a zero-coupon BOT.

    Uses YieldCalculator with ACT_ACT (YEARFRAC basis 1), qty=1:
        gross = compound(redemption_price, last_price)
        net   = compound(redemption_price - imposta_disaggio, last_price)

    Args:
        bond: The BOT to evaluate
        last_price: Last MOT price per 100 of nominal
        today: Valuation date

    Returns:
        (gross_pct, net_pct) as percentage values, or (None, None) if the data is insufficient
    """
    total_days = (bond.maturity_date - bond.issue_date).days
    residual_days = (bond.maturity_date - today).days

    if residual_days <= 0 or total_days <= 0 or last_price <= 0:
        return None, None

    disaggio_lordo = (bond.redemption_price - bond.issue_price) * residual_days / total_days
    imposta_disaggio = disaggio_lordo * (bond.tax_rate / 100)

    yc = YieldCalculator(today, bond.maturity_date)
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
