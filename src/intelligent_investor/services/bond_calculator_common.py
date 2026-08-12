# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
"""
Calculation helpers shared by BOT and BTP calculators: commission clamping and
stamp duty. Both formulas are identical between instruments (only the base
amount they're applied to differs), so they live here instead of being
duplicated. bot_calculator_service.py keeps its own private copy rather than
importing from here: it's already tested and in production, and the roadmap
(docs/roadmap-btp.md, Fase 4) asks not to touch it while the BTP calculator is
still unproven.
"""
from datetime import date
from typing import Literal

from intelligent_investor.dtos.bot_calculation_result import StampDutyResultDTO

STAMP_DUTY_RATE: float = 0.002  # 0.20% per year


def calc_commission(
    base: float,
    pct: float,
    min_fee: float,
    max_fee: float | None,
) -> float:
    """
    Apply a percentage commission on base, clamped to [min_fee, max_fee].
    max_fee=None means no upper cap (INF).
    """
    raw: float = base * (pct / 100)
    clamped: float = max(raw, min_fee)
    if max_fee is not None:
        clamped = min(clamped, max_fee)
    return clamped


def calc_stamp_duty(
    duty_base_amount: float,
    face_value: float,
    purchase_date: date,
    sale_date: date,
    stamp_duty_period: Literal["annual", "quarterly"],
) -> StampDutyResultDTO:
    """
    Estimate the 0.20%/year stamp duty on a bond holding.

    duty_base_amount: purchase-side amount before commissions (dry_amount for
    a BOT, dirty_amount for a BTP) — averaged with face_value, mirroring the
    reference spreadsheet: (C25 + C20) / 2.
    """
    duty_base: float = (duty_base_amount + face_value) / 2

    if stamp_duty_period == "annual":
        periods: int = (sale_date.year - purchase_date.year) * 12 + (sale_date.month - purchase_date.month)
        estimated_duty: float = duty_base * STAMP_DUTY_RATE * periods / 12
    else:  # quarterly
        # Count calendar quarter boundaries crossed, mirroring Excel B33:
        # QUOTIENT(MONTH(purchase)-1 + months_held, 3) - QUOTIENT(MONTH(purchase)-1, 3)
        months_held: int = (sale_date.year - purchase_date.year) * 12 + (sale_date.month - purchase_date.month)
        periods = (purchase_date.month - 1 + months_held) // 3 - (purchase_date.month - 1) // 3
        estimated_duty = duty_base * STAMP_DUTY_RATE * periods / 4

    return StampDutyResultDTO(
        holding_periods=max(0, periods),
        estimated_duty=max(0.0, estimated_duty),
    )
