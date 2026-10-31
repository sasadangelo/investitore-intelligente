# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
"""
Bond calculator: net result of buying (and optionally selling) a BOT or a fixed-rate BTP.

A BOT is the no-coupon case of a BTP, as in the `Bond` sheet of the reference
spreadsheet (docs/ObbligazioniTF v5.0.ods), which uses one sheet for every bond
type. The only type-dependent part is the issue discount (scarto di emissione):
how it accrues and when its 12.5% withholding is paid. That rule is isolated in
_BotDiscountRule and _CouponBondDiscountRule; everything else is shared.

Every time-dependent step (rateo, discount accrual, simple and compound yields)
uses the day-count convention of the bond type from utils/day_count.py.
"""
from datetime import date
from decimal import Decimal
from typing import Literal, Protocol

from intelligent_investor.dtos.bond import BondDTO
from intelligent_investor.dtos.bond_calculation_result import (
    BondCalculationResultDTO,
    CapitalGainResultDTO,
    PurchaseResultDTO,
    SaleResultDTO,
    StampDutyResultDTO,
    SummaryResultDTO,
)
from intelligent_investor.dtos.bond_transaction import (
    BondTransactionDTO,
    BuyTransactionDTO,
    SellTransactionDTO,
    TransactionDTO,
)
from intelligent_investor.utils.coupon_schedule import CouponPayment, CouponSchedule, next_coupon_date
from intelligent_investor.utils.day_count import BondConventions, DayCountConvention, conventions_for
from intelligent_investor.utils.duration import modified_duration
from intelligent_investor.utils.yield_calculator import YieldCalculator, xirr

# Standard capital gain rate: a government-bond (TdS) gain taxed at tax_rate counts for
# tax_rate / 26% (48.08% at 12.5%) of its amount against the zainetto (cell C10)
_CAPITAL_GAIN_RATE: float = 0.26
STAMP_DUTY_RATE: float = 0.002  # 0.20% per year

# Coupon bonds issued before this date accrue their discount only from the first
# coupon date after it (cell AH7 of the `Bond` sheet)
_DISCOUNT_RULE_START: date = date(1997, 1, 1)


