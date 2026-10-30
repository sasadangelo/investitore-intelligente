# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
from datetime import date
from typing import Literal

from pydantic import BaseModel, model_validator


class BondTransactionDTO(BaseModel):
    """
    Represents a bond purchase (and optional early sale) entered by the user
    to compute the net gain, yields, capital gain/loss and stamp duty.

    Shared by BOTs and fixed-rate BTPs: the transaction is the same, only the
    bond differs. Coupon schedule and accrued interest (rateo), when the bond
    has coupons, are derived from the bond's own record (bond_id), not from
    this transaction.

    Purchase venue
    --------------
    purchase_venue controls how the buy commission percentage is applied:
      - "asta": % is applied on the face value (nominal price = 100)
      - "mot" : % is applied on purchase_price; min/max caps and a fixed fee
                may also apply.

    Sale (optional)
    ---------------
    If sale_date and sale_price are both None the bond is assumed to be held
    to maturity (sale_price defaults to redemption_price = 100).
    Both fields must be either both present or both absent.
    """

    bond_id: int  # 0 is used as sentinel for manually-entered (non-DB) bonds

    # --- Purchase ---
    purchase_venue: Literal["asta", "mot"]
    purchase_date: date                         # settlement date of the purchase
    purchase_price: float                       # clean price per 100 of nominal (e.g. 96.524)
    face_value: float                           # nominal lot in Euro (e.g. 5000.0)

    buy_commission_pct: float = 0.0             # % on face value (asta) or on purchase amount (mot)
    buy_commission_min: float = 0.0             # minimum commission — mot only
    buy_commission_max: float | None = None     # maximum commission — None = no cap, mot only
    buy_commission_fixed: float = 0.0           # additional fixed fee (e.g. 3.50 €)

    # --- Sale (optional) ---
    sale_date: date | None = None               # settlement date of the sale
    sale_price: float | None = None             # clean price per 100 of nominal at sale

    sell_commission_pct: float = 0.0            # % on sale amount
    sell_commission_min: float = 0.0            # minimum commission
    sell_commission_max: float | None = None    # maximum commission — None = no cap
    sell_commission_fixed: float = 0.0          # additional fixed fee

    # --- Bank parameters ---
    stamp_duty_period: Literal["annual", "quarterly"] = "quarterly"
    portfolio_losses: float = 0.0               # capital losses in the fiscal backpack
    coupon_fee: float = 0.0                     # fixed fee in € charged at every coupon cashed (cell K44)

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------

    @model_validator(mode="after")
    def check_consistency(self) -> "BondTransactionDTO":
        if self.face_value <= 0 or self.face_value % 100 != 0:
            raise ValueError("face_value must be a positive multiple of 100")

        if self.purchase_price <= 0:
            raise ValueError("purchase_price must be positive")

        if (self.sale_date is None) != (self.sale_price is None):
            raise ValueError(
                "sale_date and sale_price must both be present or both be absent"
            )

        if self.sale_date is not None and self.sale_date <= self.purchase_date:
            raise ValueError("sale_date must be later than purchase_date")

        return self

    # ------------------------------------------------------------------
    # Derived helpers (read-only, not persisted)
    # ------------------------------------------------------------------

    @property
    def quantity(self) -> float:
        """Number of units purchased (face_value / 100)."""
        return self.face_value / 100

    @property
    def holds_to_maturity(self) -> bool:
        """True when no early sale is planned."""
        return self.sale_date is None
