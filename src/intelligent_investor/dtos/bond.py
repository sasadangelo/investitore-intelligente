# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
from datetime import date, timedelta

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

    # Optional stored link to the MEF auction result PDF.
    # When empty/None the UI falls back to the computed formula via mef_auction_result_url.
    auction_result_url: str | None = None

    model_config = ConfigDict(from_attributes=True)

    @property
    def mef_auction_result_url(self) -> str | None:
        """
        Return the stored auction_result_url if present, otherwise derive it
        automatically from issue_date / maturity_date.

        The MEF publishes results under:
          https://www.dt.mef.gov.it/export/sites/sitodt/modules/documenti_it/
            debito_pubblico/risultati_aste/risultati_aste_bot_{folder}/
            BOT-{label}-Risultati-Asta-{D1}-{D2}.{MM}.{YYYY}.pdf

        Where:
          settlement_date = issue_date (value date of the bond)
          D2              = settlement_date - 1 day (auction date)
          D1              = settlement_date - 2 days (announcement date)
          duration        = (maturity_date - issue_date).days
          folder/label    = '6_mesi' / '6-Mesi'   when duration <= 200 days
                          = 'annuali' / 'Annuale'  otherwise

        Only applies to BOT bonds.
        """
        if self.auction_result_url:  # non-empty/non-None string wins over auto-computed
            return self.auction_result_url
        if self.bond_type != "BOT":
            return None
        settlement = self.issue_date
        d2 = settlement - timedelta(days=1)
        d1 = settlement - timedelta(days=2)
        duration = (self.maturity_date - self.issue_date).days
        if duration <= 200:
            folder = "6_mesi"
            label = "6-Mesi"
        else:
            folder = "annuali"
            label = "Annuale"
        filename = (
            f"BOT-{label}-Risultati-Asta-"
            f"{d1.day:02d}-{d2.day:02d}.{d2.month:02d}.{d2.year}.pdf"
        )
        base = "https://www.dt.mef.gov.it/export/sites/sitodt/modules/documenti_it"
        return f"{base}/debito_pubblico/risultati_aste/risultati_aste_bot_{folder}/{filename}"
