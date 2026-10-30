# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
"""
Result of the bond calculator, shared by BOTs and fixed-rate BTPs.

A BOT is the no-coupon case of a BTP: its coupon plan is empty and its accrued
interest (rateo) is always 0, so clean and dirty amounts coincide. Amounts are
in Euro for the whole lot; prices are per 100 of nominal.

Sign convention for discount_tax (imposta sul disaggio) and accrued_interest_tax
(imposta sul rateo), mirroring the reference spreadsheet (foglio `Bond`, cells
K27/K28 and K39/K40): they are added to total_paid on the purchase leg and to
total_received on the sale leg, so
  - discount_tax, BOT: positive on both legs (paid upfront at purchase on the
    discount still to accrue, reimbursed at sale for the part after the sale date);
  - discount_tax, coupon bond: negative on both legs (credit at purchase for the
    discount already accrued, withheld at sale/maturity on the discount accrued so far);
  - accrued_interest_tax: negative on both legs (credit at purchase on the rateo paid
    to the seller, since the next coupon is taxed in full; withheld at an early sale
    on the rateo cashed from the buyer). Always 0.0 for a BOT.
"""
from pydantic import BaseModel

from intelligent_investor.utils.coupon_schedule import CouponPayment

__all__ = [
    "PurchaseResultDTO",
    "SaleResultDTO",
    "CapitalGainResultDTO",
    "StampDutyResultDTO",
    "SummaryResultDTO",
    "BondCalculationResultDTO",
]


class PurchaseResultDTO(BaseModel):
    """Computed amounts for the purchase leg."""

    # corso secco, per 100 of nominal
    clean_price: float
    # rateo cedolare owed to the seller, per 100 of nominal (0.0 for a BOT)
    accrued_interest: float
    # prezzo tel quel = clean_price + accrued_interest
    dirty_price: float
    # dry_amount = clean_price × quantity (importo secco)
    dry_amount: float
    # dirty_amount = dirty_price × quantity (equal to dry_amount for a BOT)
    dirty_amount: float
    # commission on face value (asta) or on dry_amount (mot), clamped to [min, max]
    commission: float
    fixed_commission: float
    # discount (disaggio) per 100 of nominal the withholding of this leg is based on:
    #   BOT: discount still to accrue from purchase to maturity
    #   coupon bond: discount already accrued from the fiscal issue date to purchase
    unit_discount: float
    # imposta sul disaggio, signed (see module docstring): + paid (BOT), − credit (coupon bond)
    discount_tax: float
    # 12.5% credit on the rateo paid to the seller, signed: always ≤ 0
    accrued_interest_tax: float
    # total outflow: dirty_amount + commission + fixed_commission + discount_tax + accrued_interest_tax
    total_paid: float


class SaleResultDTO(BaseModel):
    """Computed amounts for the sale leg (or maturity redemption)."""

    # corso secco at sale, or redemption price at maturity
    clean_price: float
    # rateo cedolare owed by the buyer at an early sale (0.0 at maturity and for a BOT)
    accrued_interest: float
    dirty_price: float
    dry_amount: float
    dirty_amount: float
    # commission on dry_amount, clamped to [min, max]; 0.0 at maturity, where nothing is sold
    commission: float
    fixed_commission: float
    # discount per 100 of nominal the withholding of this leg is based on:
    #   BOT: discount still to accrue from sale to maturity (0.0 at maturity)
    #   coupon bond: discount accrued up to the sale (the whole discount at maturity)
    unit_discount: float
    # imposta sul disaggio, signed: + reimbursed by the buyer (BOT), − withheld (coupon bond)
    discount_tax: float
    # 12.5% withheld on the rateo cashed from the buyer at an early sale, signed: always ≤ 0
    accrued_interest_tax: float
    # total inflow: dirty_amount - commission - fixed_commission + discount_tax + accrued_interest_tax
    #               - capital_gain_tax
    total_received: float


