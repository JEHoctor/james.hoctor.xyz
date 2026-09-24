"""Guards on the meta descriptions this site puts in front of search engines.

Bing Webmaster Tools flags a description shorter than about 150 characters as too thin, and
truncates one longer than about 160. The site draws its descriptions from two places: the
per-page-type strings in pelicanconf.py, used for the home page and the listing pages, and an
optional `description` key in a post's front matter, used for that one page. Both are checked
here, so a new listing page or a hand-written description cannot quietly fall out of the window.

Articles without a `description` fall back to a truncation of their own summary in the theme's
article.html; that is not checked, because it depends on how much prose the post opens with.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from blog_automation import frontmatter as fm

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = REPO_ROOT / "content"

# The window search engines are comfortable with.
MIN_LENGTH = 150
MAX_LENGTH = 160

# The longest tag, category or author name that the interpolated descriptions are sized to hold.
# Nothing enforces this on new terms, so the templates leave headroom rather than sitting at 160.
SAMPLE_TERM = "example-term"

sys.path.insert(0, str(REPO_ROOT))
import pelicanconf  # noqa: E402


def _in_window(text: str) -> bool:
    return MIN_LENGTH <= len(text) <= MAX_LENGTH


@pytest.mark.parametrize("page_name", sorted(pelicanconf.META_DESCRIPTIONS))
def test_page_type_description_fits_the_window(page_name: str) -> None:
    """Each fixed per-page-type description is long enough to be useful and short enough to survive."""
    description = pelicanconf.META_DESCRIPTIONS[page_name]
    assert _in_window(description), f"{page_name}: {len(description)} characters"


def test_page_type_descriptions_are_all_different() -> None:
    """Identical descriptions across pages are their own SEO problem, and were the old behaviour."""
    descriptions = list(pelicanconf.META_DESCRIPTIONS.values())
    assert len(set(descriptions)) == len(descriptions)


@pytest.mark.parametrize(
    "name",
    ["TAG_META_DESCRIPTION", "CATEGORY_META_DESCRIPTION", "AUTHOR_META_DESCRIPTION"],
)
def test_interpolated_description_fits_the_window(name: str) -> None:
    """The tag, category and author templates must still fit once a realistic term is filled in."""
    rendered = getattr(pelicanconf, name).format(SAMPLE_TERM)
    assert _in_window(rendered), f"{name}: {len(rendered)} characters"


@pytest.mark.parametrize("path", sorted(CONTENT_DIR.rglob("*.md")), ids=lambda p: p.name)
def test_front_matter_description_fits_the_window(path: Path) -> None:
    """A description written by hand in a post's header is held to the same window."""
    description = fm.read(path).metadata.get("description")
    if description is None:
        pytest.skip("no description in this post's front matter")
    assert _in_window(str(description)), f"{path.name}: {len(str(description))} characters"


@pytest.mark.parametrize("path", sorted(CONTENT_DIR.rglob("*.md")), ids=lambda p: p.name)
def test_noindex_is_spelled_the_one_way_the_theme_recognises(path: Path) -> None:
    """A `noindex` key the theme does not recognise is worse than none: it reads as protection.

    base.html compares the value as a lowercased string against "true", precisely so that a
    quoted "False" does not pass a bare truthiness test. That makes any other spelling a silent
    no-op, which is the failure mode this guards.
    """
    metadata = fm.read(path).metadata
    if "noindex" not in metadata:
        pytest.skip("this post does not ask to be de-indexed")
    assert str(metadata["noindex"]).lower() == "true", (
        f'{path.name}: noindex is {metadata["noindex"]!r}; the theme only honours "True"'
    )
