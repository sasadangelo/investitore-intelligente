# -----------------------------------------------------------------------------
# Copyright (c) 2025 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator


class BotAuctionDTO(BaseModel):
    """
    Represents a scheduled BOT auction entry from the annual MEF calendar.

    period        : 'mid_month' for the mid-month auction (typically annual BOTs),
                    'end_month' for the end-of-month auction (typically semi-annual).
    duration_type : 'annual' (365/366 days), 'semiannual' (182/183 days), or
                    'tbd' when the MEF has not yet announced the maturity.
    maturity_date : None when duration_type == 'tbd'.
    days          : read-only property — (maturity_date - settlement_date).days,
                    or None when maturity_date is None.
    """

    id: int | None = None

    # Auction identity
    period: Literal["mid_month", "end_month"]
    duration_type: Literal["annual", "semiannual", "tbd"]

    # Key dates
    announcement_date: date       # market announcement date
    submission_deadline: date     # deadline for submitting bids
    auction_date: date            # auction execution date
    settlement_date: date         # settlement / value date
    maturity_date: date | None    # redemption date — None when tbd

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------

    @model_validator(mode="after")
    def check_dates(self) -> "BotAuctionDTO":
        if not (self.announcement_date <= self.submission_deadline <= self.auction_date <= self.settlement_date):
            raise ValueError(
                "dates must follow the order: announcement ≤ submission ≤ auction ≤ settlement"
            )
        if self.maturity_date is not None and self.maturity_date <= self.settlement_date:
            raise ValueError("maturity_date must be after settlement_date")
        if self.duration_type == "tbd" and self.maturity_date is not None:
            raise ValueError("maturity_date must be None when duration_type is 'tbd'")
        if self.duration_type != "tbd" and self.maturity_date is None:
            raise ValueError("maturity_date is required when duration_type is not 'tbd'")
        return self

    # ------------------------------------------------------------------
    # Derived helpers (read-only, not persisted)
    # ------------------------------------------------------------------

    @property
    def days(self) -> int | None:
        """Number of days from settlement to maturity. None when maturity is unknown."""
        if self.maturity_date is None:
            return None
        return (self.maturity_date - self.settlement_date).days

    @property
    def is_past(self) -> bool:
        """True when the settlement date is strictly in the past."""
        return self.settlement_date < date.today()

    model_config = ConfigDict(from_attributes=True)
