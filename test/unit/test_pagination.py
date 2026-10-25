# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
"""
Unit tests for utils/pagination.py.

Pure functions — no DB, no Flask request context, no I/O.
"""

import pytest

from intelligent_investor.utils.pagination import paginate


def test_paginate_slices_and_reports_total_pages() -> None:
    page = paginate(list(range(25)), page=2, per_page=10)
    assert page.items == list(range(10, 20))
    assert page.number == 2
    assert page.total_pages == 3
    assert page.total_items == 25


def test_paginate_clamps_page_above_range() -> None:
    page = paginate(list(range(5)), page=99, per_page=10)
    assert page.number == 1
    assert page.total_pages == 1
    assert page.items == [0, 1, 2, 3, 4]


def test_paginate_clamps_page_below_range() -> None:
    page = paginate(list(range(5)), page=0, per_page=10)
    assert page.number == 1
    assert page.items == [0, 1, 2, 3, 4]


def test_paginate_last_page_is_partial() -> None:
    page = paginate(list(range(25)), page=3, per_page=10)
    assert page.items == list(range(20, 25))


def test_paginate_empty_list_returns_single_empty_page() -> None:
    page = paginate([], page=1, per_page=20)
    assert page.items == []
    assert page.number == 1
    assert page.total_pages == 1


def test_paginate_rejects_non_positive_per_page() -> None:
    with pytest.raises(ValueError):
        paginate([1, 2, 3], page=1, per_page=0)
