import hashlib
from pathlib import Path

import pypandoc

AUTHOR = "James Hoctor"
SITENAME = "James Hoctor"
SITEURL = "https://james.hoctor.xyz"
SITESUBTITLE = "machine learning engineer"

PATH = "content"

# Markdown is converted by pandoc (via pelican-pandoc-reader) rather than Python-Markdown.
# The pandoc binary comes from the pypandoc-binary wheel so that no system pandoc is needed;
# the conversion settings live in pandoc-config/defaults.yaml. Posts may keep a BibTeX file next
# to them (content/<slug>.bib); it is picked up automatically as that post's bibliography.
PANDOC_EXECUTABLE_PATH = pypandoc.get_pandoc_path()
PANDOC_DEFAULTS_FILES = [str(Path(__file__).parent / "pandoc-config" / "defaults.yaml")]

# Bibliographies live next to their posts, but they are not content.
IGNORE_FILES = [".#*", "*.bib"]

# Name the plugins explicitly. Left unset, Pelican loads every installed pelican.plugins.* package,
# and `uv run` does not uninstall packages a previous branch needed, so a stale .venv would silently
# add (or crash on) plugins this branch never asked for.
PLUGINS = [
    "pelican.plugins.pandoc_reader",
    "pelican.plugins.seo",
    "pelican.plugins.sitemap",
]

TIMEZONE = "America/New_York"

DEFAULT_LANG = "en"

THEME = "hyde-personalized"

# Meta descriptions. Search engines want roughly 150-160 characters, and want them to differ
# from page to page; the theme's old fallback (SITENAME + BIO) was 96 characters and identical
# on every listing page, which is what Bing Webmaster Tools flagged. Articles build their own
# description from their summary (see the theme's article.html), and pages may set `description`
# in their front matter. Everything else is keyed here by the `page_name` Pelican passes to its
# direct templates, and base.html chooses between them. tests/check_built_site.py (run by
# `just validate`) holds every page in sitemap.xml to the window and to a unique description.
#
# These describe what is published, not what the blog may cover one day: no topic belongs here
# until a published post covers it. `blog post publish` reminds whoever publishes a post to
# reread them, and private/blog-scope.md says why.
#
# The paginated pages (the home page and the per-tag, per-category and per-author pages) get
# " Page N." appended from page 2 on, so that each page stays distinct from page 1. Their
# strings, with the current term filled in, are kept to 152 characters so the suffix still fits.
META_DESCRIPTIONS = {
    "index": (
        "James Hoctor is a machine learning engineer and data scientist. He writes here about "
        "self-hosting and Linux, Python tooling, 3D printing and some math."
    ),
    "archives": (
        "Every post on James Hoctor's blog by date: self-hosting with Caddy, rsync and Certbot, "
        "Python tooling with uv, a package on PyPI, 3D printing and some math."
    ),
    "tags": (
        "The tags used on James Hoctor's blog, each linking to the posts that carry it. Not every "
        "post is tagged; the archives page lists everything published so far."
    ),
    "categories": (
        "The categories on James Hoctor's blog, each linking to the posts filed under it, from "
        "notes on self-hosting and Linux to Python tooling, 3D printing and math."
    ),
    "authors": (
        "The authors of posts on james.hoctor.xyz. James Hoctor, a machine learning engineer and "
        "data scientist, writes about self-hosting, Python tooling and math."
    ),
}

# Per-term listing pages interpolate the tag, category or author name, so their length depends
# on the term; a new term that pushes one out of the window fails `just validate`.
TAG_META_DESCRIPTION = (
    "Posts tagged {} on James Hoctor's blog, newest first, each with its date and opening "
    "paragraph. Every post, tagged or not, is listed in the archives."
)
CATEGORY_META_DESCRIPTION = (
    "Posts in the {} category on James Hoctor's blog, newest first, each shown with its date "
    "and opening paragraph and a link through to the full article."
)
AUTHOR_META_DESCRIPTION = (
    "Posts by {}, newest first. He is a machine learning engineer and data scientist writing "
    "about self-hosting and Linux, Python tooling and math."
)

# Settings specific to the theme
BIO = "Machine learning engineer and data scientist. <nobr>BS Mathematics</nobr>, <nobr>MS Computer Science.</nobr>"
PROFILE_IMAGE = "github-profile.jpg"
COLOR_THEME = "08"

# Settings specific to my fork of the theme
FAVICON_DIR = "static"
APPLE_MOBILE_WEB_APP_TITLE = "James H"


def hashed_theme_asset(path: str) -> str:
    """Return a theme static path with a hash of its content appended as a query string.

    Cloudflare and browsers hold /theme/ files for hours under their URL, while HTML is not cached,
    so a URL that changes with the file's bytes reaches readers as soon as the page does. The theme's
    files are copied to the output unchanged, so these bytes are the ones deployed. A missing file
    raises, and that fails the build.
    """
    digest = hashlib.sha256((Path(__file__).resolve().parent / THEME / "static" / path).read_bytes())
    return f"{path}?v={digest.hexdigest()[:12]}"


JINJA_FILTERS = {"hashed_theme_asset": hashed_theme_asset}

# Tell Pelican that content/static/ should be copied to the output. The default is just content/images/.
# extra/robots.txt is placed at the output root (below) to override the one pelican-seo generates, since
# pelican-seo can only add per-document rules and we need a blanket "Disallow: /drafts/".
STATIC_PATHS = ["images", "static", "extra/robots.txt"]
EXTRA_PATH_METADATA = {"extra/robots.txt": {"path": "robots.txt"}}

# Feed generation is usually not desired when developing
FEED_ALL_ATOM = None
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None

# Link to "about me" page
DISPLAY_PAGES_ON_MENU = (("about", "about.md"),)

# Blogroll
LINKS = ()

# Social widget
SOCIAL = (
    ("github", "https://github.com/JEHoctor/"),
    ("file-pdf-o", "https://drive.google.com/file/d/1dtkw-Jbo9DwJQrXAMmUa1jVqRovOlD3d/view?usp=share_link"),  # Resume
    ("linkedin", "https://www.linkedin.com/in/james-hoctor/"),
    ("thingiverse", "https://www.thingiverse.com/jehoctor/designs/"),
    ("python", "https://pypi.org/user/jehoctor/"),  # PyPI
)

DEFAULT_PAGINATION = 10

# Uncomment following line if you want document-relative URLs when developing
RELATIVE_URLS = True

# Development configuration for Pelican SEO plugin
SEO_REPORT = True
SEO_ENHANCER = True
SEO_ENHANCER_OPEN_GRAPH = True
SEO_ENHANCER_TWITTER_CARDS = True

# Uncomment below to set limits on page analysis by the SEO plugin.
# SEO_ARTICLES_LIMIT = 10
# SEO_PAGES_LIMIT = 10

# Sitemap plugin configuration. The plugin lists only content whose status is exactly
# "published", which is what keeps drafts (and hidden pages) out. A published page that sets
# `noindex` must be named in "exclude" as well, matched against the URL with no leading slash;
# see "SEO: what the plugins actually do" in CLAUDE.md. A forgotten entry fails
# tests/check_built_site.py, and so CI, which blocks merging a pull request; it does not stop
# a direct push to main from deploying, because validate is off the deploy path.
SITEMAP = {
    "format": "xml",
    "exclude": [r"^test-post\.html$"],
}
