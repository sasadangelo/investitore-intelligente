# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
"""
Day-count conventions: how days between two dates are turned into time.

Every calculation that depends on elapsed time takes its convention from here,
even when it never changes for the bonds we handle, so the rules live in one place.

The conventions are the ones offered by the reference spreadsheet
(docs/ObbligazioniTF v5.0.ods, `Emissioni` columns P/Q, `Bond` cells E21/E22).
BOND_CONVENTIONS says which one each calculation uses for each bond type.
Conventions are per bond type, not per bond: every BOT and BTP uses the same
ones (see docs/roadmap-btp.md, "Convenzioni di calcolo dei giorni").
"""
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_FLOOR, Decimal
from enum import Enum, IntEnum


class YearfracBasis(IntEnum):
    """Day-count conventions for YEARFRAC, matching LibreOffice/Excel basis codes.

    Basis  Name        Calculation
    -----  ----------  -------------------------------------------------------
      0    US_30_360   US method (NASD): 12 months of 30 days each
      1    ACT_ACT     Exact days in month, exact days in year (actual/actual)
      2    ACT_360     Exact days in month, year has 360 days
      3    ACT_365     Exact days in month, year has 365 days (fixed)
      4    EUR_30_360  European method: 12 months of 30 days each
    """
    US_30_360 = 0
    ACT_ACT = 1
    ACT_360 = 2
    ACT_365 = 3
    EUR_30_360 = 4


def yearfrac(d1: date, d2: date, basis: YearfracBasis = YearfracBasis.ACT_ACT) -> float:
    """Return the year fraction between *d1* and *d2* using the given day-count basis.

    Mirrors ``YEARFRAC(d1; d2; basis)`` in LibreOffice/Excel.

    Args:
        d1:    Start date.
        d2:    End date.
        basis: Day-count convention (default: ACT_ACT = basis 1).

    Returns:
        Year fraction as a float (e.g. 0.9589 for 350 days on a 365-day year).
    """
    if d1 == d2:
        return 0.0
    if d1 > d2:
        d1, d2 = d2, d1

    if basis == YearfracBasis.ACT_ACT:
        return _yearfrac_act_act(d1, d2)
    elif basis == YearfracBasis.ACT_360:
        return (d2 - d1).days / 360.0
    elif basis == YearfracBasis.ACT_365:
        return (d2 - d1).days / 365.0
    elif basis in (YearfracBasis.US_30_360, YearfracBasis.EUR_30_360):
        return _yearfrac_30_360(d1, d2, european=(basis == YearfracBasis.EUR_30_360))
    else:
        raise ValueError(f"Unsupported basis: {basis}")


class DayCountConvention(str, Enum):
    """
    A day-count convention, named as in the reference spreadsheet.

    Value     Spreadsheet     Year fraction (YEARFRAC basis)
    --------  --------------  -----------------------------------------------------
    act/act   act/act         actual days / actual days of the year(s) (basis 1)
    act/360   Effettiva/360   actual days / 360 (basis 2)
    act/365   Effettiva/365   actual days / 365 (basis 3)
    30/360    30/360          months of 30 days, years of 360 (US method, basis 0)
    """

    ACT_ACT = "act/act"
    ACT_360 = "act/360"
    ACT_365 = "act/365"
    THIRTY_360 = "30/360"

    @property
    def yearfrac_basis(self) -> YearfracBasis:
        """The YEARFRAC basis code implementing this convention (cells F21/F22)."""
        return _YEARFRAC_BASIS[self]

    def year_fraction(self, d1: date, d2: date) -> float:
        """
        Years between d1 and d2, as YEARFRAC(d1; d2; basis).

        Args:
            d1: Start date
            d2: End date

        Returns:
            The year fraction (0.0 when the dates coincide)
        """
        return yearfrac(d1, d2, self.yearfrac_basis)

    def accrual_fraction(self, start: date, d: date, end: date) -> Decimal:
        """
        Share of the period start→end elapsed at d, between 0 and 1.

        With act/360 and act/365 the year length cancels out and the share is the
        exact ratio of actual days, (d − start) / (end − start), kept exact in
        Decimal so amounts derived from it round correctly to the cent.

        Args:
            start: Beginning of the period
            d: Date at which the share is measured
            end: End of the period (after start)

        Returns:
            The elapsed share
        """
        if self in (DayCountConvention.ACT_360, DayCountConvention.ACT_365):
            return Decimal((d - start).days) / Decimal((end - start).days)
        return Decimal(str(self.year_fraction(start, d))) / Decimal(str(self.year_fraction(start, end)))

    def accrued_coupon(
        self,
        nominal_rate: float,
        coupon_frequency: int,
        period_start: date,
        period_end: date,
        accrual_start: date,
        settlement_date: date,
        period_coupon: float | None = None,
    ) -> float:
        """
        Accrued interest (rateo) per 100 of nominal, as in the `Bond` sheet (cells F36/F52).

        act/act is the ICMA rule used for government bonds: the coupon of the period
        times the days elapsed over the days of the whole period, rounded down to the
        6th decimal. Every other convention takes the year fraction since the accrual
        start times the annual rate.

        Args:
            nominal_rate: Annual coupon rate, in % (e.g. 2.5)
            coupon_frequency: Coupons per year
            period_start: Coupon date opening the running period (may precede the issue date)
            period_end: Next coupon date
            accrual_start: Date interest starts accruing from (period_start, or the issue date if later)
            settlement_date: Date the rateo is computed at
            period_coupon: Coupon of the whole period start→end, in act/act only, when it is
                not the regular nominal_rate / coupon_frequency (a long first coupon,
                cell AJ32). None for a regular period

        Returns:
            The gross accrued interest per 100 of nominal
        """
        if self is DayCountConvention.ACT_ACT:
            elapsed_days = max(0, (settlement_date - accrual_start).days)
            coupon = (
                Decimal(str(nominal_rate)) / Decimal(coupon_frequency)
                if period_coupon is None
                else Decimal(str(period_coupon))
            )
            # Decimal so that exact values (e.g. 0.625) are not floored to 0.624999 by float error
            accrued = coupon * Decimal(elapsed_days) / Decimal((period_end - period_start).days)
            return float(accrued.quantize(Decimal("0.000001"), rounding=ROUND_FLOOR))
        return self.year_fraction(accrual_start, settlement_date) * nominal_rate


