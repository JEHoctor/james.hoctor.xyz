"""Checks on the built site in output/, run by `just validate` rather than by pytest.

These need a build, so they cannot live alongside the pytest modules here, which read only the
content tree. The filename deliberately does not start with `test_`, so pytest does not collect
it. CI runs it in the `validate` job, which has both the build artifact and the checkout.

What it guards, and why each one is not obvious from the code:

robots.txt
    The SEO plugin writes its own robots.txt on the `all_generators_finalized` signal, which
    fires before static files are copied, so content/extra/robots.txt lands on top of it. That
    ordering is the only thing keeping the plugin's non-standard `Noindex:` lines out of the
    deployed file, and nothing in the plugin lets us turn its robots.txt off without also losing
    the canonical tags. If the ordering ever changes, this is where it shows up.

noindex versus the sitemap
    A sitemap entry asks a crawler to index a URL; `<meta name="robots" content="noindex">` asks
    it not to. A page must not do both. The sitemap plugin matches its `exclude` patterns against
    the URL relative to the output root, with no leading slash, so a pattern written with one
    silently matches nothing -- which is how `^/drafts/` sat in the config doing nothing.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "output"
SOURCE_ROBOTS = REPO_ROOT / "content" / "extra" / "robots.txt"
SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

ROBOTS_META = re.compile(r"<meta\b[^>]*\bname=\"robots\"[^>]*>", re.IGNORECASE)


def _fail(problems: list[str], message: str) -> None:
    problems.append(message)


def check_robots_txt(problems: list[str]) -> None:
    """The deployed robots.txt must be ours, not the one the SEO plugin generates."""
    built = OUTPUT_DIR / "robots.txt"
    if not built.is_file():
        _fail(problems, "output/robots.txt is missing")
        return

    built_text = built.read_text(encoding="utf-8")
    if built_text != SOURCE_ROBOTS.read_text(encoding="utf-8"):
        _fail(
            problems,
            "output/robots.txt differs from content/extra/robots.txt, so the SEO plugin's "
            "generated file is what would be deployed",
        )
    if re.search(r"^Noindex:", built_text, re.MULTILINE):
        _fail(
            problems,
            "output/robots.txt carries a non-standard 'Noindex:' line; Google dropped support "
            "in 2019 and Bing never had it",
        )


def _noindexed_urls() -> set[str]:
    """Return the output-relative URL of every built page asking not to be indexed."""
    urls = set()
    for path in OUTPUT_DIR.rglob("*.html"):
        tag = ROBOTS_META.search(path.read_text(encoding="utf-8"))
        if tag and "noindex" in tag.group(0).lower():
            urls.add(path.relative_to(OUTPUT_DIR).as_posix())
    return urls


def check_sitemap_agrees_with_noindex(problems: list[str]) -> None:
    """No URL may be advertised in the sitemap and de-indexed on the page itself."""
    sitemap = OUTPUT_DIR / "sitemap.xml"
    if not sitemap.is_file():
        _fail(problems, "output/sitemap.xml is missing")
        return

    try:
        root = ET.parse(sitemap).getroot()
    except ET.ParseError as error:
        _fail(problems, f"output/sitemap.xml is not well-formed XML: {error}")
        return

    listed = {(loc.text or "").split("/", 3)[-1] for loc in root.findall("sm:url/sm:loc", SITEMAP_NS)}
    for url in sorted(listed & _noindexed_urls()):
        _fail(
            problems,
            f"{url} is listed in the sitemap but carries a noindex robots tag; add it to "
            f"SITEMAP['exclude'] in pelicanconf.py (patterns have no leading slash)",
        )


def main() -> int:
    if not OUTPUT_DIR.is_dir():
        print("No output/ directory - run 'just publish' first", file=sys.stderr)
        return 1

    problems: list[str] = []
    check_robots_txt(problems)
    check_sitemap_agrees_with_noindex(problems)

    for problem in problems:
        print(f"check-built-site: {problem}", file=sys.stderr)
    if problems:
        return 1
    print("check-built-site: robots.txt and sitemap.xml agree with the built pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
