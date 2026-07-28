# -----------------------------------------------------------------------------
# Copyright (c) 2025 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
from datetime import date

from sqlalchemy import Column, Date, Integer, String

from intelligent_investor.db.base import Base


class BotAuctionDAO(Base):
    """
    Persists a BOT auction calendar entry.

    maturity_date is nullable to accommodate 'tbd' entries where the MEF
    has not yet announced the redemption date.
    days is intentionally excluded: it is always derivable from
    (maturity_date - settlement_date) and is exposed as a DTO property.
    """

    __tablename__ = "bot_auction"

    id: Column[int] = Column(Integer, primary_key=True)

    # Auction identity
    period: Column[str] = Column(String(20), nullable=False)         # 'mid_month' | 'end_month'
    duration_type: Column[str] = Column(String(20), nullable=False)  # 'annual' | 'semiannual' | 'tbd'

    # Key dates
    announcement_date: Column[date] = Column(Date, nullable=False)
    submission_deadline: Column[date] = Column(Date, nullable=False)
    auction_date: Column[date] = Column(Date, nullable=False)
    settlement_date: Column[date] = Column(Date, nullable=False)
    maturity_date: Column[date] = Column(Date, nullable=True)        # None when tbd
