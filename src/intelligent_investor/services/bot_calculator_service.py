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

        # Load/unload prices: commissions spread per unit, minus the discount
        # accrued from issue date to purchase/sale date (that portion of the
        # disaggio was already "priced in" and is not a capital gain/loss).
        load_price: float = (
            tx.purchase_price
            + (purchase.commission + purchase.fixed_commission) / quantity
            - (theoretical_purchase_price - bond.issue_price)
        )
        unload_price: float = (
            sale_price
            - (sale.commission + sale.fixed_commission) / quantity
            - (theoretical_sale_price - bond.issue_price)
        )

        unit_gain_loss: float = unload_price - load_price
        tax_rate: float = bond.tax_rate / 100  # 0.125 for TdS

        # Step 1 — Plus/Minus Realizzata (D34 in Excel)
        total_gain_loss: float = unit_gain_loss * quantity

        # Step 2 — Riduzione Imponibile per TdS (C35)
        tds_reduction: float = total_gain_loss * _TDS_REDUCTION

        # Step 3 — Imposta lorda (D33): only when plus valenza
        gross_tax: float = total_gain_loss * tax_rate if total_gain_loss > 0 else 0.0

        if total_gain_loss > 0:
            # Imponibile netto = plus realizzata − riduzione TdS − zainetto già usato
            # Portfolio losses are at 26%-equivalent; scale to 12.5% to compare
            scaled_losses: float = tx.portfolio_losses * tax_rate / _CAPITAL_GAIN_RATE
            net_taxable: float = max(0.0, total_gain_loss - tds_reduction - scaled_losses)
            capital_gain_tax: float = net_taxable * tax_rate
            # Zainetto residuo: parte dello zainetto non consumata dalla plus (B36/D38)
            plus_after_tds: float = total_gain_loss - tds_reduction
            consumed: float = min(tx.portfolio_losses * tax_rate / _CAPITAL_GAIN_RATE, plus_after_tds)
            remaining_loss: float = max(0.0, tx.portfolio_losses - consumed * _CAPITAL_GAIN_RATE / tax_rate)
        else:
            net_taxable = 0.0
            capital_gain_tax = 0.0
            # Minus da aggiungere allo zainetto: abs(total) × 48.08% (C35 Excel quando minus)
            remaining_loss = abs(tds_reduction)

        return CapitalGainResultDTO(
            theoretical_purchase_price=theoretical_purchase_price,
            theoretical_sale_price=theoretical_sale_price,
            load_price=load_price,
            unload_price=unload_price,
            unit_gain_loss=unit_gain_loss,
            total_gain_loss=total_gain_loss,
            tds_reduction=tds_reduction,
            gross_tax=gross_tax,
            net_taxable=net_taxable,
            capital_gain_tax=capital_gain_tax,
            remaining_loss=remaining_loss,
        )

    def _calc_stamp_duty(
        self,
        tx: BotTransactionDTO,
        sale_date: date,
        purchase: PurchaseResultDTO,
    ) -> StampDutyResultDTO:
        # Base = average between purchase dry amount and face value (redemption)
        # mirrors Excel: (C25 + C20) / 2
        duty_base: float = (purchase.dry_amount + tx.face_value) / 2

        if tx.stamp_duty_period == "annual":
            periods: int = (sale_date.year - tx.purchase_date.year) * 12 + (sale_date.month - tx.purchase_date.month)
            estimated_duty: float = duty_base * _STAMP_DUTY_RATE * periods / 12
        else:  # quarterly
            # Count calendar quarter boundaries crossed, mirroring Excel B33:
            # QUOTIENT(MONTH(purchase)-1 + months_held, 3) - QUOTIENT(MONTH(purchase)-1, 3)
            months_held: int = (
                (sale_date.year - tx.purchase_date.year) * 12
                + (sale_date.month - tx.purchase_date.month)
            )
            periods = (
                (tx.purchase_date.month - 1 + months_held) // 3
                - (tx.purchase_date.month - 1) // 3
            )
            estimated_duty = duty_base * _STAMP_DUTY_RATE * periods / 4

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

        # Gross gain = pure cash flow without commissions, taxes or stamp duty
        # mirrors Excel C37 = SUM(J5:J6) = −dry_purchase + redemption_dry
        gross_gain: float = sale.dry_amount - purchase.dry_amount
        # Net gain before duty = total received − total paid − capital gain tax
        net_gain_before_duty: float = (sale.total_received - purchase.total_paid) - capital_gain_tax
        net_gain: float = net_gain_before_duty - stamp_duty.estimated_duty

        holding_days: int = (sale_date - purchase_date).days or 1
        year_frac: float = holding_days / 365
        dry_purchase: float = purchase.dry_amount
        total_paid: float = purchase.total_paid

        # Lordo: base = dry_purchase  (mirrors Excel C41 / XIRR J5:J6)
        simple_gross_yield: float = gross_gain / dry_purchase / year_frac * 100
        compound_gross_yield: float = (sale.dry_amount / dry_purchase) ** (1 / year_frac) * 100 - 100

        # Netto pre-bollo: base = total_paid  (mirrors Excel B42 / XIRR K5:K6)
        net_pre_redemption: float = sale.total_received - capital_gain_tax
        simple_net_yield_before_duty: float = net_gain_before_duty / total_paid / year_frac * 100
        compound_net_yield_before_duty: float = (net_pre_redemption / total_paid) ** (1 / year_frac) * 100 - 100

        # Netto: base = total_paid  (mirrors Excel B43 / XIRR L5:L6)
        net_redemption: float = net_pre_redemption - stamp_duty.estimated_duty
        simple_net_yield: float = net_gain / total_paid / year_frac * 100
        compound_net_yield: float = (net_redemption / total_paid) ** (1 / year_frac) * 100 - 100

        return SummaryResultDTO(
            gross_gain=gross_gain,
            net_gain_before_duty=net_gain_before_duty,
            net_gain=net_gain,
            simple_gross_yield=simple_gross_yield,
            compound_gross_yield=compound_gross_yield,
            simple_net_yield_before_duty=simple_net_yield_before_duty,
            compound_net_yield_before_duty=compound_net_yield_before_duty,
            simple_net_yield=simple_net_yield,
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
