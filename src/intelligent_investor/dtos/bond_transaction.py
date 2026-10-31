# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
"""
A bond purchase, an optional early sale and the account it is held in.

    TransactionDTO                one trade: settlement date, clean price, commissions
    ├── BuyTransactionDTO         + venue (asta/MOT) and nominal lot
    └── SellTransactionDTO        an early sale on the MOT

    BondTransactionDTO            what the calculator works on
    ├── buy:     BuyTransactionDTO
    ├── sell:    SellTransactionDTO | None   (None = held to maturity)
    └── account: AccountDTO                  (stamp duty, fee per coupon, zainetto)

Shared by BOTs and fixed-rate BTPs: the transaction is the same, only the bond
differs. Coupon schedule and accrued interest (rateo), when the bond has coupons,
are derived from the bond's own record (bond_id), not from this transaction.
"""
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class TransactionDTO(BaseModel):
    """
    One trade of the bond: when it settles, at which clean price, with which commissions.

    The commission is commission_pct of commission_base(), clamped to
    [commission_min, commission_max], plus commission_fixed.
    """

    date: date                                  # settlement date
    price: float = Field(gt=0)                  # clean price per 100 of nominal (e.g. 96.524)

    commission_pct: float = 0.0                 # % of commission_base()
    commission_min: float = 0.0                 # minimum commission in €
    commission_max: float | None = None         # maximum commission in € — None = no cap
    commission_fixed: float = 0.0               # additional fixed fee in € (e.g. 3.50)

    def commission_base(self, dry_amount: float) -> float:
        """Amount the commission percentage applies to: by default the clean amount traded."""
        return dry_amount


class BuyTransactionDTO(TransactionDTO):
    """The purchase: at auction or on the MOT, of a nominal lot."""

    venue: Literal["asta", "mot"]
    face_value: float                           # nominal lot in € (e.g. 5000.0)

    @model_validator(mode="after")
    def check_face_value(self) -> "BuyTransactionDTO":
        if self.face_value <= 0 or self.face_value % 100 != 0:
            raise ValueError("face_value must be a positive multiple of 100")
        return self

    def commission_base(self, dry_amount: float) -> float:
        """At auction the commission is a share of the nominal lot (cell A26), on the MOT of the clean amount."""
        return self.face_value if self.venue == "asta" else dry_amount

    @property
    def quantity(self) -> float:
        """Number of units purchased (face_value / 100)."""
        return self.face_value / 100


class SellTransactionDTO(TransactionDTO):
    """An early sale on the MOT, of the whole lot; the commission is a share of the clean amount (cell A44)."""


class AccountDTO(BaseModel):
    """What depends on the account the bond is held in, not on a single trade."""

    stamp_duty_period: Literal["annual", "quarterly"] = "quarterly"
    portfolio_losses: float = 0.0               # capital losses in the zainetto fiscale
    coupon_fee: float = 0.0                     # fixed fee in € charged at every coupon cashed (cell K44)


class BondTransactionDTO(BaseModel):
    """A purchase of a bond, its optional early sale and the account it is held in."""

    bond_id: int  # 0 is used as sentinel for manually-entered (non-DB) bonds
    buy: BuyTransactionDTO
    sell: SellTransactionDTO | None = None      # None = held to maturity
    account: AccountDTO = Field(default_factory=AccountDTO)

    @model_validator(mode="after")
    def check_dates(self) -> "BondTransactionDTO":
        if self.sell is not None and self.sell.date <= self.buy.date:
            raise ValueError("the sale date must be later than the purchase date")
        return self

    @property
    def quantity(self) -> float:
        """Number of units bought, and sold if there is an early sale (the whole lot)."""
        return self.buy.quantity

    @property
    def holds_to_maturity(self) -> bool:
        """True when no early sale is planned."""
        return self.sell is None

    @classmethod
    def from_flat(
        cls,
        *,
        bond_id: int,
        purchase_venue: Literal["asta", "mot"],
        purchase_date: date,
        purchase_price: float,
        face_value: float,
        buy_commission_pct: float = 0.0,
        buy_commission_min: float = 0.0,
        buy_commission_max: float | None = None,
        buy_commission_fixed: float = 0.0,
        sale_date: date | None = None,
        sale_price: float | None = None,
        sell_commission_pct: float = 0.0,
        sell_commission_min: float = 0.0,
        sell_commission_max: float | None = None,
        sell_commission_fixed: float = 0.0,
        stamp_duty_period: Literal["annual", "quarterly"] = "quarterly",
        portfolio_losses: float = 0.0,
        coupon_fee: float = 0.0,
    ) -> "BondTransactionDTO":
        """
        Build a transaction from the flat field names of the calculator form and of the
        reference test cases (test/unit/fixtures).

        Raises:
            ValueError: if only one of sale_date and sale_price is given, or the data is inconsistent
        """
        if (sale_date is None) != (sale_price is None):
            raise ValueError("sale_date and sale_price must both be present or both be absent")
        sell = None
        if sale_date is not None and sale_price is not None:
            sell = SellTransactionDTO(
                date=sale_date,
                price=sale_price,
                commission_pct=sell_commission_pct,
                commission_min=sell_commission_min,
                commission_max=sell_commission_max,
                commission_fixed=sell_commission_fixed,
            )
        return cls(
            bond_id=bond_id,
            buy=BuyTransactionDTO(
                venue=purchase_venue,
                date=purchase_date,
                price=purchase_price,
                face_value=face_value,
                commission_pct=buy_commission_pct,
                commission_min=buy_commission_min,
                commission_max=buy_commission_max,
                commission_fixed=buy_commission_fixed,
            ),
            sell=sell,
            account=AccountDTO(
                stamp_duty_period=stamp_duty_period, portfolio_losses=portfolio_losses, coupon_fee=coupon_fee
            ),
        )
