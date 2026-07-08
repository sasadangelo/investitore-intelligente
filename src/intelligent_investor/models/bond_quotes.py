# -----------------------------------------------------------------------------
# Copyright (c) 2025 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
from datetime import date

from sqlalchemy import Column, Date, Float, ForeignKey, Integer
from sqlalchemy.orm import relationship

from intelligent_investor.db.base import Base


class BondQuoteDAO(Base):
    """
    Represents the single, most recent market quote for a specific Bond.
    Historical tracking is skipped to focus purely on current investment yield analysis.
    """

    __tablename__ = "bond_quote"

    id: Column[int] = Column(Integer, primary_key=True)
    bond_id: Column[int] = Column(
        Integer,
        ForeignKey(column="bond.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # Enforces a strict 1:1 relationship (one current quote per bond)
    )

    quote_date: Column[date] = Column(Date, nullable=False, default=date.today)  # Quote date
    last_price = Column(Float, nullable=False)    # Last traded price
    var_percent = Column(Float, nullable=False)   # Daily percentage variation

    bond = relationship(argument="BondDAO", back_populates="quotes")
