# -----------------------------------------------------------------------------
# Copyright (c) 2025 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
from datetime import date

from pydantic import BaseModel, ConfigDict, model_validator


class BondDTO(BaseModel):
    """
    Represents a fixed-income security (BOT, BTP, Corporate Bond) as a data
    transfer object. purchase_price is intentionally excluded: it belongs to a
    future Transaction/Portfolio entity.
    """

    # Core identifiers
    id: int | None = None
    name: str                          # e.g. "Bot Zc Jul25 A Eur"
    isin: str                          # e.g. "IT0005603342"
    bond_type: str                     # 'BOT', 'BTP', 'BTP_ITALIA', 'CORPORATE'

    # Key financial dates
    issue_date: date
    maturity_date: date

    @model_validator(mode="after")
    def check_dates(self) -> "BondDTO":
        if self.issue_date >= self.maturity_date:
            raise ValueError("issue_date must be earlier than maturity_date")
        return self

    # Price parameters
    issue_price: float                 # Price at issuance
    redemption_price: float = 100.0   # Reimbursement price at maturity (usually 100.0)

    # Coupon parameters (0 for BOTs/zero coupons, active for BTPs)
    nominal_rate: float = 0.0         # Annual coupon % (e.g. 3.5)
    coupon_frequency: int = 0         # 0=Zero Coupon, 1=Annual, 2=Semi-annual

    # Fiscal regime
    tax_rate: float = 12.5            # 12.5 govt bonds, 26.0 corporate

    model_config = ConfigDict(from_attributes=True)
