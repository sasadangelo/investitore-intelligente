# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
"""
In-memory pagination of an already sorted list, reusable by any list page.
"""
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class Page(Generic[T]):
    """One page of a list, with the information needed to render the pager."""

    items: list[T]
    number: int  # 1-indexed, always within [1, total_pages]
    per_page: int
    total_items: int

    @property
    def total_pages(self) -> int:
        """Number of pages; an empty list still has one (empty) page."""
        return max(1, -(-self.total_items // self.per_page))  # ceil division


def paginate(items: Sequence[T], page: int, per_page: int) -> Page[T]:
    """
    Slice *items* to the given 1-indexed *page*.

    Args:
        items: Full (already sorted) list
        page: Requested page, clamped to the valid range
        per_page: Page size, must be positive

    Returns:
        The requested page

    Raises:
        ValueError: if per_page is not positive
    """
    if per_page <= 0:
        raise ValueError(f"per_page must be positive, got {per_page}")
    total_pages = max(1, -(-len(items) // per_page))
    number = min(max(1, page), total_pages)
    start = (number - 1) * per_page
    return Page(items=list(items[start : start + per_page]), number=number, per_page=per_page, total_items=len(items))
