# -----------------------------------------------------------------------------
# Copyright (c) 2025 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
from datetime import date
from typing import Any

from sqlalchemy import Column, Date, Float, Integer, String
from sqlalchemy.orm import relationship

from .base import Base


class BondDAO(Base):
    """
    Represents a fixed-income security (BOT, BTP, Corporate Bond) stored in the database.
    purchase_price is intentionally excluded: it belongs to a future Transaction/Portfolio entity.
    """

    __tablename__ = "bond"

    # Core identifiers
    id: Column[int] = Column(Integer, primary_key=True)
    name: Column[str] = Column(String(length=100), unique=True, nullable=False)   # e.g. "Bot Zc Jul25 A Eur"
    isin: Column[str] = Column(String(length=20), unique=True, nullable=False)    # e.g. "IT0005603342"
    bond_type: Column[str] = Column(String(length=20), nullable=False)  # 'BOT', 'BTP', 'BTP_ITALIA', 'CORPORATE'

    # Key financial dates
    issue_date: Column[date] = Column(Date, nullable=False)
    maturity_date: Column[date] = Column(Date, nullable=False)

    # Price parameters
    issue_price = Column(Float, nullable=False)                        # Price at issuance
    redemption_price = Column(Float, nullable=False, default=100.0)    # Usually 100.0

    # Coupon parameters (0 for BOTs/zero coupons, active for BTPs)
    nominal_rate: Column[Any] = Column(Float, nullable=False, default=0.0)      # Annual coupon % (e.g. 3.5)
    coupon_frequency: Column[int] = Column(Integer, nullable=False, default=0)  # 0=Zero Coupon, 1=Annual, 2=Semi-annual

    # Fiscal regime
    tax_rate = Column(Float, nullable=False, default=12.5)             # 12.5 govt bonds, 26.0 corporate

    # One-to-many relationship with BondQuoteDAO
    quotes = relationship(
        argument="BondQuoteDAO",
        back_populates="bond",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
