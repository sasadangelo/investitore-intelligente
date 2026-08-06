# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
from datetime import date
from enum import IntEnum


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
    US_30_360  = 0
    ACT_ACT    = 1
    ACT_360    = 2
    ACT_365    = 3
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


class YieldCalculator:
    """Compute annualised simple and compound (XIRR) yields for a fixed-income investment.

    All yield methods return a percentage value (e.g. 3.396 for 3.396%).

    Two distinct year-fraction conventions are used — matching LibreOffice/Excel:

    * **Simple yield** uses ``YEARFRAC(start, end, basis)`` (default ACT_ACT = basis 1).
      The denominator depends on whether 29-Feb falls in the period (<=1yr case)
      or on the average of spanned years (>1yr case).

    * **Compound yield (XIRR)** always uses ``days / 365`` regardless of basis.
      This matches Excel ``XIRR`` behaviour for two-cashflow investments and produces
      values identical to the ODS reference spreadsheet's TIR column.

    Args:
        start_date: Purchase / settlement date of the investment.
        end_date:   Maturity / sale date of the investment.
        basis:      Day-count convention for the *simple* year fraction
                    (default: ACT_ACT = LibreOffice/Excel basis 1).

    Usage — BOT calculator::

        yc = YieldCalculator(purchase_date, maturity_date)
        gross_simple   = yc.simple(gross_gain, dry_purchase)
        gross_compound = yc.compound(sale_dry, dry_purchase)
        net_simple     = yc.simple(net_gain, total_paid)
        net_compound   = yc.compound(net_redemption, total_paid)

    Usage — bond catalogue (qty=1)::

        yc = YieldCalculator(today, maturity_date)
        gross_yield = yc.compound(redemption_price, last_price)
        net_yield   = yc.compound(redemption_price - imposta_disaggio, last_price)
    """

    def __init__(
        self,
        start_date: date,
        end_date: date,
        basis: YearfracBasis = YearfracBasis.ACT_ACT,
    ) -> None:
        if start_date >= end_date:
            raise ValueError("end_date must be strictly after start_date")
        self._start = start_date
        self._end = end_date
        self._basis = basis
        self._yf_simple: float | None = None   # yearfrac(basis), lazy
        self._yf_xirr: float | None = None     # days/365, lazy

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def year_fraction(self) -> float:
        """Year fraction for simple yields: ``YEARFRAC(start, end, basis)``."""
        if self._yf_simple is None:
            self._yf_simple = yearfrac(self._start, self._end, self._basis)
        return self._yf_simple

    @property
    def year_fraction_xirr(self) -> float:
        """Year fraction for compound (XIRR) yields: ``days / 365`` (always)."""
        if self._yf_xirr is None:
            self._yf_xirr = (self._end - self._start).days / 365.0
        return self._yf_xirr

    def simple(self, gain: float, capital: float) -> float:
        """Annualised simple yield: ``(gain / capital) / year_fraction × 100``.

        Uses YEARFRAC with the chosen basis (default ACT_ACT).

        Args:
            gain:    Total gain over the holding period (e.g. net_gain, gross_gain).
            capital: Invested capital (e.g. dry_purchase, total_paid, last_price).

        Returns:
            Yield as a percentage (e.g. 3.396).
        """
        return gain / capital / self.year_fraction * 100

    def compound(self, final_proceeds: float, capital: float) -> float:
        """Annualised compound yield (XIRR): ``(final_proceeds/capital)^(365/days) − 1 × 100``.

        Replicates Excel/LibreOffice ``XIRR`` for a two-cashflow investment
        (−capital at start_date, +final_proceeds at end_date).
        Always uses ``days / 365`` as the time exponent, regardless of basis.

        Args:
            final_proceeds: Total amount received at maturity/sale
                            (e.g. sale_dry, net_redemption, redemption_price).
            capital:        Invested capital (e.g. dry_purchase, total_paid, last_price).

        Returns:
            Yield as a percentage (e.g. 3.399).
        """
        return (final_proceeds / capital) ** (1 / self.year_fraction_xirr) * 100 - 100


# ---------------------------------------------------------------------------
# Private helpers
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
