# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
"""
Coupon schedule and accrued-interest utilities for fixed-rate coupon bonds (BTP).

Reusable by both the BTP calculator (Fase 4) and the bond catalogue (Fase 5).
coupon_frequency=0 (zero-coupon, e.g. BOT) is treated as a no-coupon degenerate
case throughout: schedules are empty and accrued interest is always 0.0.
"""
from dataclasses import dataclass
from datetime import date

from intelligent_investor.utils.day_count import DayCountConvention


@dataclass(frozen=True)
class CouponPayment:
    """A single coupon date (stacco): payment date + gross/net amount per 100 of nominal."""

    payment_date: date
    gross_amount: float
    net_amount: float


class CouponSchedule:
    """
    Coupon schedule and accrued-interest calculator for a single fixed-rate bond.

    Bundles the bond's coupon parameters once at construction (mirrors
    YieldCalculator's stateful style) and lazily caches the generated coupon
    dates, since previous_coupon_date/accrued_interest/schedule all need the
    same underlying list — computing it once avoids re-walking the backward
    date generation on every call.

    Args:
        issue_date:       Bond issue date.
        maturity_date:    Bond maturity date (must be after issue_date).
        coupon_frequency: Coupons per year (1=annual, 2=semi-annual, ...).
                           0 (zero-coupon, e.g. BOT) degenerates to no coupons.
        nominal_rate:     Annual coupon rate, in % (e.g. 3.6).
        tax_rate:         Withholding tax on coupons and accrued interest (rateo),
                           in % (default 12.5).
        accrued_interest_convention: Day count of the rateo (default act/act, the
                           ICMA rule; see BondConventions.accrued_interest).

    Usage — BTP calculator::

        cs = CouponSchedule(bond.issue_date, bond.maturity_date, bond.coupon_frequency,
                             bond.nominal_rate, bond.tax_rate)
        gross_accrued = cs.accrued_interest(purchase_date)      # rateo lordo
        net_accrued = cs.net_accrued_interest(purchase_date)    # rateo netto
        coupon_plan = cs.schedule                                # piano cedole
    """

    def __init__(
        self,
        issue_date: date,
        maturity_date: date,
        coupon_frequency: int,
        nominal_rate: float,
        tax_rate: float = 12.5,
        accrued_interest_convention: DayCountConvention = DayCountConvention.ACT_ACT,
    ) -> None:
        if coupon_frequency > 0:
            if issue_date >= maturity_date:
                raise ValueError("issue_date must be earlier than maturity_date")
            if 12 % coupon_frequency != 0:
                raise ValueError(f"unsupported coupon_frequency: {coupon_frequency}")
        self._issue_date = issue_date
        self._maturity_date = maturity_date
        self._coupon_frequency = coupon_frequency
        self._nominal_rate = nominal_rate
        self._tax_rate = tax_rate
        self._accrued_interest_convention = accrued_interest_convention
        self._dates: list[date] | None = None  # lazy cache

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def dates(self) -> list[date]:
        """
        Ascending list of coupon dates (date di stacco) in (issue_date, maturity_date].

        Equivalent to Excel/LibreOffice COUPNCD: coupons are anchored to
        maturity_date and generated backwards in steps of 12/coupon_frequency
        months (e.g. maturity 15/07, semi-annual → ..., 15/01/Y, 15/07/Y).
        Empty when coupon_frequency == 0.
        """
        if self._dates is None:
            self._dates = self._generate_dates()
        return self._dates

    @property
    def gross_coupon_amount(self) -> float:
        """Gross coupon paid per 100 of nominal at each coupon date (0.0 if coupon_frequency == 0)."""
        if self._coupon_frequency <= 0:
            return 0.0
        return self._nominal_rate / self._coupon_frequency

    @property
    def net_coupon_amount(self) -> float:
        """Net coupon paid per 100 of nominal at each coupon date, after withholding tax_rate%."""
        return self.gross_coupon_amount * (1 - self._tax_rate / 100)

    @property
    def schedule(self) -> list[CouponPayment]:
        """
        Full coupon plan (piano cedole) from issue to maturity: one CouponPayment
        per coupon date, with gross/net amount per 100 of nominal (constant across
        coupon dates, since the coupon is fixed-rate). Empty for coupon_frequency == 0.
        """
        gross = self.gross_coupon_amount
        net = self.net_coupon_amount
        return [CouponPayment(payment_date=d, gross_amount=gross, net_amount=net) for d in self.dates]

    def previous_coupon_date(self, settlement_date: date) -> date:
        """
        Return the last coupon date on or before settlement_date (data di regolamento).

        Falls back to issue_date when settlement_date precedes the first
        coupon, or when coupon_frequency == 0 (no coupons at all — the whole
        life is one "period" for accrued-interest purposes).
        """
        if self._coupon_frequency <= 0:
            return self._issue_date
        last = self._issue_date
        for d in self.dates:
            if d > settlement_date:
                break
            last = d
        return last

    def accrued_interest(self, settlement_date: date) -> float:
        """
        Gross accrued interest (rateo cedolare lordo) at settlement_date
        (data di regolamento), per 100 of nominal.

        Computed in the bond's accrued-interest convention (act/act ICMA for BOT and
        BTP, see utils/day_count.py), over the regular coupon period anchored to
        maturity, starting from the issue date when the bond was issued in the
        middle of it (foglio `Bond`, cells F36/F52).

        This is owed by the buyer to the seller at purchase (added on top of the
        clean price), and by the seller to the buyer at an early sale: the coupon
        is always paid in full to whoever holds the bond at the next coupon date,
        so the party who held it for only part of the period must be compensated
        for the days it actually accrued.

        Returns 0.0 when coupon_frequency == 0 (zero-coupon bonds have no accrued interest).
        """
        # At (or after) maturity the last coupon is paid in full: nothing is accrued
        if self._coupon_frequency <= 0 or settlement_date >= self._maturity_date:
            return 0.0
        period_start, period_end = self._coupon_period(settlement_date)
        return self._accrued_interest_convention.accrued_coupon(
            nominal_rate=self._nominal_rate,
            coupon_frequency=self._coupon_frequency,
            period_start=period_start,
            period_end=period_end,
            accrual_start=max(period_start, self._issue_date),
            settlement_date=settlement_date,
        )

    def net_accrued_interest(self, settlement_date: date) -> float:
        """Net accrued interest (rateo cedolare netto) at settlement_date, after withholding tax_rate%."""
        return self.accrued_interest(settlement_date) * (1 - self._tax_rate / 100)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _coupon_period(self, settlement_date: date) -> tuple[date, date]:
        """
        Regular coupon period containing settlement_date, as (start, end] anchored to maturity.

        start is the coupon date on or before settlement_date (COUPPCD) and may fall
        before issue_date; end is the next coupon date (COUPNCD).
        """
        end = next_coupon_date(settlement_date, self._maturity_date, self._coupon_frequency)
        periods_back = 0
        while _subtract_months(self._maturity_date, periods_back * 12 // self._coupon_frequency) != end:
            periods_back += 1
        start = _subtract_months(self._maturity_date, (periods_back + 1) * 12 // self._coupon_frequency)
        return start, end

    def _generate_dates(self) -> list[date]:
        if self._coupon_frequency <= 0:
            return []
        step_months = 12 // self._coupon_frequency
        # Coupon dates (date di stacco) are anchored to maturity_date, not
        # issue_date (COUPNCD convention): a bond's coupon calendar is fixed by
        # its final redemption date, so we walk backward from there in
        # step_months increments (e.g. 6 for semi-annual) until issue_date is
        # reached — matching how coupons actually fall in the real calendar.
        dates: list[date] = []
        current = self._maturity_date
        while current > self._issue_date:
            dates.append(current)
            current = _subtract_months(current, step_months)
        dates.reverse()
        return dates


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def next_coupon_date(settlement_date: date, maturity_date: date, coupon_frequency: int) -> date:
    """
    First coupon date strictly after settlement_date — equivalent of COUPNCD in LibreOffice/Excel.

    Coupon dates are anchored to maturity_date and step back by 12/coupon_frequency
    months, so the result does not depend on the issue date (it can fall before it).

    Args:
        settlement_date: Reference date
        maturity_date: Bond maturity, the last coupon date
        coupon_frequency: Coupons per year; 0 (no coupons) returns settlement_date

    Returns:
        The next coupon date, or maturity_date when settlement_date is in the last period
    """
    if coupon_frequency <= 0:
        return settlement_date
    step_months = 12 // coupon_frequency
    candidate = maturity_date
    periods_back = 1
    # Step back from maturity (not from the previous candidate) so that day clamping
    # in short months (e.g. 31 → 30) does not drift across iterations
    while (previous := _subtract_months(maturity_date, periods_back * step_months)) > settlement_date:
        candidate = previous
        periods_back += 1
    return candidate


def _subtract_months(d: date, months: int) -> date:
    """Subtract *months* calendar months from *d*, clamping the day to the target month length.

    Used by _generate_dates to step backward from maturity_date by the coupon
    period (12/coupon_frequency months) at each iteration.
    """
    total_months = d.year * 12 + (d.month - 1) - months
    year, month = divmod(total_months, 12)
    month += 1
    day = min(d.day, _days_in_month(year, month))
    return date(year, month, day)


def _days_in_month(year: int, month: int) -> int:
    """Number of days in year/month, used by _subtract_months to clamp the day
    (e.g. day 31 → 30/28/29) when the target month is shorter."""
    next_month = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return (next_month - date(year, month, 1)).days