class BondCalculatorService:
    """
    Stateless service that computes the full purchase/sale result of a bond.

    Usage:
        result = BondCalculatorService().calculate(transaction, bond)
    """

    def calculate(self, transaction: BondTransactionDTO, bond: BondDTO) -> BondCalculationResultDTO:
        """
        Compute purchase, coupons, sale, capital gain, stamp duty and summary figures.

        Args:
            transaction: User-supplied transaction parameters
            bond: The bond being traded (dates, prices, coupon, tax rate)

        Returns:
            The fully populated result
        """
        quantity: float = transaction.quantity
        conventions: BondConventions = conventions_for(bond.bond_type)
        discount_rule = _discount_rule_for(bond, conventions.issue_discount)
        coupon_schedule = CouponSchedule(
            bond.issue_date,
            bond.maturity_date,
            bond.coupon_frequency,
            bond.nominal_rate,
            bond.tax_rate,
            accrued_interest_convention=conventions.accrued_interest,
            first_coupon_date=bond.first_coupon_date,
        )

        buy, sell, account = transaction.buy, transaction.sell, transaction.account
        # Effective sale date and price (maturity when no early sale)
        sale_date: date = sell.date if sell else bond.maturity_date
        sale_price: float = sell.price if sell else bond.redemption_price

        tax_rate: float = bond.tax_rate / 100
        purchase = self._calc_purchase(buy, coupon_schedule, discount_rule, quantity, tax_rate)
        coupon_plan = self._calc_coupon_plan(coupon_schedule, buy.date, sale_date)
        sale = self._calc_sale(sell, coupon_schedule, discount_rule, quantity, tax_rate, sale_date, sale_price)
        capital_gain = self._calc_capital_gain(
            tx=transaction,
            bond=bond,
            discount_rule=discount_rule,
            quantity=quantity,
            sale_date=sale_date,
            sale_price=sale_price,
            purchase=purchase,
            sale=sale,
        )
        # Capital gain tax is withheld by the broker at sale/redemption
        if capital_gain.capital_gain_tax > 0:
            sale = sale.model_copy(update={"total_received": sale.total_received - capital_gain.capital_gain_tax})
        stamp_duty = calc_stamp_duty(
            duty_base_amount=purchase.dry_amount,
            face_value=buy.face_value,
            purchase_date=buy.date,
            sale_date=sale_date,
            stamp_duty_period=account.stamp_duty_period,
        )
        summary = self._calc_summary(
            coupon_fee=account.coupon_fee,
            bond=bond,
            conventions=conventions,
            purchase=purchase,
            coupon_plan=coupon_plan,
            sale=sale,
            stamp_duty=stamp_duty,
            quantity=quantity,
            purchase_date=buy.date,
            sale_date=sale_date,
        )

        return BondCalculationResultDTO(
            quantity=quantity,
            purchase=purchase,
            coupon_plan=coupon_plan,
            coupon_fee=account.coupon_fee,
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
        buy: BuyTransactionDTO,
        coupon_schedule: CouponSchedule,
        discount_rule: "_DiscountRule",
        quantity: float,
        tax_rate: float,
    ) -> PurchaseResultDTO:
        # Accrued interest (rateo) owed to the seller for the running coupon period
        # (always 0.0 for a BOT, which has no coupons)
        accrued_interest: float = coupon_schedule.accrued_interest(buy.date)
        dirty_price: float = buy.price + accrued_interest
        dry_amount: float = buy.price * quantity
        dirty_amount: float = dirty_price * quantity

        # Commission base: face value at auction, clean amount on the market (cell A26)
        commission: float = trade_commission(buy, dry_amount)
        fixed_commission: float = buy.commission_fixed
        unit_discount, discount_tax = discount_rule.purchase_withholding(buy.date, quantity)
        # The next coupon is taxed in full, including the part paid to the seller as
        # rateo: the buyer gets a 12.5% credit on that part (cell K28)
        accrued_interest_tax: float = -accrued_interest * quantity * tax_rate
        total_paid: float = dirty_amount + commission + fixed_commission + discount_tax + accrued_interest_tax

        return PurchaseResultDTO(
            clean_price=buy.price,
            accrued_interest=accrued_interest,
            dirty_price=dirty_price,
            dry_amount=dry_amount,
            dirty_amount=dirty_amount,
            commission=commission,
            fixed_commission=fixed_commission,
            unit_discount=unit_discount,
            discount_tax=discount_tax,
            accrued_interest_tax=accrued_interest_tax,
            total_paid=total_paid,
        )

    def _calc_coupon_plan(
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
        sell: SellTransactionDTO | None,
        coupon_schedule: CouponSchedule,
        discount_rule: "_DiscountRule",
        quantity: float,
        tax_rate: float,
        sale_date: date,
        sale_price: float,
    ) -> SaleResultDTO:
        # Accrued interest owed by the buyer to the seller for the running coupon
        # period (0.0 at maturity, where the last coupon is paid in full)
        accrued_interest: float = coupon_schedule.accrued_interest(sale_date)
        dirty_price: float = sale_price + accrued_interest
        dry_amount: float = sale_price * quantity
        dirty_amount: float = dirty_price * quantity

        if sell is None:
            # Redemption is not a sale: no sale commission applies (cell K36)
            commission: float = 0.0
            fixed_commission: float = 0.0
        else:
            # Commission base: clean amount (cell A44)
            commission = trade_commission(sell, dry_amount)
            fixed_commission = sell.commission_fixed
        unit_discount, discount_tax = discount_rule.sale_withholding(sale_date, sell is None, quantity)
        # The rateo cashed from the buyer is coupon income: 12.5% is withheld on it (cell K40)
        accrued_interest_tax: float = -accrued_interest * quantity * tax_rate
        total_received: float = dirty_amount - commission - fixed_commission + discount_tax + accrued_interest_tax

        return SaleResultDTO(
            clean_price=sale_price,
            accrued_interest=accrued_interest,
            dirty_price=dirty_price,
            dry_amount=dry_amount,
            dirty_amount=dirty_amount,
            commission=commission,
            fixed_commission=fixed_commission,
            unit_discount=unit_discount,
            discount_tax=discount_tax,
            accrued_interest_tax=accrued_interest_tax,
            total_received=total_received,
        )

    def _calc_capital_gain(
        self,
        tx: BondTransactionDTO,
        bond: BondDTO,
        discount_rule: "_DiscountRule",
        quantity: float,
        sale_date: date,
        sale_price: float,
        purchase: PurchaseResultDTO,
        sale: SaleResultDTO,
    ) -> CapitalGainResultDTO:
        # Computed for every purchase, auction included, as the sheet does (K26/K38 do not
        # look at the venue): at auction the theoretical price is the issue price, but the
        # commissions still raise the load price, and an early sale can be above or below
        # the theoretical price
        theoretical_purchase_price: float = discount_rule.theoretical_price(tx.buy.date)
        theoretical_sale_price: float = discount_rule.theoretical_price(sale_date, at_maturity=tx.holds_to_maturity)

        # Load/unload prices: clean price with commissions spread per unit, minus the
        # discount accrued so far — that part of the price gap is taxed as discount
        # (discount_tax), not as a capital gain/loss (cells K26 and K38)
        load_price: float = (
            tx.buy.price
            + (purchase.commission + purchase.fixed_commission) / quantity
            - discount_rule.accrued_discount(tx.buy.date)
        )
        unload_price: float = (
            sale_price
            - (sale.commission + sale.fixed_commission) / quantity
            - discount_rule.accrued_discount(sale_date, at_maturity=tx.holds_to_maturity)
        )

        unit_gain_loss: float = unload_price - load_price
        tax_rate: float = bond.tax_rate / 100  # 0.125 for TdS
        tds_factor: float = tax_rate / _CAPITAL_GAIN_RATE  # 0.4808 for TdS (cell C10)

        # Step 1 — Plus/Minus Realizzata (K48)
        total_gain_loss: float = unit_gain_loss * quantity

        # Step 2 — Riduzione Imponibile per TdS (K49): the part of the gain or loss that
        # counts against the zainetto
        tds_reduction: float = total_gain_loss * tds_factor

        if total_gain_loss > 0:
            # Step 3 — the zainetto offsets the reduced gain (K51); the tax on what is left,
            # brought back to the full gain, is withheld at sale/redemption (K52)
            taxable: float = max(0.0, tds_reduction - tx.account.portfolio_losses)
            capital_gain_tax: float = taxable / tds_factor * tax_rate if tds_factor > 0 else 0.0
            # Zainetto residuo: part of the zainetto not consumed by the gain (K53)
            remaining_loss: float = max(0.0, tx.account.portfolio_losses - tds_reduction)
        else:
            capital_gain_tax = 0.0
            # Loss to add to the zainetto: abs(total) × 48.08%
            remaining_loss = abs(tds_reduction)

        return CapitalGainResultDTO(
            theoretical_purchase_price=theoretical_purchase_price,
            theoretical_sale_price=theoretical_sale_price,
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
        coupon_fee: float,
        bond: BondDTO,
        conventions: BondConventions,
        purchase: PurchaseResultDTO,
        coupon_plan: list[CouponPayment],
        sale: SaleResultDTO,
        stamp_duty: StampDutyResultDTO,
        quantity: float,
        purchase_date: date,
        sale_date: date,
    ) -> SummaryResultDTO:
        gross_coupons: float = sum(cp.gross_amount for cp in coupon_plan) * quantity
        # The bank's fee per coupon (cell K44) reduces every net coupon cashed, not the gross ones
        net_coupons: float = sum(cp.net_amount for cp in coupon_plan) * quantity - coupon_fee * len(coupon_plan)

        # Gross gain = pure cash flow without commissions, taxes or stamp duty
        gross_gain: float = gross_coupons + sale.dirty_amount - purchase.dirty_amount
        # Net gain before duty = net coupons + total received − total paid
        # (capital_gain_tax is already deducted from sale.total_received by calculate()).
        # Decimal avoids float subtraction errors on midpoint values (e.g. 144.575
        # must round to 144.58 via ROUND_HALF_UP, not 144.57).
        net_gain_before_duty: float = float(
            Decimal(str(net_coupons)) + Decimal(str(sale.total_received)) - Decimal(str(purchase.total_paid))
        )
        net_gain: float = float(Decimal(str(net_gain_before_duty)) - Decimal(str(stamp_duty.estimated_duty)))

        yc = YieldCalculator(
            purchase_date,
            sale_date,
            simple_convention=conventions.simple_yield,
            compound_convention=conventions.compound_yield,
        )
        simple_gross_yield: float = yc.simple(gross_gain, purchase.dirty_amount)
        simple_net_yield_before_duty: float = yc.simple(net_gain_before_duty, purchase.total_paid)
        simple_net_yield: float = yc.simple(net_gain, purchase.total_paid)

        net_proceeds: float = sale.total_received - stamp_duty.estimated_duty
        if not coupon_plan:
            # Two cash flows only: closed-form compound yield (same value as XIRR)
            compound_gross_yield: float = yc.compound(sale.dirty_amount, purchase.dirty_amount)
            compound_net_yield_before_duty: float = yc.compound(sale.total_received, purchase.total_paid)
            compound_net_yield: float = yc.compound(net_proceeds, purchase.total_paid)
        else:
            # Coupons in between: XIRR on the dated cash flows
            def flows(outflow: float, coupon_side: Literal["gross", "net"], inflow: float) -> list[tuple[date, float]]:
                coupons = [
                    (
                        cp.payment_date,
                        cp.gross_amount * quantity
                        if coupon_side == "gross"
                        else cp.net_amount * quantity - coupon_fee,
                    )
                    for cp in coupon_plan
                ]
                return [(purchase_date, -outflow)] + coupons + [(sale_date, inflow)]

            compound = conventions.compound_yield
            compound_gross_yield = xirr(flows(purchase.dirty_amount, "gross", sale.dirty_amount), convention=compound)
            net_flows = flows(purchase.total_paid, "net", sale.total_received)
            compound_net_yield_before_duty = xirr(net_flows, convention=compound)
            # Stamp duty taken out year by year, as the sheet does (column R)
            compound_net_yield = xirr(spread_stamp_duty(net_flows, stamp_duty.estimated_duty), convention=compound)

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
            # On the net yield, as cell K16 (K4 = net yield after stamp duty)
            modified_duration=calc_modified_duration(bond, purchase_date, sale_date, compound_net_yield),
        )


