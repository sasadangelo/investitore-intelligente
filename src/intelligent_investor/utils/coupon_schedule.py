# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
"""
Coupon schedule and accrued-interest utilities for fixed-rate coupon bonds (BTP).

Reusable by both the BTP calculator (Fase 4) and the bond catalogue (Fase 6).
coupon_frequency=0 (zero-coupon, e.g. BOT) is treated as a no-coupon degenerate
case throughout: schedules are empty and accrued interest is always 0.0.
"""
from dataclasses import dataclass
from datetime import date

from intelligent_investor.utils.yield_calculator import YearfracBasis, yearfrac


@dataclass(frozen=True)
class CouponPayment:
    """A single coupon stacco: payment date + gross/net amount per 100 of nominal."""

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
        tax_rate:         Withholding tax on coupons/rateo, in % (default 12.5).

    Usage — BTP calculator::

        cs = CouponSchedule(bond.issue_date, bond.maturity_date, bond.coupon_frequency,
                             bond.nominal_rate, bond.tax_rate)
        rateo_lordo = cs.accrued_interest(purchase_date)
        rateo_netto = cs.net_accrued_interest(purchase_date)
        piano_cedole = cs.schedule
    """

    def __init__(
        self,
        issue_date: date,
        maturity_date: date,
        coupon_frequency: int,
        nominal_rate: float,
        tax_rate: float = 12.5,
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
        self._dates: list[date] | None = None  # lazy cache

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def dates(self) -> list[date]:
        """
        Ascending list of coupon stacco dates in (issue_date, maturity_date].

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
        """Gross coupon paid per 100 of nominal at each stacco (0.0 if coupon_frequency == 0)."""
        if self._coupon_frequency <= 0:
            return 0.0
        return self._nominal_rate / self._coupon_frequency

    @property
    def net_coupon_amount(self) -> float:
        """Net coupon paid per 100 of nominal at each stacco, after withholding tax_rate%."""
        return self.gross_coupon_amount * (1 - self._tax_rate / 100)

    @property
    def schedule(self) -> list[CouponPayment]:
        """
        Full coupon plan from issue to maturity: one CouponPayment per stacco
        date, with gross/net amount per 100 of nominal (constant across
        stacchi, since the coupon is fixed-rate). Empty for coupon_frequency == 0.
        """
        gross = self.gross_coupon_amount
        net = self.net_coupon_amount
        return [CouponPayment(payment_date=d, gross_amount=gross, net_amount=net) for d in self.dates]

    def previous_coupon_date(self, settlement_date: date) -> date:
        """
        Return the last coupon stacco date on or before settlement_date.

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
        Gross accrued interest (rateo cedolare lordo) at settlement_date, per
        100 of nominal: the quota of the running coupon matured since the
        last stacco (or since issue_date, if no coupon has been paid yet),
        using ACT/ACT (yearfrac basis 1) — same convention as
        YieldCalculator's simple yield.

        Returns 0.0 when coupon_frequency == 0 (zero-coupon bonds have no rateo).
        """
        if self._coupon_frequency <= 0:
            return 0.0
        last = self.previous_coupon_date(settlement_date)
        return self._nominal_rate * yearfrac(last, settlement_date, YearfracBasis.ACT_ACT)

    def net_accrued_interest(self, settlement_date: date) -> float:
        """Net accrued interest (rateo cedolare netto) at settlement_date, after withholding tax_rate%."""
        return self.accrued_interest(settlement_date) * (1 - self._tax_rate / 100)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _generate_dates(self) -> list[date]:
        if self._coupon_frequency <= 0:
            return []
        step_months = 12 // self._coupon_frequency
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


def _subtract_months(d: date, months: int) -> date:
    """Subtract *months* calendar months from *d*, clamping the day to the target month length."""
    total_months = d.year * 12 + (d.month - 1) - months
    year, month = divmod(total_months, 12)
    month += 1
    day = min(d.day, _days_in_month(year, month))
    return date(year, month, day)


def _days_in_month(year: int, month: int) -> int:
    next_month = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return (next_month - date(year, month, 1)).days
