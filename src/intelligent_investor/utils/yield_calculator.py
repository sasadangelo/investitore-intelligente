# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
from datetime import date

from intelligent_investor.utils.day_count import DayCountConvention, YearfracBasis, yearfrac

__all__ = ["YearfracBasis", "YieldCalculator", "xirr", "yearfrac"]  # yearfrac re-exported from day_count


class YieldCalculator:
    """Compute annualised simple and compound (XIRR) yields for a fixed-income investment.

    All yield methods return a percentage value (e.g. 3.396 for 3.396%).

    Two distinct day-count conventions are used — matching LibreOffice/Excel —
    both taken from utils/day_count.py (BondConventions.simple_yield/compound_yield):

    * **Simple yield** uses ``YEARFRAC(start, end, basis)`` (default act/act = basis 1).
      The denominator depends on whether 29-Feb falls in the period (<=1yr case)
      or on the average of spanned years (>1yr case).

    * **Compound yield (XIRR)** uses ``days / 365`` (act/365), as Excel ``XIRR``
      always does, so values match the ODS reference spreadsheet's TIR column.

    Args:
        start_date:          Purchase / settlement date of the investment.
        end_date:            Maturity / sale date of the investment.
        simple_convention:   Day count of the *simple* year fraction (default act/act).
        compound_convention: Day count of the *compound* time exponent (default act/365).

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
        simple_convention: DayCountConvention = DayCountConvention.ACT_ACT,
        compound_convention: DayCountConvention = DayCountConvention.ACT_365,
    ) -> None:
        if start_date >= end_date:
            raise ValueError("end_date must be strictly after start_date")
        self._start = start_date
        self._end = end_date
        self._simple_convention = simple_convention
        self._compound_convention = compound_convention
        self._yf_simple: float | None = None   # simple_convention year fraction, lazy
        self._yf_xirr: float | None = None     # compound_convention year fraction, lazy

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def year_fraction(self) -> float:
        """Year fraction for simple yields: ``YEARFRAC(start, end, basis)`` of simple_convention."""
        if self._yf_simple is None:
            self._yf_simple = self._simple_convention.year_fraction(self._start, self._end)
        return self._yf_simple

    @property
    def year_fraction_xirr(self) -> float:
        """Year fraction for compound (XIRR) yields, in compound_convention (``days / 365`` by default)."""
        if self._yf_xirr is None:
            self._yf_xirr = self._compound_convention.year_fraction(self._start, self._end)
        return self._yf_xirr

    def simple(self, gain: float, capital: float) -> float:
        """Annualised simple yield: ``(gain / capital) / year_fraction × 100``.

        Uses YEARFRAC in simple_convention (default act/act).

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
        Uses year_fraction_xirr (``days / 365`` by default) as the time exponent.

        Args:
            final_proceeds: Total amount received at maturity/sale
                            (e.g. sale_dry, net_redemption, redemption_price).
            capital:        Invested capital (e.g. dry_purchase, total_paid, last_price).

        Returns:
            Yield as a percentage (e.g. 3.399).
        """
        return (final_proceeds / capital) ** (1 / self.year_fraction_xirr) * 100 - 100


def xirr(
    cashflows: list[tuple[date, float]],
    guess: float = 0.1,
    convention: DayCountConvention = DayCountConvention.ACT_365,
) -> float:
    """Annualised compound yield (XIRR) for a series of dated cash flows.

    Generalises ``YieldCalculator.compound()`` from a two-flow (purchase → final
    proceeds) formula to N dated flows — e.g. a BTP's purchase outflow, periodic
    net coupons, and final sale/redemption inflow. Uses the same ``days / 365``
    convention as ``YieldCalculator.year_fraction_xirr``, anchored to the earliest
    cash flow date, so it reduces to ``YieldCalculator.compound()`` for the
    two-flow case.

    Solved with Newton-Raphson starting from *guess*; falls back to bisection
    if Newton-Raphson fails to converge (e.g. poor initial guess, degenerate
    cash flow pattern).

    Args:
        cashflows: List of (date, amount) pairs, in any order. Outflows (e.g.
                   the purchase price) are negative, inflows (coupons, sale
                   proceeds, redemption) positive.
        guess:     Initial rate guess for Newton-Raphson (default 0.10 = 10%).
        convention: Day count of the time exponents (default act/365 = ``days / 365``,
                   as Excel XIRR).

    Returns:
        Annualised yield as a percentage (e.g. 3.399 for 3.399%), consistent
        with ``YieldCalculator.compound()``.

    Raises:
        ValueError: if cashflows has fewer than two entries, or all amounts
                    share the same sign (no rate can zero the NPV).
    """
    if len(cashflows) < 2:
        raise ValueError("xirr requires at least two cash flows")
    if not any(amount < 0 for _, amount in cashflows) or not any(amount > 0 for _, amount in cashflows):
        raise ValueError("xirr requires at least one negative and one positive cash flow")

    t0 = min(d for d, _ in cashflows)
    years = [convention.year_fraction(t0, d) for d, _ in cashflows]
    amounts = [amount for _, amount in cashflows]

    def npv(rate: float) -> float:
        return sum(a / (1.0 + rate) ** t for a, t in zip(amounts, years, strict=True))

    def dnpv(rate: float) -> float:
        return sum(
            -t * a / (1.0 + rate) ** (t + 1) for a, t in zip(amounts, years, strict=True) if t > 0
        )

    rate = guess
    for _ in range(100):
        f = npv(rate)
        df = dnpv(rate)
        if df == 0:
            break
        new_rate = rate - f / df
        if new_rate <= -1.0:
            break
        if abs(new_rate - rate) < 1e-10:
            return new_rate * 100
        rate = new_rate

    return _xirr_bisection(amounts, years) * 100


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _xirr_bisection(
    amounts: list[float],
    years: list[float],
    low: float = -0.999999,
    high: float = 10.0,
    tol: float = 1e-10,
    max_iter: int = 200,
) -> float:
    """Bisection fallback for ``xirr()`` when Newton-Raphson fails to converge.

    Expands *high* geometrically until the NPV changes sign between *low* and
    *high* (a root is bracketed), then bisects down to *tol*.
    """
    def npv(rate: float) -> float:
        return sum(a / (1.0 + rate) ** t for a, t in zip(amounts, years, strict=True))

    f_low = npv(low)
    f_high = npv(high)
    while f_low * f_high > 0 and high < 1e6:
        high *= 2
        f_high = npv(high)
    if f_low * f_high > 0:
        raise ValueError("xirr: could not bracket a root")

    for _ in range(max_iter):
        mid = (low + high) / 2
        f_mid = npv(mid)
        if abs(f_mid) < tol or (high - low) < tol:
            return mid
        if f_low * f_mid < 0:
            high = mid
            f_high = f_mid
        else:
            low = mid
            f_low = f_mid
    return (low + high) / 2
