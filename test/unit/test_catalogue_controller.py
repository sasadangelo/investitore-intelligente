# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
"""
Unit tests for the pure helpers of catalogue_controller.py: the column-header sort
toggle and the parsing of the "Parametri avanzati" query parameters.

No DB, no Flask request context, no I/O.
"""

import pytest
from werkzeug.datastructures import MultiDict

from intelligent_investor.controllers.catalogue_controller import _read_costs, _toggle_sort_dir
from intelligent_investor.services.catalogue_service import PurchaseCosts


def test_toggle_sort_dir_flips_when_same_field() -> None:
    assert _toggle_sort_dir("maturity", "asc", "maturity") == "desc"
    assert _toggle_sort_dir("maturity", "desc", "maturity") == "asc"


def test_toggle_sort_dir_uses_field_default_when_switching_field() -> None:
    assert _toggle_sort_dir("maturity", "asc", "yield_gross") == "desc"
    assert _toggle_sort_dir("yield_gross", "desc", "maturity") == "asc"


def test_read_costs_inactive_without_lot() -> None:
    costs, params = _read_costs(MultiDict({"commission_pct": "0.19", "sort": "maturity"}))

    assert costs is None
    assert params == {"commission_pct": "0.19"}  # still carried over in the links


def test_read_costs_parses_fields_and_blank_means_default() -> None:
    blank = {"commission_min": "", "commission_max": "", "bank_profile_id": ""}
    args = MultiDict({"face_value": "5000", "commission_pct": "0,19", **blank})

    costs, params = _read_costs(args)

    assert costs == PurchaseCosts(face_value=5000, commission_pct=0.19, commission_max=None, bank_profile_id=None)
    assert params == {"face_value": "5000", "commission_pct": "0,19"}


def test_read_costs_with_bank_profile_and_cap() -> None:
    costs, _ = _read_costs(MultiDict({"face_value": "10000", "bank_profile_id": "4", "commission_max": "19"}))

    assert costs is not None
    assert costs.bank_profile_id == 4
    assert costs.commission_max == 19.0


@pytest.mark.parametrize(
    "args",
    [
        {"face_value": "abc"},
        {"face_value": "150"},  # not a multiple of 100
        {"face_value": "0"},
        {"face_value": "1000", "commission_pct": "-1"},
        {"face_value": "1000", "bank_profile_id": "x"},
    ],
)
def test_read_costs_rejects_invalid_values(args: dict[str, str]) -> None:
    with pytest.raises(ValueError):
        _read_costs(MultiDict(args))
