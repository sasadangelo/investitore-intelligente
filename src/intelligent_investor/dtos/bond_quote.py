# -----------------------------------------------------------------------------
# Copyright (c) 2025 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
from datetime import date, datetime
from typing import Annotated

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


class BondQuoteDTO(BaseModel):
    """Represents a daily bond market quote."""

    id: int | None = None
    bond_id: int
    # Accept 'date' (from callers/JSON) or 'quote_date' (from ORM attribute).
    date: Annotated[date, Field(validation_alias=AliasChoices("date", "quote_date"))]
    last_price: float
    var_percent: float

    # Parse 'dd/mm/yyyy' strings into Python date objects
    @field_validator("date", mode="before")
    @classmethod
    def parse_date(cls, value):
        if isinstance(value, str):
            return datetime.strptime(value, "%d/%m/%Y").date()
        return value

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
