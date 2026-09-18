"""Guards on this repository's content tree, checked with the tools that publish it.

These are tests of the site rather than of the automation package, which is why they live here
and not under automation/tests: they read the real content/ directory.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from blog_automation import frontmatter as fm
from blog_automation import mirror

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = REPO_ROOT / "content"


@pytest.mark.parametrize("path", sorted(CONTENT_DIR.rglob("*.md")), ids=lambda p: p.name)
def test_every_real_post_round_trips_byte_for_byte(path: Path) -> None:
    """Parsing and re-rendering a real post must not change a single byte.

    This is what lets the CLI edit one key and leave the rest of a header alone.
    """
    text = path.read_text(encoding="utf-8")
    assert fm.render(fm.parse(text)) == text


def test_every_current_post_is_classified_and_drafts_outnumber_nothing_silently() -> None:
    """A regression guard against the incident: the real content tree must yield some withheld drafts.

    If every post suddenly reads as publishable, or none does, the parser and the headers have
    drifted apart again.
    """
    posts = sorted(p for p in (REPO_ROOT / "content").rglob("*.md"))
    statuses = {p.name: mirror.publication_status(p) for p in posts}
    assert all(isinstance(status, str) for status in statuses.values()), statuses
    assert "draft" in statuses.values()
    assert "published" in statuses.values()
