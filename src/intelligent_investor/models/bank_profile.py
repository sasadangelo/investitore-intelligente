# -----------------------------------------------------------------------------
# Copyright (c) 2025 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from intelligent_investor.db.base import Base


class BankProfileDAO(Base):
    """Persists a bank + channel profile (e.g. "MPS — Internet Banking")."""

    __tablename__ = "bank_profile"

    id: Column[int] = Column(Integer, primary_key=True)
    bank_name: Column[str] = Column(String(length=100), nullable=False)
    profile_name: Column[str] = Column(String(length=100), nullable=False)
    notes: Column[str] = Column(String(length=500), nullable=True)
    info_url: Column[str] = Column(String(length=500), nullable=True)

    # One profile has many commission rows
    commissions = relationship(
        argument="BankCommissionDAO",
        back_populates="profile",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="BankCommissionDAO.venue, BankCommissionDAO.days_min",
    )


class BankCommissionDAO(Base):
    """Persists one commission schedule row for a BankProfile."""

    __tablename__ = "bank_commission"

    id: Column[int] = Column(Integer, primary_key=True)
    profile_id: Column[int] = Column(Integer, ForeignKey(column="bank_profile.id", ondelete="CASCADE"), nullable=False)

    venue: Column[str] = Column(String(length=10), nullable=False)  # 'asta' | 'mot'
    duration_type: Column[str] = Column(String(length=20), nullable=False, default="any")
    days_min: Column[int] = Column(Integer, nullable=True)
    days_max: Column[int] = Column(Integer, nullable=True)

    commission_pct = Column(Float, nullable=False, default=0.0)
    commission_min = Column(Float, nullable=False, default=0.0)
    commission_max = Column(Float, nullable=True)  # None = no cap
    commission_fixed = Column(Float, nullable=False, default=0.0)

    profile = relationship(argument="BankProfileDAO", back_populates="commissions")