_YEARFRAC_BASIS: dict[DayCountConvention, YearfracBasis] = {
    DayCountConvention.ACT_ACT: YearfracBasis.ACT_ACT,
    DayCountConvention.ACT_360: YearfracBasis.ACT_360,
    DayCountConvention.ACT_365: YearfracBasis.ACT_365,
    DayCountConvention.THIRTY_360: YearfracBasis.US_30_360,
}


# ---------------------------------------------------------------------------
# YEARFRAC helpers
# ---------------------------------------------------------------------------


def _is_leap(y: int) -> bool:
    return (y % 4 == 0 and y % 100 != 0) or y % 400 == 0


def _yearfrac_act_act(d1: date, d2: date) -> float:
    """ACT/ACT (basis 1) — LibreOffice/Excel exact-days convention.

    * Period <= 1 year: denominator = 366 if 29-Feb falls strictly inside
      the period (d1 < 29-Feb <= d2), otherwise 365.
    * Period >  1 year: arithmetic mean of the lengths of every calendar year
      fully or partially spanned by the period.
    """
    total_days = (d2 - d1).days

    try:
        one_year_later = date(d1.year + 1, d1.month, d1.day)
    except ValueError:
        one_year_later = date(d1.year + 1, 3, 1)

    if d2 <= one_year_later:
        has_feb29 = False
        for y in (d1.year, d2.year):
            if _is_leap(y):
                feb29 = date(y, 2, 29)
                if d1 < feb29 <= d2:
                    has_feb29 = True
                    break
        denom: float = 366.0 if has_feb29 else 365.0
    else:
        years_spanned = range(d1.year, d2.year + 1)
        denom = sum(366.0 if _is_leap(y) else 365.0 for y in years_spanned) / len(years_spanned)

    return total_days / denom


def _yearfrac_30_360(d1: date, d2: date, european: bool) -> float:
    """30/360 convention (basis 0 = US/NASD, basis 4 = European)."""
    d1m, d1d = d1.month, d1.day
    d2m, d2d = d2.month, d2.day

    if european:
        if d1d == 31:
            d1d = 30
        if d2d == 31:
            d2d = 30
    else:
        if d2d == 31 and d1d >= 30:
            d2d = 30
        if d1d == 31:
            d1d = 30

    days = (d2.year - d1.year) * 360 + (d2m - d1m) * 30 + (d2d - d1d)
    return days / 360.0


@dataclass(frozen=True)
class BondConventions:
    """The day-count convention of each time-dependent calculation for one bond type."""

    # Rateo cedolare (cell F21, `Emissioni` column Q). Irrelevant for bonds without coupons.
    accrued_interest: DayCountConvention
    # How the issue discount (scarto di emissione) accrues between issue and maturity
    # (cell F22, `Emissioni` column P)
    issue_discount: DayCountConvention
    # Holding period of the simple yield (cell K15, always YEARFRAC basis 1)
    simple_yield: DayCountConvention
    # Time exponent of the compound yield (XIRR, which always counts days / 365)
    compound_yield: DayCountConvention


BOND_CONVENTIONS: dict[str, BondConventions] = {
    # BOT: no coupons; the discount accrues in proportion to actual days from issue to
    # maturity (cell F29 with F6 = 3, regardless of F22): the act/365 share is exactly
    # that ratio. Yields as in the sheet.
    "BOT": BondConventions(
        accrued_interest=DayCountConvention.ACT_ACT,
        issue_discount=DayCountConvention.ACT_365,
        simple_yield=DayCountConvention.ACT_ACT,
        compound_yield=DayCountConvention.ACT_365,
    ),
    # Fixed-rate BTP: act/act for both rateo and discount, as for every BTP in the
    # `Emissioni` sheet. Yields as in the sheet.
    "BTP": BondConventions(
        accrued_interest=DayCountConvention.ACT_ACT,
        issue_discount=DayCountConvention.ACT_ACT,
        simple_yield=DayCountConvention.ACT_ACT,
        compound_yield=DayCountConvention.ACT_365,
    ),
}


def conventions_for(bond_type: str) -> BondConventions:
    """
    Return the day-count conventions of a bond type.

    Args:
        bond_type: "BOT" or "BTP"

    Returns:
        The conventions of that bond type

    Raises:
        ValueError: if the bond type is not handled
    """
    try:
        return BOND_CONVENTIONS[bond_type]
    except KeyError:
        raise ValueError(f"Unsupported bond type: {bond_type!r} (supported: {', '.join(BOND_CONVENTIONS)})")
