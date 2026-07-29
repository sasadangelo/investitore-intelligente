# -----------------------------------------------------------------------------
# Copyright (c) 2025 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
from typing import Literal

from pydantic import BaseModel, ConfigDict, computed_field, model_validator


class BankProfileDTO(BaseModel):
    """
    Represents a bank + channel combination (e.g. "MPS — Internet Banking").

    bank_name    : official bank name (e.g. "Monte dei Paschi di Siena")
    profile_name : channel or tier (e.g. "Internet Banking", "Filiale", "Phone Banking")
    notes        : optional free-text notes (e.g. disclaimer, last verified date)
    """

    id: int | None = None
    bank_name: str
    profile_name: str
    notes: str | None = None
    info_url: str | None = None

    @computed_field
    @property
    def display_name(self) -> str:
        """Short label shown in dropdowns: "<bank> — <profile>"."""
        return f"{self.bank_name} — {self.profile_name}"

    model_config = ConfigDict(from_attributes=True)


class BankCommissionDTO(BaseModel):
    """
    Commission schedule for one venue/duration combination within a BankProfile.

    venue         : 'asta' (primary market) or 'mot' (secondary market).
    duration_type : 'any' when the same rates apply to all durations (most MOT profiles),
                    or 'annual' / 'semiannual' / 'quarterly' for duration-specific rates.
    days_min      : lower bound of the holding-days range (inclusive). None = no lower bound.
    days_max      : upper bound of the holding-days range (inclusive). None = no upper bound.
                    Both None  → matches any duration (used together with duration_type='any').
                    Only used for auction ('asta') profiles where MEF caps vary by days:
                        None–80   → 0.03%
                        81–140    → 0.05%
                        141–270   → 0.10%
                        271–None  → 0.15%
    commission_pct   : percentage applied on face value (asta) or purchase amount (mot).
    commission_min   : minimum commission in EUR (0 for asta profiles).
    commission_max   : maximum commission in EUR. None = no cap (N.P.).
    commission_fixed : fixed fee in EUR added on top of the percentage
                       (e.g. €5.00 dossier fee for MPS asta, €3.50 intermediation for Intesa MOT).
    """

    id: int | None = None
    profile_id: int

    venue: Literal["asta", "mot"]
    duration_type: Literal["any", "annual", "semiannual", "quarterly"] = "any"

    # Days range — both None means "matches any number of days"
    days_min: int | None = None
    days_max: int | None = None

    commission_pct: float = 0.0
    commission_min: float = 0.0
    commission_max: float | None = None   # None = no cap
    commission_fixed: float = 0.0

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------

    @model_validator(mode="after")
    def check_days_range(self) -> "BankCommissionDTO":
        if self.days_min is not None and self.days_max is not None:
            if self.days_min > self.days_max:
                raise ValueError("days_min must be <= days_max")
        return self

    def matches_days(self, days: int | None) -> bool:
        """
        Return True if the given number of days falls within this commission's range.
        When days is None (tbd auction), only an unconstrained row (both None) matches.
        """
        if days is None:
            return self.days_min is None and self.days_max is None
        if self.days_min is not None and days < self.days_min:
            return False
        if self.days_max is not None and days > self.days_max:
            return False
        return True

    model_config = ConfigDict(from_attributes=True)
