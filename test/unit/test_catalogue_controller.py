# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
"""
Unit tests for the column-header sort toggle in catalogue_controller.py.

Pure function — no DB, no Flask request context, no I/O.
"""

from intelligent_investor.controllers.catalogue_controller import _toggle_sort_dir


def test_toggle_sort_dir_flips_when_same_field() -> None:
    assert _toggle_sort_dir("maturity", "asc", "maturity") == "desc"
    assert _toggle_sort_dir("maturity", "desc", "maturity") == "asc"


def test_toggle_sort_dir_uses_field_default_when_switching_field() -> None:
    assert _toggle_sort_dir("maturity", "asc", "yield_gross") == "desc"
    assert _toggle_sort_dir("yield_gross", "desc", "maturity") == "asc"
