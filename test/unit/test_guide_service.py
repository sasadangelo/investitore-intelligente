# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
"""
Unit tests for GuideService.

All tests use pytest's tmp_path fixture and monkey-patch the private
_GUIDES_DIR constant so no real docs/guides/ files are needed.
"""
from pathlib import Path

import pytest

import intelligent_investor.services.guide_service as _guide_module
from intelligent_investor.services.guide_service import GuideService

# ------------------------------------------------------------------
# Fixture: redirect _GUIDES_DIR to a tmp directory
# ------------------------------------------------------------------

FRONTMATTER = """\
---
title: Test Guide
description: A test guide
icon: bi-star
order: 1
---

# Hello

This is the body.
"""

MINIMAL_FRONTMATTER = """\
---
title: Minimal
description: Min desc
---

Body here.
"""


@pytest.fixture(autouse=True)
def patch_guides_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point GuideService at a temp directory for every test."""
    monkeypatch.setattr(_guide_module, "_GUIDES_DIR", tmp_path)
    return tmp_path


# ------------------------------------------------------------------
# list_all
# ------------------------------------------------------------------


def test_list_all_empty_dir(tmp_path: Path) -> None:
    assert GuideService().list_all() == []


def test_list_all_returns_one_guide(tmp_path: Path) -> None:
    (tmp_path / "test-guide.md").write_text(FRONTMATTER, encoding="utf-8")
    guides = GuideService().list_all()
    assert len(guides) == 1
    assert guides[0].slug == "test-guide"
    assert guides[0].title == "Test Guide"
    assert guides[0].icon == "bi-star"
    assert guides[0].order == 1


def test_list_all_sorted_by_order_then_title(tmp_path: Path) -> None:
    (tmp_path / "b.md").write_text(
        "---\ntitle: B Guide\ndescription: d\norder: 2\n---\nbody", encoding="utf-8"
    )
    (tmp_path / "a.md").write_text(
        "---\ntitle: A Guide\ndescription: d\norder: 1\n---\nbody", encoding="utf-8"
    )
    (tmp_path / "c.md").write_text(
        "---\ntitle: C Guide\ndescription: d\norder: 2\n---\nbody", encoding="utf-8"
    )
    guides = GuideService().list_all()
    assert [g.slug for g in guides] == ["a", "b", "c"]


def test_list_all_skips_malformed_file(tmp_path: Path) -> None:
    (tmp_path / "good.md").write_text(FRONTMATTER, encoding="utf-8")
    (tmp_path / "bad.md").write_text("no frontmatter here", encoding="utf-8")
    guides = GuideService().list_all()
    assert len(guides) == 1
    assert guides[0].slug == "good"


def test_list_all_default_icon_and_order(tmp_path: Path) -> None:
    (tmp_path / "minimal.md").write_text(MINIMAL_FRONTMATTER, encoding="utf-8")
    guides = GuideService().list_all()
    assert guides[0].icon == "bi-book"
    assert guides[0].order == 99


# ------------------------------------------------------------------
# get
# ------------------------------------------------------------------


def test_get_returns_none_for_missing_slug(tmp_path: Path) -> None:
    assert GuideService().get("nonexistent") is None


def test_get_returns_guide_with_html(tmp_path: Path) -> None:
    (tmp_path / "test-guide.md").write_text(FRONTMATTER, encoding="utf-8")
    guide = GuideService().get("test-guide")
    assert guide is not None
    assert guide.meta.slug == "test-guide"
    assert guide.meta.title == "Test Guide"
    assert "<h1" in guide.html_content
    assert "Hello" in guide.html_content


def test_get_body_excludes_frontmatter(tmp_path: Path) -> None:
    (tmp_path / "test-guide.md").write_text(FRONTMATTER, encoding="utf-8")
    guide = GuideService().get("test-guide")
    assert guide is not None
    # YAML keys must not appear in rendered HTML
    assert "bi-star" not in guide.html_content
    assert "icon:" not in guide.html_content


def test_get_returns_none_for_malformed_file(tmp_path: Path) -> None:
    (tmp_path / "bad.md").write_text("no frontmatter", encoding="utf-8")
    assert GuideService().get("bad") is None
