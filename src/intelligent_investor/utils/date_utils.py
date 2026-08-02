# -----------------------------------------------------------------------------
# Copyright (c) 2025 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
from datetime import date


def yearfrac_act_act(d1: date, d2: date) -> float:
    """Return the year fraction between *d1* and *d2* using Excel YEARFRAC basis 1.

    Excel basis 1 (actual/actual) computes::

        days(d1, d2) / average_year_length

    where *average_year_length* is the arithmetic mean of the lengths (365 or
    366 days) of all calendar years spanned by the period.  This matches the
    formula used by the reference spreadsheet's ``YEARFRAC(purchase, maturity, 1)``
    call stored in cell K15 of the Bond sheet.

    For example, for 2024-04-12 → 2025-04-14 (367 days, spanning leap year 2024
    and regular year 2025)::

        average = (366 + 365) / 2 = 365.5
        result  = 367 / 365.5 ≈ 1.004104

    Falls back to ``days / 365`` for same-day input (prevents division by zero).
    """
    if d1 == d2:
        return 1.0  # avoid division-by-zero; caller ensures days >= 1 anyway

    if d1 > d2:
        d1, d2 = d2, d1

    def _year_days(y: int) -> int:
        return 366 if (y % 4 == 0 and y % 100 != 0) or y % 400 == 0 else 365

    total_days = (d2 - d1).days
    years_spanned = range(d1.year, d2.year + 1)
    avg_year = sum(_year_days(y) for y in years_spanned) / len(years_spanned)
    return total_days / avg_year
