# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
from datetime import date

from intelligent_investor.dtos.bond import BondDTO
from intelligent_investor.dtos.btp_calculation_result import (
    BtpCalculationResultDTO,
    BtpCapitalGainResultDTO,
    BtpPurchaseResultDTO,
    BtpSaleResultDTO,
    BtpSummaryResultDTO,
    StampDutyResultDTO,
)
from intelligent_investor.dtos.btp_transaction import BtpTransactionDTO
from intelligent_investor.services.bond_calculator_common import calc_commission, calc_stamp_duty
from intelligent_investor.utils.coupon_schedule import CouponPayment, CouponSchedule
from intelligent_investor.utils.yield_calculator import YieldCalculator, xirr

# Reduction factor applied to the capital gain taxable base for government bonds
# (TdS): 12.5% tax / 26% standard rate = 0.4808 reduction → effective rate = 12.5%
_TDS_REDUCTION: float = 0.4808
_CAPITAL_GAIN_RATE: float = 0.26


class BtpCalculatorService:
    """
    Stateless service that computes the full BTP purchase/sale result,
    including the coupon flows accrued while the bond is held.

    Usage:
        result = BtpCalculatorService().calculate(transaction, bond)
    """

    def calculate(
        self,
        transaction: BtpTransactionDTO,
        bond: BondDTO,
    ) -> BtpCalculationResultDTO:
        """
        Compute all purchase, coupon, sale, capital-gain, stamp-duty and
        summary figures for the given transaction and bond.

        Args:
            transaction: user-supplied transaction parameters.
            bond:        the bond being traded (provides dates, coupon, prices, tax_rate).

        Returns:
            A fully populated BtpCalculationResultDTO.
        """
        quantity: float = transaction.quantity
        coupon_schedule = CouponSchedule(
            bond.issue_date, bond.maturity_date, bond.coupon_frequency, bond.nominal_rate, bond.tax_rate
        )

        # Effective sale date and price (maturity when no early sale)
        sale_date: date = transaction.sale_date or bond.maturity_date
        sale_price: float = transaction.sale_price or bond.redemption_price

        purchase: BtpPurchaseResultDTO = self._calc_purchase(transaction, coupon_schedule, quantity)
        coupon_plan: list[CouponPayment] = self._calc_coupon_schedule(
            coupon_schedule, transaction.purchase_date, sale_date
        )
        sale: BtpSaleResultDTO = self._calc_sale(transaction, coupon_schedule, quantity, sale_date, sale_price)
        capital_gain: BtpCapitalGainResultDTO = self._calc_capital_gain(
            tx=transaction,
            bond=bond,
            quantity=quantity,
            sale_price=sale_price,
            purchase=purchase,
            sale=sale,
        )
        # Deduct capital gain tax from total_received (withheld by the broker at redemption)
        if capital_gain.capital_gain_tax > 0:
            sale = sale.model_copy(update={"total_received": sale.total_received - capital_gain.capital_gain_tax})
        stamp_duty: StampDutyResultDTO = calc_stamp_duty(
            duty_base_amount=purchase.dirty_amount,
            face_value=transaction.face_value,
            purchase_date=transaction.purchase_date,
            sale_date=sale_date,
            stamp_duty_period=transaction.stamp_duty_period,
        )
        summary: BtpSummaryResultDTO = self._calc_summary(
            purchase=purchase,
            coupon_plan=coupon_plan,
            sale=sale,
            stamp_duty=stamp_duty,
            quantity=quantity,
            purchase_date=transaction.purchase_date,
            sale_date=sale_date,
        )

        return BtpCalculationResultDTO(
            quantity=quantity,
            purchase=purchase,
            coupon_plan=coupon_plan,
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
        tx: BtpTransactionDTO,
        coupon_schedule: CouponSchedule,
        quantity: float,
    ) -> BtpPurchaseResultDTO:
        # Accrued interest (rateo) owed to the seller: a plain transfer between
        # the two private parties, not income — no withholding applies to it.
        accrued_interest: float = coupon_schedule.accrued_interest(tx.purchase_date)
        dirty_price: float = tx.purchase_price + accrued_interest
        dirty_amount: float = dirty_price * quantity

        commission: float = calc_commission(
            base=tx.face_value if tx.purchase_venue == "asta" else dirty_amount,
            pct=tx.buy_commission_pct,
            min_fee=tx.buy_commission_min,
            max_fee=tx.buy_commission_max,
        )
        fixed_commission = tx.buy_commission_fixed
        total_paid = dirty_amount + commission + fixed_commission

        return BtpPurchaseResultDTO(
            clean_price=tx.purchase_price,
            accrued_interest=accrued_interest,
            dirty_price=dirty_price,
            dirty_amount=dirty_amount,
            commission=commission,
            fixed_commission=fixed_commission,
            total_paid=total_paid,
        )

    def _calc_coupon_schedule(
        self,
        coupon_schedule: CouponSchedule,
        purchase_date: date,
        sale_date: date,
    ) -> list[CouponPayment]:
        # Only coupons actually cashed in by this holder: paid after purchase
        # (the rateo already compensated the seller for anything earlier) and
        # on or before the sale/maturity date (an early sale hands the running
        # coupon's rateo to the buyer instead, via _calc_sale).
        return [cp for cp in coupon_schedule.schedule if purchase_date < cp.payment_date <= sale_date]

    def _calc_sale(
        self,
        tx: BtpTransactionDTO,
        coupon_schedule: CouponSchedule,
        quantity: float,
        sale_date: date,
        sale_price: float,
    ) -> BtpSaleResultDTO:
        # Accrued interest owed by the buyer to the seller for the running
        # coupon period (0.0 when held to maturity on a coupon date).
        accrued_interest: float = coupon_schedule.accrued_interest(sale_date)
        dirty_price: float = sale_price + accrued_interest
        dirty_amount: float = dirty_price * quantity

        commission: float = calc_commission(
            base=dirty_amount,
            pct=tx.sell_commission_pct,
            min_fee=tx.sell_commission_min,
            max_fee=tx.sell_commission_max,
        )
        fixed_commission: float = tx.sell_commission_fixed
        total_received: float = dirty_amount - commission - fixed_commission

        return BtpSaleResultDTO(
            clean_price=sale_price,
            accrued_interest=accrued_interest,
            dirty_price=dirty_price,
            dirty_amount=dirty_amount,
            commission=commission,
            fixed_commission=fixed_commission,
            total_received=total_received,
        )

    def _calc_capital_gain(
        self,
        tx: BtpTransactionDTO,
        bond: BondDTO,
        quantity: float,
        sale_price: float,
        purchase: BtpPurchaseResultDTO,
        sale: BtpSaleResultDTO,
    ) -> BtpCapitalGainResultDTO:
        # Unlike a BOT, a BTP's clean price isn't constrained to a fixed
        # issue→maturity accretion line, so no theoretical-price offset is
        # needed: the capital gain is simply the clean-price gap (commissions
        # spread per unit), since the accrued-interest portions are excluded
        # by construction (clean_price already strips them out).
        load_price: float = tx.purchase_price + (purchase.commission + purchase.fixed_commission) / quantity
        unload_price: float = sale_price - (sale.commission + sale.fixed_commission) / quantity

        unit_gain_loss: float = unload_price - load_price
        tax_rate: float = bond.tax_rate / 100  # 0.125 for TdS

        # Step 1 — Plus/Minus Realizzata
        total_gain_loss: float = unit_gain_loss * quantity

        # Step 2 — Riduzione Imponibile per TdS — informativa
        tds_reduction: float = total_gain_loss * _TDS_REDUCTION

        # Step 3 — Imposta sulla plusvalenza: tax_rate% applicato direttamente
        # sulla plus. È questa che il sostituto d'imposta trattiene al rimborso.
        capital_gain_tax: float = total_gain_loss * tax_rate if total_gain_loss > 0 else 0.0

        if total_gain_loss > 0:
            # Zainetto residuo: parte dello zainetto non consumata dalla plus
            scaled_losses: float = tx.portfolio_losses * tax_rate / _CAPITAL_GAIN_RATE
            plus_after_tds: float = total_gain_loss - tds_reduction
            consumed: float = min(scaled_losses, plus_after_tds)
            remaining_loss: float = max(0.0, tx.portfolio_losses - consumed * _CAPITAL_GAIN_RATE / tax_rate)
        else:
            # Minus da aggiungere allo zainetto
            remaining_loss = abs(tds_reduction)

        return BtpCapitalGainResultDTO(
            load_price=load_price,
            unload_price=unload_price,
            unit_gain_loss=unit_gain_loss,
            total_gain_loss=total_gain_loss,
            tds_reduction=tds_reduction,
            capital_gain_tax=capital_gain_tax,
            remaining_loss=remaining_loss,
        )

    def _calc_summary(
        self,
        purchase: BtpPurchaseResultDTO,
        coupon_plan: list[CouponPayment],
        sale: BtpSaleResultDTO,
        stamp_duty: StampDutyResultDTO,
        quantity: float,
        purchase_date: date,
        sale_date: date,
    ) -> BtpSummaryResultDTO:
        gross_coupons: float = sum(cp.gross_amount for cp in coupon_plan) * quantity
        net_coupons: float = sum(cp.net_amount for cp in coupon_plan) * quantity

        # Gross gain = pure cash flow without commissions, taxes or stamp duty
        gross_gain: float = gross_coupons + sale.dirty_amount - purchase.dirty_amount
        # Net gain before duty = net coupons + total received - total paid.
        # capital_gain_tax is already deducted from sale.total_received by calculate().
        net_gain_before_duty: float = net_coupons + sale.total_received - purchase.total_paid
        net_gain: float = net_gain_before_duty - stamp_duty.estimated_duty

        yc = YieldCalculator(purchase_date, sale_date)

        # Lordo: nessuna commissione, nessuna imposta
        gross_cashflows: list[tuple[date, float]] = (
            [(purchase_date, -purchase.dirty_amount)]
            + [(cp.payment_date, cp.gross_amount * quantity) for cp in coupon_plan]
            + [(sale_date, sale.dirty_amount)]
        )
        simple_gross_yield: float = yc.simple(gross_gain, purchase.dirty_amount)
        compound_gross_yield: float = xirr(gross_cashflows)

        # Netto pre-bollo: cedole nette, capital_gain_tax già dedotta da sale.total_received
        net_cashflows_before_duty: list[tuple[date, float]] = (
            [(purchase_date, -purchase.total_paid)]
            + [(cp.payment_date, cp.net_amount * quantity) for cp in coupon_plan]
            + [(sale_date, sale.total_received)]
        )
        simple_net_yield_before_duty: float = yc.simple(net_gain_before_duty, purchase.total_paid)
        compound_net_yield_before_duty: float = xirr(net_cashflows_before_duty)

        # Netto: bollo dedotto dall'ultimo flusso
        net_cashflows: list[tuple[date, float]] = (
            [(purchase_date, -purchase.total_paid)]
            + [(cp.payment_date, cp.net_amount * quantity) for cp in coupon_plan]
            + [(sale_date, sale.total_received - stamp_duty.estimated_duty)]
        )
        simple_net_yield: float = yc.simple(net_gain, purchase.total_paid)
        compound_net_yield: float = xirr(net_cashflows)

        return BtpSummaryResultDTO(
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