# ---------------------------------------------------------------------------
# Issue discount (scarto di emissione) rules — the only type-dependent part
# ---------------------------------------------------------------------------


class _DiscountRule(Protocol):
    """How the issue discount accrues and when its withholding is paid."""

    def theoretical_price(self, d: date, at_maturity: bool = False) -> float:
        """Issue price plus the discount accrued at *d* (prezzo teorico)."""
        ...

    def accrued_discount(self, d: date, at_maturity: bool = False) -> float:
        """Discount accrued at *d*, per 100 of nominal, used for load/unload prices."""
        ...

    def purchase_withholding(self, purchase_date: date, quantity: float) -> tuple[float, float]:
        """(unit_discount, signed discount_tax) of the purchase leg."""
        ...

    def sale_withholding(self, sale_date: date, at_maturity: bool, quantity: float) -> tuple[float, float]:
        """(unit_discount, signed discount_tax) of the sale/redemption leg."""
        ...


class _BotDiscountRule:
    """
    BOT (`Bond` sheet with F6 = 3): the discount accrues in proportion to the time
    elapsed from issue to maturity, measured in the BOT discount convention (act/365:
    the ratio of actual days). The buyer pays upfront the tax on the discount still
    to accrue, and an early seller gets back the part that will accrue after the sale.
    """

    def __init__(self, bond: BondDTO, convention: DayCountConvention) -> None:
        self._bond = bond
        self._convention = convention
        self._discount: Decimal = Decimal(str(bond.redemption_price)) - Decimal(str(bond.issue_price))

    def theoretical_price(self, d: date, at_maturity: bool = False) -> float:
        bond = self._bond
        return bond.issue_price + (bond.redemption_price - bond.issue_price) * float(self._elapsed(d))

    def accrued_discount(self, d: date, at_maturity: bool = False) -> float:
        return self.theoretical_price(d) - self._bond.issue_price

    def purchase_withholding(self, purchase_date: date, quantity: float) -> tuple[float, float]:
        return self._residual_discount_tax(purchase_date, quantity)

    def sale_withholding(self, sale_date: date, at_maturity: bool, quantity: float) -> tuple[float, float]:
        # 0.0 at maturity: no discount is left to accrue
        return self._residual_discount_tax(sale_date, quantity)

    def _elapsed(self, d: date) -> Decimal:
        """Share of the BOT life elapsed at *d*."""
        return self._convention.accrual_fraction(self._bond.issue_date, d, self._bond.maturity_date)

    def _residual_discount_tax(self, d: date, quantity: float) -> tuple[float, float]:
        """Discount still to accrue from *d* to maturity, and the (positive) tax on it."""
        bond = self._bond
        residual: Decimal = 1 - self._elapsed(d)
        unit_discount: float = float(self._discount * residual)
        # Decimal keeps the tax exact to the cent, as in the reference spreadsheet
        discount_tax: float = float(
            self._discount * residual * Decimal(str(bond.tax_rate)) / Decimal("100") * Decimal(str(quantity))
        )
        return unit_discount, discount_tax


