# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
"""
Guide service — reads Markdown files from the docs/guides/ directory,
parses YAML frontmatter, and converts the body to HTML.

Each guide file must start with a YAML frontmatter block:

    ---
    title: Titolo della guida
    description: Breve descrizione mostrata nell'indice
    icon: bi-book          # Bootstrap Icons class (optional, default: bi-book)
    order: 1               # Sort order in the index (optional, default: 99)
    ---

    # Corpo della guida in Markdown...
"""

from dataclasses import dataclass, field
from pathlib import Path

import markdown
import yaml

from intelligent_investor.core.log import LoggerManager

logger = LoggerManager.get_logger("GuideService")

# Absolute path to the guides directory
_GUIDES_DIR = Path(__file__).parent.parent.parent.parent / "docs" / "guides"

# Markdown extensions enabled
_MD_EXTENSIONS = [
    "extra",        # tables, fenced code, footnotes, …
    "toc",          # [TOC] macro + auto anchor ids on headings
    "sane_lists",   # better list handling
    "nl2br",        # newlines → <br>
]


@dataclass
class GuideMetadata:
    """Frontmatter fields for a single guide."""
    slug: str
    title: str
    description: str
    icon: str = "bi-book"
    order: int = 99


@dataclass
class Guide:
    """A fully-loaded guide with metadata and rendered HTML body."""
    meta: GuideMetadata
    html_content: str


class GuideService:
    """
    Reads and renders Markdown guides from docs/guides/.

    The directory is scanned on each call — no caching — so edits to .md
    files are reflected immediately without restarting the server.
    """

    def list_all(self) -> list[GuideMetadata]:
        """Return metadata for all guides, sorted by `order` then `title`."""
        guides = []
        for path in _GUIDES_DIR.glob("*.md"):
            try:
                meta = self._parse_frontmatter(path)
                guides.append(meta)
            except Exception as exc:
                logger.warning(f"Skipping {path.name}: {exc}")
        return sorted(guides, key=lambda g: (g.order, g.title))

    def get(self, slug: str) -> Guide | None:
        """Load and render a guide by slug (filename without .md). Returns None if not found."""
        path = _GUIDES_DIR / f"{slug}.md"
        if not path.exists():
            return None
        try:
            meta = self._parse_frontmatter(path)
            body = self._body(path)
            html = markdown.markdown(body, extensions=_MD_EXTENSIONS)
            return Guide(meta=meta, html_content=html)
        except Exception as exc:
            logger.error(f"Failed to render guide {slug}: {exc}")
            return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _raw(path: Path) -> str:
        return path.read_text(encoding="utf-8")

    def _parse_frontmatter(self, path: Path) -> GuideMetadata:
        """Extract YAML frontmatter and return a GuideMetadata instance."""
        raw = self._raw(path)
        if not raw.startswith("---"):
            raise ValueError("missing YAML frontmatter block")
        parts = raw.split("---", 2)
        if len(parts) < 3:
            raise ValueError("malformed YAML frontmatter")
        fm = yaml.safe_load(parts[1]) or {}
        return GuideMetadata(
            slug=path.stem,
            title=fm.get("title", path.stem),
            description=fm.get("description", ""),
            icon=fm.get("icon", "bi-book"),
            order=int(fm.get("order", 99)),
        )

    @staticmethod
    def _body(path: Path) -> str:
        """Return the Markdown body (everything after the closing --- of frontmatter)."""
        raw = path.read_text(encoding="utf-8")
        if raw.startswith("---"):
            parts = raw.split("---", 2)
            return parts[2].lstrip("\n") if len(parts) >= 3 else ""
        return raw