class CapitalGainResultDTO(BaseModel):
    """
    Capital gain section.

    The theoretical price is the issue price plus the discount accrued so far: the
    part of the price gap explained by the discount is taxed as discount
    (discount_tax), only the rest is a capital gain or loss.

    Sequence:
      1. unit_gain_loss   = unload_price - load_price        (per 100 of nominal)
      2. total_gain_loss  = unit_gain_loss × quantity        (Plus/Minus Realizzata in €)
      3. tds_reduction    = total_gain_loss × 48.08%         (Riduzione Imponibile per TdS)
      4. capital_gain_tax = max(0, tds_reduction − portfolio_losses) / 48.08% × 12.5%  (if gain)
                            — trattenuta dal sostituto al rimborso, after offsetting the zainetto
      5. remaining_loss   = zainetto residuo (if gain) or minus da aggiungere allo zainetto (if loss)

    48.08% is tax_rate / 26% (cell C10): a government-bond gain counts for 48.08% of
    its amount when offset against the zainetto (cells K49–K53).
    """

    theoretical_purchase_price: float
    theoretical_sale_price: float
    # clean purchase price + commissions per unit − discount accrued at purchase
    load_price: float
    # clean sale price − commissions per unit − discount accrued at sale
    unload_price: float
    unit_gain_loss: float
    total_gain_loss: float
    tds_reduction: float
    capital_gain_tax: float
    # zainetto residuo (if gain) or minus to add to the zainetto (if loss)
    remaining_loss: float


class StampDutyResultDTO(BaseModel):
    """Estimated stamp duty (imposta di bollo) for the holding period."""

    # number of periods (quarters or months) the bond is held
    holding_periods: int
    # 0.20%/year on the average between dry purchase amount and face value
    estimated_duty: float


class SummaryResultDTO(BaseModel):
    """
    Final gains and yields.

    gross_gain              = inflows - outflow, without commissions, taxes or stamp duty
                              (coupons + sale/redemption dirty amount - purchase dirty amount)
    net_gain_before_duty    = net coupons - coupon fees + total_received - total_paid
    net_gain                = net_gain_before_duty - estimated_duty

    Yields (start=purchase_date, end=sale_date):
        simple   = gain / capital / YEARFRAC(basis=ACT_ACT)
        compound = (proceeds / capital) ^ (365/days) - 1 when no coupon is cashed
                   (2-flow closed form), xirr() on the dated cash flows otherwise
                   — the two coincide when there are no coupons (days/365 convention).
                   In the net yield after stamp duty the duty is spread over the calendar
                   years held, as column R of the sheet (see spread_stamp_duty).
    """

    gross_gain: float
    net_gain_before_duty: float
    net_gain: float

    simple_gross_yield: float               # % lordo
    compound_gross_yield: float             # % lordo annualised
    simple_net_yield_before_duty: float     # % netto pre-bollo
    compound_net_yield_before_duty: float   # % netto pre-bollo annualised
    simple_net_yield: float                 # % netto
    compound_net_yield: float               # % netto annualised

    # Modified duration at purchase, on the flows to maturity discounted at compound_net_yield
    # (cell K16). None for a bond without coupons, a holding shorter than 365 days or a
    # non-positive yield, where the sheet leaves the cell blank.
    modified_duration: float | None


class BondCalculationResultDTO(BaseModel):
    """
    Full result of the bond calculator.

    capital_gain is None only for a BOT bought at auction: its purchase price is the
    theoretical price by construction, so no capital gain can arise.
    """

    quantity: float
    purchase: PurchaseResultDTO
    # coupons cashed by this holder: paid after purchase and on or before sale/maturity
    coupon_plan: list[CouponPayment]
    # fixed fee in € the bank charges at each of those coupons (cell K44), already
    # deducted from the net gain and the net yields
    coupon_fee: float = 0.0
    sale: SaleResultDTO
    capital_gain: CapitalGainResultDTO | None
    stamp_duty: StampDutyResultDTO
    summary: SummaryResultDTO