class _CouponBondDiscountRule:
    """
    Coupon bond (`Bond` sheet with F6 = 2): the discount accrues by YEARFRAC in the
    BTP discount convention (act/act) from the fiscal issue date (F29). The buyer gets a tax credit on the discount
    already accrued (K27); the seller is withheld the tax on the discount accrued up
    to the sale (K39), or on the whole discount at maturity (F16). Bonds issued at
    or above par have no discount (F30 = 0).
    """

    def __init__(self, bond: BondDTO, convention: DayCountConvention) -> None:
        self._bond = bond
        self._convention = convention
        self._tax_rate: float = bond.tax_rate / 100
        # Gross issue discount per 100 of nominal (F15), 0.0 when issued at or above par
        self._discount: float = max(0.0, bond.redemption_price - bond.issue_price)
        # Discount accrues from the issue date, or from the first coupon date after
        # 1/1/1997 for older bonds (AH7); the denominator always spans issue→maturity
        self._accrual_start: date = max(
            bond.issue_date, next_coupon_date(_DISCOUNT_RULE_START, bond.maturity_date, bond.coupon_frequency)
        )
        self._life: float = convention.year_fraction(bond.issue_date, bond.maturity_date)

    def theoretical_price(self, d: date, at_maturity: bool = False) -> float:
        bond = self._bond
        if at_maturity:
            return bond.redemption_price
        accrued_years: float = 0.0
        if d > self._accrual_start:
            accrued_years = self._convention.year_fraction(self._accrual_start, d)
        # Unclamped, as in F29: for a bond issued above par it moves down towards par
        return bond.issue_price + (bond.redemption_price - bond.issue_price) / self._life * accrued_years

    def accrued_discount(self, d: date, at_maturity: bool = False) -> float:
        if self._discount == 0.0:
            return 0.0
        if at_maturity:
            return self._discount
        return self.theoretical_price(d) - self._bond.issue_price

    def purchase_withholding(self, purchase_date: date, quantity: float) -> tuple[float, float]:
        unit_discount: float = self.accrued_discount(purchase_date)
        return unit_discount, -unit_discount * self._tax_rate * quantity

    def sale_withholding(self, sale_date: date, at_maturity: bool, quantity: float) -> tuple[float, float]:
        unit_discount: float = self.accrued_discount(sale_date, at_maturity=at_maturity)
        return unit_discount, -unit_discount * self._tax_rate * quantity


