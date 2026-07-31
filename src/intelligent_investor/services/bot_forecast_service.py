# -----------------------------------------------------------------------------
# Copyright (c) 2025 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
"""
BOT issue-price forecast service.

Method: weighted-average implied yield from active BOT market prices.

For each future auction with a known duration type (annual / semiannual):
  1. Collect all active BOTs of the same duration group that have a last_price.
  2. For each such BOT compute the annualised gross yield implied by last_price:
         r_i = (100 / last_price_i) ^ (365 / days_to_maturity_i) - 1
  3. Compute the weighted average yield, weighting by days_to_maturity
     (longer-dated BOTs are closer to the target duration and receive more weight):
         r_avg = sum(r_i * days_i) / sum(days_i)
  4. Derive the estimated issue price for the target duration (days_target):
         price_est = 100 / (1 + r_avg * days_target / 365)
  5. Derive gross and net annualised yields from price_est:
         gross = (100 / price_est) ^ (365 / days_target) - 1
         net   = ((100 - tax_on_discount) / price_est) ^ (365 / days_target) - 1
     where tax_on_discount = (100 - price_est) * 0.125

A minimum of MIN_BONDS bonds with valid quotes is required; otherwise the
forecast is marked as unavailable.
"""

from dataclasses import dataclass
from datetime import date

from intelligent_investor.core.log import LoggerManager
from intelligent_investor.dtos.bond import BondDTO
from intelligent_investor.dtos.bond_quote import BondQuoteDTO
from intelligent_investor.dtos.bot_auction import BotAuctionDTO
from intelligent_investor.services.bond_quote_service import BondQuoteService
from intelligent_investor.services.bond_service import BondService
from intelligent_investor.services.bot_auction_service import BotAuctionService

logger = LoggerManager.get_logger("BotForecastService")

# Minimum number of active BOTs with quotes needed to compute a forecast
MIN_BONDS = 2

# Duration group boundaries (days from settlement to maturity)
ANNUAL_MIN_DAYS = 271
SEMIANNUAL_MAX_DAYS = 270

# Italian withholding tax rate on government bond discount
DISCOUNT_TAX_RATE = 0.125


@dataclass
class BondDataPoint:
    """One active BOT used as input to the forecast."""

    name: str
    days_to_maturity: int
    last_price: float
    implied_yield: float  # annualised gross yield, as a fraction (e.g. 0.0245)
    weight: float  # relative weight in the weighted average


@dataclass
class BotForecastResult:
    """Forecast result for a single future auction."""

    auction: BotAuctionDTO
    days_target: int  # days from settlement to maturity
    data_points: list[BondDataPoint]  # bonds used for the estimate
    available: bool  # False when not enough data

    # Populated only when available is True
    estimated_price: float | None = None
    gross_yield_pct: float | None = None
    net_yield_pct: float | None = None
    avg_implied_yield_pct: float | None = None


def _is_leap(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def _year_days(ref_date: date) -> int:
    return 366 if _is_leap(ref_date.year) else 365


def _implied_gross_yield(last_price: float, days_to_maturity: int) -> float:
    """Annualised gross yield implied by last_price for a zero-coupon bond."""
    if days_to_maturity <= 0 or last_price <= 0:
        return 0.0
    return (100.0 / last_price) ** (365.0 / days_to_maturity) - 1.0


def _duration_group(days: int) -> str:
    """Map bond duration to 'annual' or 'semiannual'."""
    return "annual" if days >= ANNUAL_MIN_DAYS else "semiannual"


class BotForecastService:
    """Compute issue-price forecasts for upcoming BOT auctions."""

    def __init__(self) -> None:
        self._bond_svc = BondService()
        self._quote_svc = BondQuoteService()
        self._auction_svc = BotAuctionService()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def forecast_all(self) -> list[BotForecastResult]:
        """
        Return a forecast result for every future auction that has a known
        duration type (annual or semiannual).  Auctions with duration_type='tbd'
        are included but marked as unavailable.
        """
        today = date.today()
        auctions = sorted(
            [a for a in self._auction_svc.list_all() if a.settlement_date >= today],
            key=lambda a: a.auction_date,
        )
        bonds = self._bond_svc.list_all()
        quotes: dict[int, BondQuoteDTO] = {q.bond_id: q for q in self._quote_svc.list_all()}
        active_bonds = [b for b in bonds if b.maturity_date and b.maturity_date >= today]

        results = []
        for auction in auctions:
            results.append(self._forecast_one(auction, active_bonds, quotes, today))
        return results

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _forecast_one(
        self,
        auction: BotAuctionDTO,
        active_bonds: list[BondDTO],
        quotes: dict[int, BondQuoteDTO],
        today: date,
    ) -> BotForecastResult:
        """Compute the forecast for a single auction."""

        # tbd auctions: duration unknown, cannot forecast
        if auction.duration_type == "tbd" or auction.maturity_date is None or auction.days is None:
            return BotForecastResult(
                auction=auction,
                days_target=0,
                data_points=[],
                available=False,
            )

        days_target = auction.days
        target_group = auction.duration_type  # 'annual' or 'semiannual'

        # Collect active BOTs of the same duration group with a valid quote
        data_points: list[BondDataPoint] = []
        for bond in active_bonds:
            if bond.id is None:
                continue
            quote = quotes.get(bond.id)
            if quote is None or quote.last_price <= 0:
                continue
            bond_days_total = (bond.maturity_date - bond.issue_date).days
            if _duration_group(bond_days_total) != target_group:
                continue
            days_to_maturity = (bond.maturity_date - today).days
            if days_to_maturity <= 0:
                continue
            implied = _implied_gross_yield(quote.last_price, days_to_maturity)
            data_points.append(
                BondDataPoint(
                    name=bond.name,
                    days_to_maturity=days_to_maturity,
                    last_price=quote.last_price,
                    implied_yield=implied,
                    weight=days_to_maturity,  # filled with absolute value, normalised below
                )
            )

        if len(data_points) < MIN_BONDS:
            return BotForecastResult(
                auction=auction,
                days_target=days_target,
                data_points=data_points,
                available=False,
            )

        # Sort by days_to_maturity descending (most days first)
        data_points.sort(key=lambda dp: dp.days_to_maturity, reverse=True)

        # Normalise weights
        total_weight = sum(dp.days_to_maturity for dp in data_points)
        for dp in data_points:
            dp.weight = dp.days_to_maturity / total_weight

        # Weighted average implied yield
        r_avg = sum(dp.implied_yield * dp.weight for dp in data_points)

        # Estimated issue price
        price_est = 100.0 / (1.0 + r_avg * days_target / 365.0)

        # Gross annualised yield from estimated price
        gross = (100.0 / price_est) ** (365.0 / days_target) - 1.0

        # Net yield: deduct withholding tax on discount from redemption
        discount = 100.0 - price_est
        tax_on_discount = discount * DISCOUNT_TAX_RATE
        net = ((100.0 - tax_on_discount) / price_est) ** (365.0 / days_target) - 1.0

        logger.info(
            f"Forecast {auction.auction_date} {auction.duration_type}: "
            f"price={price_est:.4f}  gross={gross * 100:.3f}%  net={net * 100:.3f}%  "
            f"n={len(data_points)}"
        )

        return BotForecastResult(
            auction=auction,
            days_target=days_target,
            data_points=data_points,
            available=True,
            estimated_price=round(price_est, 4),
            gross_yield_pct=round(gross * 100, 3),
            net_yield_pct=round(net * 100, 3),
            avg_implied_yield_pct=round(r_avg * 100, 3),
        )
