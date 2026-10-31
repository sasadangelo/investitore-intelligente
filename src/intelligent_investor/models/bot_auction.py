# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
from datetime import date

from sqlalchemy import Column, Date, ForeignKey, Integer, String

from intelligent_investor.db.base import Base


class BotAuctionDAO(Base):
    """
    Persists an auction calendar entry: a BOT auction or a BTP one.

    The table keeps its historical name; session says which MEF auction it is.
    A BTP auction has no maturity of its own: the bonds offered, known only from
    the MEF announcement, are AuctionOfferingDAO rows.

    maturity_date is nullable to accommodate 'tbd' entries where the MEF
    has not yet announced the redemption date.
    days is intentionally excluded: it is always derivable from
    (maturity_date - settlement_date) and is exposed as a DTO property.
    """

    __tablename__ = "bot_auction"

    id: Column[int] = Column(Integer, primary_key=True)

    # MEF auction session: 'bot' | 'medium_long' (mid-month BTPs) | 'short' (end-month BTP Short)
    session: Column[str] = Column(String(20), nullable=False, default="bot")

    # Auction identity
    period: Column[str] = Column(String(20), nullable=False)         # 'mid_month' | 'end_month'
    duration_type: Column[str] = Column(String(20), nullable=False)  # 'annual' | 'semiannual' | 'tbd'

    # Key dates
    announcement_date: Column[date] = Column(Date, nullable=False)
    submission_deadline: Column[date] = Column(Date, nullable=False)
    auction_date: Column[date] = Column(Date, nullable=False)
    settlement_date: Column[date] = Column(Date, nullable=False)
    maturity_date: Column[date] = Column(Date, nullable=True)        # None when tbd


class AuctionOfferingDAO(Base):
    """
    Persists one bond offered at a BTP auction, as announced by the MEF.

    The link to the catalogue is resolved by ISIN when the calendar is shown, so a
    reopening points to the bond in the archive and a new bond needs no archive entry.
    """

    __tablename__ = "auction_offering"

    id: Column[int] = Column(Integer, primary_key=True)
    auction_id: Column[int] = Column(
        Integer, ForeignKey(column="bot_auction.id", ondelete="CASCADE"), nullable=False
    )
    isin: Column[str] = Column(String(12), nullable=False)
    name: Column[str] = Column(String(100), nullable=False)
    maturity_date: Column[date] = Column(Date, nullable=True)  # None when not yet known
