# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
from pydantic import BaseModel

from intelligent_investor.dtos.bot_calculation_result import StampDutyResultDTO
from intelligent_investor.utils.coupon_schedule import CouponPayment

__all__ = [
    "StampDutyResultDTO",
    "BtpPurchaseResultDTO",
    "BtpSaleResultDTO",
    "BtpCapitalGainResultDTO",
    "BtpSummaryResultDTO",
    "BtpCalculationResultDTO",
]


class BtpPurchaseResultDTO(BaseModel):
    """
    Computed amounts for the BTP purchase leg.

    The buyer pays the seller the quoted clean price plus the coupon accrued
    since the last coupon date (rateo cedolare): this accrued amount is a
    straight transfer between the two private parties, not income, so no
    withholding tax applies to it.
    """

    # clean_price = quoted price per 100 of nominal (prezzo tel quel)
    clean_price: float
    # accrued_interest = gross rateo cedolare owed to the seller, per 100 of
    # nominal (0.0 when purchased exactly on a coupon date); untaxed
    accrued_interest: float
    # dirty_price = clean_price + accrued_interest (corso secco actually paid)
    dirty_price: float
    # dirty_amount = dirty_price × quantity
    dirty_amount: float
    # commission applied on face value (asta) or on dirty_amount (mot),
    # clamped between buy_commission_min and buy_commission_max
    commission: float
    fixed_commission: float
    # total outflow: dirty_amount + commission + fixed_commission
    total_paid: float


class BtpSaleResultDTO(BaseModel):
    """Computed amounts for the sale leg (or maturity redemption)."""

    # clean_price = quoted price per 100 of nominal at sale (redemption_price if held to maturity)
    clean_price: float
    # accrued_interest = gross rateo cedolare owed by the buyer to the seller, per 100 of
    # nominal (0.0 when held to maturity: the seller receives the full last coupon instead)
    accrued_interest: float
    # dirty_price = clean_price + accrued_interest
    dirty_price: float
    # dirty_amount = dirty_price × quantity
    dirty_amount: float
    # commission applied on dirty_amount, clamped between sell_commission_min and sell_commission_max
    # (0.0 when held to maturity — redemption has no commission)
    commission: float
    fixed_commission: float
    # total inflow: dirty_amount - commission - fixed_commission
    total_received: float


class BtpCapitalGainResultDTO(BaseModel):
    """
    Capital gain section.

    Unlike a BOT, a BTP's return already includes the coupon flows (taxed
    separately as they're paid, see coupon_plan on BtpCalculationResultDTO):
    the capital gain here is only the plus/minusvalenza on the clean-price
    difference between purchase and sale/redemption — the accrued interest
    portions are excluded since they're not a price movement.

    Same 48,08% TdS-reduction and "zainetto" (fiscal backpack) logic already
    implemented for BOTs in _calc_capital_gain, applied to this price gap
    instead of the BOT's discount (disaggio).
    """

    # load_price = clean price at purchase (prezzo di carico)
    load_price: float
    # unload_price = clean price at sale/redemption (prezzo di scarico)
    unload_price: float
    # gain/loss per single BTP unit: unload_price − load_price
    unit_gain_loss: float
    # total_gain_loss = unit_gain_loss × quantity  (Plus/Minus Realizzata in €)
    total_gain_loss: float
    # tds_reduction = total_gain_loss × 48.08%  (Riduzione Imponibile per TdS — solo informativa)
    tds_reduction: float
    # capital_gain_tax = total_gain_loss × 12.5%  (trattenuta dal sostituto al rimborso, 0 if minus)
    capital_gain_tax: float
    # remaining_loss:
    #   if gain → zainetto fiscale residuo dopo compensazione (€, in termini 26%-equiv)
    #   if loss → minus valenza da aggiungere allo zainetto   (€, in termini 26%-equiv)
    remaining_loss: float


class BtpSummaryResultDTO(BaseModel):
    """
    Final gains and yields, computed over the full multi-flow cashflow series
    (purchase outflow, net coupons, sale/redemption inflow) instead of the
    BOT's 2-point formula.

    gross_gain              = sum of all inflows (coupons + sale) - dirty_amount at purchase
    net_gain_before_duty    = gross_gain, net of coupon withholding and capital_gain_tax
    net_gain                = net_gain_before_duty - estimated_duty

    Yields are computed by YieldCalculator.xirr() on the dated cashflow series
    (purchase outflow, one entry per coupon, sale/redemption inflow):
        simple   = gain / capital / YEARFRAC(basis=ACT_ACT)
        compound = xirr(cashflows)  (days/365 convention, anchored to purchase_date)
    """

    gross_gain: float
    net_gain_before_duty: float
    net_gain: float

    simple_gross_yield: float               # % lordo
    compound_gross_yield: float             # % lordo annualised (XIRR)
    simple_net_yield_before_duty: float     # % netto pre-bollo
    compound_net_yield_before_duty: float   # % netto pre-bollo annualised (XIRR)
    simple_net_yield: float                 # % netto
    compound_net_yield: float               # % netto annualised (XIRR)


class BtpCalculationResultDTO(BaseModel):
    """Full result of the BTP calculator."""

    quantity: float
    purchase: BtpPurchaseResultDTO
    # coupon_plan = one entry per coupon date between purchase and sale/maturity
    coupon_plan: list[CouponPayment]
    sale: BtpSaleResultDTO
    capital_gain: BtpCapitalGainResultDTO
    stamp_duty: StampDutyResultDTO
    summary: BtpSummaryResultDTO