def _discount_rule_for(bond: BondDTO, convention: DayCountConvention) -> _DiscountRule:
    """
    Pick the discount rule for *bond* (only BOTs and fixed-rate BTPs are handled).

    Args:
        bond: The bond being traded
        convention: Day count of the discount accrual for its bond type
    """
    if bond.bond_type == "BOT":
        return _BotDiscountRule(bond, convention)
    return _CouponBondDiscountRule(bond, convention)


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def trade_commission(trade: TransactionDTO, dry_amount: float) -> float:
    """
    Percentage commission of a trade, on the base its type defines (TransactionDTO.commission_base).

    Args:
        trade: The purchase or the sale
        dry_amount: Clean amount traded (price × quantity)

    Returns:
        The commission in €, without the fixed fee
    """
    return calc_commission(
        base=trade.commission_base(dry_amount),
        pct=trade.commission_pct,
        min_fee=trade.commission_min,
        max_fee=trade.commission_max,
    )


def calc_commission(base: float, pct: float, min_fee: float, max_fee: float | None) -> float:
    """
    Apply a percentage commission on base, clamped to [min_fee, max_fee].

    max_fee=None means no upper cap.
    """
    raw: float = base * (pct / 100)
    clamped: float = max(raw, min_fee)
    if max_fee is not None:
        clamped = min(clamped, max_fee)
    return clamped


