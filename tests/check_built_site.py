"""Checks on the built site in output/, run by `just validate` rather than by pytest.

These need a build, so they cannot live alongside the pytest modules here, which read only the
content tree. The filename deliberately does not start with `test_`, so pytest does not collect
it. CI runs it in the `validate` job, which has both the build artifact and the checkout.

It reads the rendered HTML, because that is what search engines see and what the config only
promises: a template edit or a page without a `description` can change a description without
touching any setting. The reasons behind each check are in "SEO: what the plugins actually do"
in CLAUDE.md. In short:

- output/robots.txt is content/extra/robots.txt, not the file the SEO plugin generates.
- Every URL in sitemap.xml has exactly one meta description, 150-160 characters long, and no
  two of them share one.
- Every published or hidden page whose front matter sets `noindex` carries the robots tag in
  its built HTML, and no page carrying that tag is listed in the sitemap.
"""

from __future__ import annotations

import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

from blog_automation import frontmatter as fm
from pelican.settings import DEFAULT_CONFIG
from pelican.utils import slugify

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "output"
CONTENT_DIR = REPO_ROOT / "content"
SOURCE_ROBOTS = CONTENT_DIR / "extra" / "robots.txt"
SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

# The window search engines are comfortable with; Bing flags shorter, and truncates longer.
MIN_LENGTH = 150
MAX_LENGTH = 160


class _MetaTags(HTMLParser):
    """Collects the attributes of every <meta> tag; attribute values arrive unescaped."""

    def __init__(self) -> None:
        super().__init__()
        self.tags: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "meta":
            self.tags.append({name.lower(): value or "" for name, value in attrs})


def meta_contents(path: Path, name: str) -> list[str]:
    """Return the content of every <meta name="..."> tag with this name in a built page."""
    parser = _MetaTags()
    parser.feed(path.read_text(encoding="utf-8"))
    return [tag.get("content", "") for tag in parser.tags if tag.get("name", "").lower() == name]


def is_noindexed(path: Path) -> bool:
    return any("noindex" in content.lower() for content in meta_contents(path, "robots"))


def output_path_for_url(url: str) -> str:
    """The file under output/ that serves a sitemap URL; a directory URL is its index.html."""
    path = urlparse(url).path.lstrip("/")
    if path == "" or path.endswith("/"):
        path += "index.html"
    return path


def check_robots_txt(problems: list[str]) -> None:
    built = OUTPUT_DIR / "robots.txt"
    if not built.is_file():
        problems.append("output/robots.txt is missing")
    elif built.read_text(encoding="utf-8") != SOURCE_ROBOTS.read_text(encoding="utf-8"):
        problems.append(
            "output/robots.txt differs from content/extra/robots.txt, so the SEO plugin's generated "
            "file (without our Disallow: /drafts/ and Sitemap: lines) is what would be deployed",
        )


def sitemap_pages(problems: list[str]) -> list[str] | None:
    """The output-relative path of every page the sitemap lists, or None if it cannot be read."""
    sitemap = OUTPUT_DIR / "sitemap.xml"
    if not sitemap.is_file():
        problems.append("output/sitemap.xml is missing")
        return None
    try:
        root = ET.parse(sitemap).getroot()
    except ET.ParseError as error:
        problems.append(f"output/sitemap.xml is not well-formed XML: {error}")
        return None
    pages = []
    for loc in root.findall("sm:url/sm:loc", SITEMAP_NS):
        page = output_path_for_url(loc.text or "")
        if (OUTPUT_DIR / page).is_file():
            pages.append(page)
        else:
            problems.append(f"sitemap.xml lists {loc.text}, but output/{page} does not exist")
    if not pages:
        problems.append("sitemap.xml lists no pages that exist in output/")
    return pages


def check_descriptions(problems: list[str], pages: list[str]) -> None:
    """One description per sitemap page, inside the window, and never shared with another page."""
    seen: dict[str, str] = {}
    for page in pages:
        descriptions = meta_contents(OUTPUT_DIR / page, "description")
        if len(descriptions) != 1:
            problems.append(f"{page} has {len(descriptions)} meta descriptions, not exactly one")
            continue
        description = descriptions[0]
        if not MIN_LENGTH <= len(description) <= MAX_LENGTH:
            problems.append(
                f"{page}: description is {len(description)} characters, outside "
                f"{MIN_LENGTH}-{MAX_LENGTH}: {description!r}",
            )
        if description in seen:
            problems.append(f"{page} has the same description as {seen[description]}: {description!r}")
        else:
            seen[description] = page


def check_noindex_and_sitemap_disagree(problems: list[str], pages: list[str]) -> None:
    problems.extend(
        f"{page} is listed in the sitemap but carries a noindex robots tag; add it to "
        f"SITEMAP['exclude'] in pelicanconf.py (patterns have no leading slash)"
        for page in pages
        if is_noindexed(OUTPUT_DIR / page)
    )


def built_page_for(source: Path, post: fm.Post) -> str:
    """Where Pelican writes a post or page, under this site's default URL settings."""
    if "save_as" in post.metadata:
        return str(post.metadata["save_as"])
    slug = str(post.metadata.get("slug") or "") or slugify(
        str(post.metadata.get("title", "")),
        regex_subs=DEFAULT_CONFIG["SLUG_REGEX_SUBSTITUTIONS"],
    )
    is_page = source.is_relative_to(CONTENT_DIR / "pages")
    return f"pages/{slug}.html" if is_page else f"{slug}.html"


def check_noindex_reaches_the_page(problems: list[str]) -> None:
    """A noindex request in front matter must turn into a robots tag in the built page."""
    for source in sorted(CONTENT_DIR.rglob("*.md")):
        post = fm.read(source)
        if str(post.metadata.get("noindex", "")).lower() != "true":
            continue
        if fm.status_of(post) not in {"published", "hidden"}:
            continue  # drafts are built under drafts/, which robots.txt disallows outright
        page = built_page_for(source, post)
        built = OUTPUT_DIR / page
        if not built.is_file():
            problems.append(f"{source.relative_to(REPO_ROOT)} sets noindex, but output/{page} does not exist")
        elif not is_noindexed(built):
            problems.append(f"{source.relative_to(REPO_ROOT)} sets noindex, but output/{page} has no robots tag")


def main() -> int:
    if not OUTPUT_DIR.is_dir():
        print("No output/ directory - run 'just publish' first", file=sys.stderr)
        return 1

    problems: list[str] = []
    check_robots_txt(problems)
    pages = sitemap_pages(problems)
    if pages is not None:
        check_descriptions(problems, pages)
        check_noindex_and_sitemap_disagree(problems, pages)
    check_noindex_reaches_the_page(problems)

    for problem in problems:
        print(f"check-built-site: {problem}", file=sys.stderr)
    if problems:
        return 1
    print(
        f"check-built-site: robots.txt is ours; {len(pages or [])} sitemap pages each have one unique "
        f"{MIN_LENGTH}-{MAX_LENGTH} character description; noindex pages are tagged and unlisted",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
