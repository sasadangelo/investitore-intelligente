# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

AuctionSession = Literal["bot", "medium_long", "short"]

# BTP Short auctions are always at month end; medium-long ones are mid-month and often
# also at month end (MEF calendar 2026: e.g. 13/10 and 29/10, 12/11 and 27/11)
SHORT_SESSION_PERIOD = "end_month"


class BotAuctionDTO(BaseModel):
    """
    Represents a scheduled auction from the annual MEF calendar: a BOT or a BTP one.

    session       : 'bot', 'medium_long' (auction of fixed-rate BTPs from 3 to 30/50
                    years, mid-month and often also at month end) or 'short'
                    (end-month auction of BTP Short Term).
                    These are auction sessions, not bond types. A BTP auction has
                    no duration or maturity of its own (duration_type 'tbd'): the
                    bonds offered are AuctionOfferingDTO entries.

    period        : 'mid_month' for the mid-month auction (typically annual BOTs),
                    'end_month' for the end-of-month auction (typically semi-annual).
    duration_type : 'annual' (365/366 days), 'semiannual' (182/183 days), or
                    'tbd' when the MEF has not yet announced the maturity.
    maturity_date : None when duration_type == 'tbd'.
    days          : read-only property — (maturity_date - settlement_date).days,
                    or None when maturity_date is None.
    """

    id: int | None = None

    session: AuctionSession = "bot"

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
        if self.session != "bot":
            if self.duration_type != "tbd":
                raise ValueError("a BTP auction has no duration of its own: duration_type must be 'tbd'")
            if self.session == "short" and self.period != SHORT_SESSION_PERIOD:
                raise ValueError("a BTP Short auction is held at month end")
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


class AuctionOfferingDTO(BaseModel):
    """
    A bond offered at a BTP auction, as announced by the MEF a few days before.

    isin          : the bond's ISIN; when it is in the catalogue the auction is a
                    reopening and the calendar links to it.
    maturity_date : None when not yet known.
    """

    id: int | None = None
    auction_id: int
    isin: str = Field(min_length=12, max_length=12)
    name: str = Field(min_length=1, max_length=100)
    maturity_date: date | None = None

    @field_validator("isin", mode="before")
    @classmethod
    def normalise_isin(cls, value: object) -> object:
        return value.strip().upper() if isinstance(value, str) else value

    model_config = ConfigDict(from_attributes=True)
