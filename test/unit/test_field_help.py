# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
"""
Unit tests for the field help of templates/_help.html.

A key used with info('...') but missing from HELP would render an empty popover
without any error, so every key used in the templates must have a text.
"""
import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

_TEMPLATES = Path(__file__).parents[2] / "src" / "intelligent_investor" / "templates"
_USE = re.compile(r"""info\(\s*'([a-z0-9_]+)'\s*\)|help\s*=\s*'([a-z0-9_]+)'|sort_th\([^)]*,\s*'([a-z0-9_]+)'\s*\)""")


def _help_texts() -> dict[str, str]:
    module = Environment(loader=FileSystemLoader(_TEMPLATES)).get_template("_help.html").module
    return module.HELP  # type: ignore[attr-defined]


def _used_keys() -> set[str]:
    keys: set[str] = set()
    for path in _TEMPLATES.rglob("*.html"):
        for match in _USE.finditer(path.read_text(encoding="utf-8")):
            keys.update(k for k in match.groups() if k)
    return keys


def test_every_used_key_has_a_text() -> None:
    used = _used_keys()
    assert used, "no info() call found: the pattern no longer matches the templates"
    assert used - set(_help_texts()) == set()


def test_every_text_is_used() -> None:
    assert set(_help_texts()) - _used_keys() == set()


def test_info_renders_a_popover_with_the_text() -> None:
    env = Environment(loader=FileSystemLoader(_TEMPLATES), autoescape=True)
    html = env.from_string('{% from "_help.html" import info %}{{ info("duration") }}').render()

    assert 'data-bs-toggle="popover"' in html
    assert "prezzo scende di circa questa percentuale" in html
    assert "dell&#39;1%" in html  # apostrophes escaped inside the attribute