def calc_modified_duration(bond: BondDTO, settlement_date: date, end_date: date, yield_pct: float) -> float | None:
    """
    Modified duration of a bond bought on settlement_date, as cell K16 of the `Bond` sheet.

    MDURATION runs on the flows up to maturity even when the bond is sold earlier,
    but the sheet leaves it blank when the holding (settlement to end_date, cell M15)
    is shorter than 365 days, for a bond without coupons and for a non-positive yield.

    Args:
        bond: The bond (maturity, coupon rate and frequency, bond type)
        settlement_date: Purchase settlement date
        end_date: Sale date, or maturity when the bond is held to maturity
        yield_pct: Annual yield the flows are discounted at, in %

    Returns:
        The modified duration, or None where the sheet shows nothing
    """
    if bond.coupon_frequency <= 0 or bond.nominal_rate <= 0 or yield_pct <= 0:
        return None
    if (end_date - settlement_date).days < 365:
        return None
    return modified_duration(
        settlement_date,
        bond.maturity_date,
        bond.nominal_rate,
        yield_pct,
        bond.coupon_frequency,
        conventions_for(bond.bond_type).duration,
    )


def spread_stamp_duty(flows: list[tuple[date, float]], duty: float) -> list[tuple[date, float]]:
    """
    Subtract the stamp duty from dated cash flows one calendar year at a time (column R).

    The duty is split evenly over the calendar years between the first and the last
    flow (cell M17) and each share is taken from the first flow of the new year; when
    both fall in the same year the whole duty comes out of the last flow.

    Args:
        flows: (date, amount) pairs in date order, the purchase first
        duty: Total stamp duty of the holding (cell K17)

    Returns:
        The flows with the duty subtracted; the total subtracted is always *duty*
    """
    years = flows[-1][0].year - flows[0][0].year
    if years <= 0:
        return flows[:-1] + [(flows[-1][0], flows[-1][1] - duty)]
    per_year = duty / years
    spread = [flows[0]]
    for (previous, _), (current, amount) in zip(flows, flows[1:], strict=False):  # consecutive pairs
        spread.append((current, amount - per_year * (current.year - previous.year)))
    return spread


def calc_stamp_duty(
    duty_base_amount: float,
    face_value: float,
    purchase_date: date,
    sale_date: date,
    stamp_duty_period: Literal["annual", "quarterly"],
) -> StampDutyResultDTO:
    """
    Estimate the 0.20%/year stamp duty on a bond holding.

    Args:
        duty_base_amount: Clean purchase amount before commissions, averaged with
            face_value as in the reference spreadsheet: (F25 + 100) / 2 (cell K17)
        face_value: Nominal lot
        purchase_date: Settlement date of the purchase
        sale_date: Settlement date of the sale, or maturity
        stamp_duty_period: How often the bank charges it

    Returns:
        Number of holding periods and the estimated duty
    """
    duty_base: float = (duty_base_amount + face_value) / 2
    months_held: int = (sale_date.year - purchase_date.year) * 12 + (sale_date.month - purchase_date.month)

    if stamp_duty_period == "annual":
        periods: int = months_held
        estimated_duty: float = duty_base * STAMP_DUTY_RATE * periods / 12
    else:  # quarterly
        # Count calendar quarter boundaries crossed:
        # QUOTIENT(MONTH(purchase)-1 + months_held, 3) - QUOTIENT(MONTH(purchase)-1, 3)
        periods = (purchase_date.month - 1 + months_held) // 3 - (purchase_date.month - 1) // 3
        estimated_duty = duty_base * STAMP_DUTY_RATE * periods / 4

    return StampDutyResultDTO(
        holding_periods=max(0, periods),
        estimated_duty=max(0.0, estimated_duty),
    )
