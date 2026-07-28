# -----------------------------------------------------------------------------
# Copyright (c) 2025 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
from datetime import date

from intelligent_investor.dtos.bond import BondDTO
from intelligent_investor.dtos.bot_calculation_result import (
    BotCalculationResultDTO,
    CapitalGainResultDTO,
    PurchaseResultDTO,
    SaleResultDTO,
    StampDutyResultDTO,
    SummaryResultDTO,
)
from intelligent_investor.dtos.bot_transaction import BotTransactionDTO

# Reduction factor applied to the capital gain taxable base for government bonds
# (TdS): 12.5% tax / 26% standard rate = 0.4808 reduction → effective rate = 12.5%
_TDS_REDUCTION: float = 0.4808
_CAPITAL_GAIN_RATE: float = 0.26
_STAMP_DUTY_RATE: float = 0.002  # 0.20% per year


class BotCalculatorService:
    """
    Stateless service that computes the full BOT purchase/sale result.

    Usage:
        result = BotCalculatorService().calculate(transaction, bond)
    """

    def calculate(
        self,
        transaction: BotTransactionDTO,
        bond: BondDTO,
    ) -> BotCalculationResultDTO:
        """
        Compute all purchase, sale, capital-gain, stamp-duty and summary
        figures for the given transaction and bond.

        Args:
            transaction: user-supplied transaction parameters.
            bond:        the bond being traded (provides dates, prices, tax_rate).

        Returns:
            A fully populated BotCalculationResultDTO.
        """
        quantity: float = transaction.quantity
        total_days: int = (bond.maturity_date - bond.issue_date).days

        # Effective sale date and price (maturity when no early sale)
        sale_date: date = transaction.sale_date or bond.maturity_date
        sale_price: float = transaction.sale_price or bond.redemption_price

        purchase: PurchaseResultDTO = self._calc_purchase(
            tx=transaction, bond=bond, total_days=total_days, quantity=quantity
        )
        sale: SaleResultDTO = self._calc_sale(transaction, bond, total_days, quantity, sale_date, sale_price)
        capital_gain: CapitalGainResultDTO | None = self._calc_capital_gain(
            tx=transaction,
            bond=bond,
            total_days=total_days,
            quantity=quantity,
            sale_date=sale_date,
            sale_price=sale_price,
            purchase=purchase,
            sale=sale,
        )
        stamp_duty: StampDutyResultDTO = self._calc_stamp_duty(transaction, sale_date, purchase)
        summary: SummaryResultDTO = self._calc_summary(
            purchase=purchase,
            sale=sale,
            capital_gain=capital_gain,
            stamp_duty=stamp_duty,
            purchase_date=transaction.purchase_date,
            sale_date=sale_date,
        )

        return BotCalculationResultDTO(
            quantity=quantity,
            purchase=purchase,
            sale=sale,
            capital_gain=capital_gain,
            stamp_duty=stamp_duty,
            summary=summary,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _calc_purchase(
        self,
        tx: BotTransactionDTO,
        bond: BondDTO,
        total_days: int,
        quantity: float,
    ) -> PurchaseResultDTO:
        days_held_at_purchase: int = (bond.maturity_date - tx.purchase_date).days
        unit_discount: float = (bond.redemption_price - bond.issue_price) * days_held_at_purchase / total_days
        discount_tax: float = unit_discount * (bond.tax_rate / 100) * quantity

        dry_amount: float = tx.purchase_price * quantity
        commission: float = _calc_commission(
            base=tx.face_value if tx.purchase_venue == "asta" else dry_amount,
            pct=tx.buy_commission_pct,
            min_fee=tx.buy_commission_min,
            max_fee=tx.buy_commission_max,
        )
        fixed_commission = tx.buy_commission_fixed
        total_paid = dry_amount + commission + fixed_commission + discount_tax

        return PurchaseResultDTO(
            dry_amount=dry_amount,
            commission=commission,
            fixed_commission=fixed_commission,
            unit_discount=unit_discount,
            discount_tax=discount_tax,
            total_paid=total_paid,
        )

    def _calc_sale(
        self,
        tx: BotTransactionDTO,
        bond: BondDTO,
        total_days: int,
        quantity: float,
        sale_date: date,
        sale_price: float,
    ) -> SaleResultDTO:
        # Discount accrued from sale_date to maturity — reimbursed by the buyer
        # (0 when held to maturity: sale_date == maturity_date)
        days_remaining_at_sale: int = (bond.maturity_date - sale_date).days
        unit_discount: float = (bond.redemption_price - bond.issue_price) * days_remaining_at_sale / total_days
        discount_tax: float = unit_discount * (bond.tax_rate / 100) * quantity

        dry_amount: float = sale_price * quantity
        commission: float = _calc_commission(
            base=dry_amount,
            pct=tx.sell_commission_pct,
            min_fee=tx.sell_commission_min,
            max_fee=tx.sell_commission_max,
        )
        fixed_commission: float = tx.sell_commission_fixed
        total_received: float = dry_amount - commission - fixed_commission + discount_tax

        return SaleResultDTO(
            dry_amount=dry_amount,
            commission=commission,
            fixed_commission=fixed_commission,
            unit_discount=unit_discount,
            discount_tax=discount_tax,
            total_received=total_received,
        )

    def _calc_capital_gain(
        self,
        tx: BotTransactionDTO,
        bond: BondDTO,
        total_days: int,
        quantity: float,
        sale_date: date,
        sale_price: float,
        purchase: PurchaseResultDTO,
        sale: SaleResultDTO,
    ) -> CapitalGainResultDTO | None:
        # Capital gain only applies to MOT purchases
        if tx.purchase_venue == "asta":
            return None

        # Theoretical price: linear interpolation on the issue→maturity line
        days_from_issue_to_purchase: int = (tx.purchase_date - bond.issue_date).days
        days_from_issue_to_sale: int = (sale_date - bond.issue_date).days
        theoretical_purchase_price: float = (
            bond.issue_price + (bond.redemption_price - bond.issue_price) * days_from_issue_to_purchase / total_days
        )
        theoretical_sale_price: float = (
            bond.issue_price + (bond.redemption_price - bond.issue_price) * days_from_issue_to_sale / total_days
        )

        # Load/unload prices include commissions spread per unit
        load_price: float = tx.purchase_price + (purchase.commission + purchase.fixed_commission) / quantity
        unload_price: float = sale_price - (sale.commission + sale.fixed_commission) / quantity

        unit_gain_loss: float = unload_price - load_price

        if unit_gain_loss > 0:
            # Plus valenza: taxable base reduced by 48.08% for government bonds
            taxable_base: float = unit_gain_loss * quantity * (1 - _TDS_REDUCTION)
            # Offset against portfolio losses from fiscal backpack
            net_taxable: float = max(0.0, taxable_base - tx.portfolio_losses)
            capital_gain_tax: float = net_taxable * _CAPITAL_GAIN_RATE
            remaining_loss: float = 0.0
        else:
            taxable_base = 0.0
            capital_gain_tax = 0.0
            # Minus valenza available after consuming portfolio_losses
            remaining_loss = max(0.0, abs(unit_gain_loss) * quantity - tx.portfolio_losses)

        return CapitalGainResultDTO(
            theoretical_purchase_price=theoretical_purchase_price,
            theoretical_sale_price=theoretical_sale_price,
            load_price=load_price,
            unload_price=unload_price,
            unit_gain_loss=unit_gain_loss,
            taxable_base=taxable_base,
            capital_gain_tax=capital_gain_tax,
            remaining_loss=remaining_loss,
        )

    def _calc_stamp_duty(
        self,
        tx: BotTransactionDTO,
        sale_date: date,
        purchase: PurchaseResultDTO,
    ) -> StampDutyResultDTO:
        if tx.stamp_duty_period == "annual":
            periods: int = (sale_date.year - tx.purchase_date.year) * 12 + (sale_date.month - tx.purchase_date.month)
            estimated_duty: float = purchase.total_paid * _STAMP_DUTY_RATE * periods / 12
        else:  # quarterly
            start_quarter: int = (tx.purchase_date.month - 1) // 3
            end_quarter: int = (sale_date.month - 1) // 3 + (sale_date.year - tx.purchase_date.year) * 4
            periods = end_quarter - start_quarter
            estimated_duty = purchase.total_paid * _STAMP_DUTY_RATE * periods / 4

        return StampDutyResultDTO(
            holding_periods=max(0, periods),
            estimated_duty=max(0.0, estimated_duty),
        )

    def _calc_summary(
        self,
        purchase: PurchaseResultDTO,
        sale: SaleResultDTO,
        capital_gain: CapitalGainResultDTO | None,
        stamp_duty: StampDutyResultDTO,
        purchase_date: date,
        sale_date: date,
    ) -> SummaryResultDTO:
        capital_gain_tax: float = capital_gain.capital_gain_tax if capital_gain else 0.0

        gross_gain: float = sale.total_received - purchase.total_paid
        net_gain_before_duty: float = gross_gain - capital_gain_tax
        net_gain: float = net_gain_before_duty - stamp_duty.estimated_duty
        effective_total_received: float = sale.total_received - capital_gain_tax

        holding_days: int = (sale_date - purchase_date).days or 1

        simple_gross_yield: float = gross_gain / purchase.total_paid * 100
        simple_net_yield: float = net_gain / purchase.total_paid * 100
        compound_gross_yield = (effective_total_received / purchase.total_paid) ** (365 / holding_days) * 100 - 100
        compound_net_yield = ((effective_total_received - stamp_duty.estimated_duty) / purchase.total_paid) ** (
            365 / holding_days
        ) * 100 - 100

        return SummaryResultDTO(
            gross_gain=gross_gain,
            net_gain_before_duty=net_gain_before_duty,
            net_gain=net_gain,
            effective_total_received=effective_total_received,
            simple_gross_yield=simple_gross_yield,
            simple_net_yield=simple_net_yield,
            compound_gross_yield=compound_gross_yield,
            compound_net_yield=compound_net_yield,
        )


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------


def _calc_commission(
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
