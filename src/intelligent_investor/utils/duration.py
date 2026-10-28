# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
"""
Macaulay and modified duration of a fixed-rate coupon bond.

Mirrors DURATION and MDURATION of LibreOffice, used by the reference spreadsheet
(docs/ObbligazioniTF v5.0.ods, foglio `Bond`, cell K16). The remaining cash flows
are the coupons still to be paid plus the redemption at 100, discounted at the
given yield compounded coupon_frequency times a year. The first flow is a
fraction of a period away when settlement falls between two coupon dates.

The modified duration is the price sensitivity to the yield: if the yield rises by
1 percentage point, the tel quel price falls by about modified_duration %.
"""
from datetime import date

from intelligent_investor.utils.coupon_schedule import coupon_count
from intelligent_investor.utils.day_count import DayCountConvention

_REDEMPTION = 100.0


def macaulay_duration(
    settlement_date: date,
    maturity_date: date,
    nominal_rate: float,
    yield_pct: float,
    coupon_frequency: int,
    convention: DayCountConvention = DayCountConvention.THIRTY_360,
) -> float:
    """
    Macaulay duration in years, as DURATION(settlement; maturity; coupon; yield; frequency; basis).

    Each flow is weighted by its time in periods, t + shift, where shift places the
    first flow a fraction of a period after settlement:
        shift = year_fraction(settlement, maturity) × frequency − number of coupons
    (LibreOffice's GetDuration).

    Args:
        settlement_date: Purchase settlement date
        maturity_date: Bond maturity, the last coupon date
        nominal_rate: Annual coupon rate, in % (e.g. 3.35)
        yield_pct: Annual yield the flows are discounted at, in % (e.g. 3.0)
        coupon_frequency: Coupons per year (1, 2 or 4)
        convention: Day count of the year fraction (default 30/360, basis 0, as cell K16
                    which leaves the basis out)

    Returns:
        The duration in years

    Raises:
        ValueError: if the bond pays no coupons or settlement is not before maturity
    """
    if coupon_frequency <= 0:
        raise ValueError("duration needs a coupon frequency > 0")
    if settlement_date >= maturity_date:
        raise ValueError("settlement_date must be earlier than maturity_date")

    coupons = coupon_count(settlement_date, maturity_date, coupon_frequency)
    shift = convention.year_fraction(settlement_date, maturity_date) * coupon_frequency - coupons
    coupon = nominal_rate / coupon_frequency
    discount = 1 + yield_pct / 100 / coupon_frequency

    weighted = 0.0
    price = 0.0
    for t in range(1, coupons + 1):
        flow = coupon + (_REDEMPTION if t == coupons else 0.0)
        present_value = flow / discount ** (t + shift)
        weighted += (t + shift) * present_value
        price += present_value
    return weighted / price / coupon_frequency


def modified_duration(
    settlement_date: date,
    maturity_date: date,
    nominal_rate: float,
    yield_pct: float,
    coupon_frequency: int,
    convention: DayCountConvention = DayCountConvention.THIRTY_360,
) -> float:
    """
    Modified duration, as MDURATION(...): Macaulay duration / (1 + yield / frequency).

    Args and Raises: as macaulay_duration

    Returns:
        The modified duration (% change of the tel quel price for a 1-point change in yield)
    """
    macaulay = macaulay_duration(
        settlement_date, maturity_date, nominal_rate, yield_pct, coupon_frequency, convention
    )
    return macaulay / (1 + yield_pct / 100 / coupon_frequency)
