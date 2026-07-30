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

    Sequence (mirrors the Excel calcolatore-bot.ods):
      1. unit_gain_loss      = unload_price - load_price          (per single BOT)
      2. total_gain_loss     = unit_gain_loss × quantity           (D34 in Excel)
      3. tds_reduction       = total_gain_loss × 48.08%           (C35 — TdS reduction)
      4. gross_tax           = total_gain_loss × 12.5%  (if >0)   (D33)
      5. net_taxable         = max(0, total_gain_loss - tds_reduction - portfolio_losses_equiv)
      6. capital_gain_tax    = net_taxable × 12.5%                (E37 scaled)
      7. remaining_loss      = zainetto residuo (if gain) or minus da aggiungere allo zainetto (if loss)
    """

    theoretical_purchase_price: float
    theoretical_sale_price: float
    # load_price  = (secco + comm + fisso) / qty − (prezzo_teorico_acquisto − prezzo_emissione)
    load_price: float
    # unload_price = (secco_vendita − comm − fisso) / qty − (prezzo_teorico_vendita − prezzo_emissione)
    unload_price: float
    # gain/loss per single BOT unit: unload_price − load_price
    unit_gain_loss: float
    # total_gain_loss = unit_gain_loss × quantity  (Plus/Minus Realizzata in €)
    total_gain_loss: float
    # tds_reduction = total_gain_loss × 48.08%  (Riduzione Imponibile per TdS)
    tds_reduction: float
    # gross_tax = total_gain_loss × 12.5%  (Imposta lorda, 0 if minus)
    gross_tax: float
    # net_taxable = imponibile netto dopo zainetto fiscale (0 if fully offset or if minus)
    net_taxable: float
    # capital_gain_tax = net_taxable × 12.5%  (Imposta netta sulla Plusvalenza)
    capital_gain_tax: float
    # remaining_loss:
    #   if gain → zainetto fiscale residuo dopo compensazione (€, in termini 26%-equiv)
    #   if loss → minus valenza da aggiungere allo zainetto   (€, in termini 26%-equiv)
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

    gross_gain              = dry_sale - dry_purchase  (no comm, no taxes)
    net_gain_before_duty    = total_received - total_paid - capital_gain_tax
    net_gain                = net_gain_before_duty - estimated_duty

    All yields use dry_purchase as base and actual/365 yearfrac (mirrors Excel).
    Three pairs (gross, net pre-bollo, net):
        simple   = gain / dry_purchase / yearfrac
        compound = (redemption / dry_purchase) ^ (1/yearfrac) - 1  (= XIRR)
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
