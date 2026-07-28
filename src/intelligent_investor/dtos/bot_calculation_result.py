# -----------------------------------------------------------------------------
# Copyright (c) 2025 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
from pydantic import BaseModel


class PurchaseResultDTO(BaseModel):
    """Computed amounts for the BOT purchase leg."""

    # dry_amount = purchase_price × quantity
    dry_amount: float
    # commission applied on face value (asta) or on dry_amount (mot),
    # clamped between buy_commission_min and buy_commission_max
    commission: float
    fixed_commission: float
    # discount accrued to the buyer per single BOT unit
    # = (100 - purchase_price) × (maturity_date - purchase_date) / total_days
    unit_discount: float
    # withholding tax on discount paid upfront by law: tax_rate% × unit_discount × quantity
    discount_tax: float
    # total outflow: dry_amount + commission + fixed_commission + discount_tax
    total_paid: float


class SaleResultDTO(BaseModel):
    """Computed amounts for the sale leg (or maturity redemption)."""

    # dry_amount = sale_price × quantity
    dry_amount: float
    # commission applied on dry_amount, clamped between sell_commission_min and sell_commission_max
    commission: float
    fixed_commission: float
    # discount accrued from sale date to maturity per single BOT unit
    # = (100 - purchase_price) × (maturity_date - sale_date) / total_days
    # (0.0 when held to maturity)
    unit_discount: float
    # discount tax reimbursed by the future buyer: tax_rate% × unit_discount × quantity
    # (0.0 when held to maturity)
    discount_tax: float
    # total inflow: dry_amount - commission - fixed_commission + discount_tax
    total_received: float


class CapitalGainResultDTO(BaseModel):
    """
    Capital gain section — populated only for MOT purchases.

    The theoretical price is the point on the straight line between
    (issue_date, issue_price) and (maturity_date, 100).
    If load_price < theoretical_purchase_price a capital gain arises and is
    taxed at 26% on the taxable base (reduced by 48.08% for government bonds).

    unit_gain_loss > 0  → capital gain  (taxed)
    unit_gain_loss < 0  → capital loss  (enters the fiscal backpack)
    remaining_loss      → portion of capital loss not offset by portfolio_losses
    """

    theoretical_purchase_price: float
    theoretical_sale_price: float
    # load_price  = purchase_price + purchase_commissions / quantity
    load_price: float
    # unload_price = sale_price - sale_commissions / quantity
    unload_price: float
    # gain/loss per single BOT unit: unload_price - load_price
    unit_gain_loss: float
    # taxable base: unit_gain_loss × quantity × (1 - 0.4808)  — 0 if unit_gain_loss <= 0
    taxable_base: float
    # capital gain tax: 26% × taxable_base  — 0 if unit_gain_loss <= 0
    capital_gain_tax: float
    # capital loss not offset by the portfolio_losses provided by the user — 0 if gain
    remaining_loss: float


class StampDutyResultDTO(BaseModel):
    """
    Stamp duty estimate (0.20% per year on the investment value).

    holding_periods = months (annual frequency) or quarters (quarterly frequency)
                      between purchase_date and sale_date (or maturity_date)
    estimated_duty  = 0.20% × total_paid × holding_periods / 12  (annual)
                      or × holding_periods / 4                    (quarterly)
    """

    holding_periods: int
    estimated_duty: float


class SummaryResultDTO(BaseModel):
    """
    Final gains and yields.

    gross_gain              = total_received - total_paid
                              (before capital gain tax and stamp duty)
    net_gain_before_duty    = gross_gain - capital_gain_tax
    net_gain                = net_gain_before_duty - estimated_duty
    effective_total_received = total_received - capital_gain_tax

    Simple yields are computed on total_paid.
    Compound yields are annualised:
        (final / initial) ^ (365 / holding_days) - 1
    """

    gross_gain: float
    net_gain_before_duty: float
    net_gain: float
    effective_total_received: float

    simple_gross_yield: float       # %
    simple_net_yield: float         # %
    compound_gross_yield: float     # % annualised
    compound_net_yield: float       # % annualised


class BotCalculationResultDTO(BaseModel):
    """
    Full result of the BOT calculator.

    capital_gain is None when purchase_venue == 'asta': at auction the
    purchase price equals the theoretical price so no capital gain can arise.
    """

    quantity: float
    purchase: PurchaseResultDTO
    sale: SaleResultDTO
    capital_gain: CapitalGainResultDTO | None   # None when venue == "asta"
    stamp_duty: StampDutyResultDTO
    summary: SummaryResultDTO
