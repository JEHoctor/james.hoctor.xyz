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
# direct templates. tests/test_descriptions.py checks the rendered lengths.
META_DESCRIPTIONS = {
    "index": (
        "James Hoctor is a machine learning engineer and data scientist with a BS in "
        "Mathematics and an MS in Computer Science. Notes on math, Python tooling and Linux."
    ),
    "archives": (
        "Every post on James Hoctor's blog, newest first: writing on machine learning, "
        "mathematics, Python tooling such as uv, and running a self-hosted Linux server."
    ),
    "tags": (
        "Browse James Hoctor's blog by tag. Topics span mathematics and probability, machine "
        "learning, Python packaging and tooling, and self-hosted Linux server notes."
    ),
    "categories": (
        "Browse James Hoctor's blog by category. Posts on machine learning, mathematics, "
        "Python tooling and the Linux servers that host this site, grouped by subject."
    ),
    "authors": (
        "Posts on james.hoctor.xyz listed by author. James Hoctor is a machine learning "
        "engineer and data scientist writing about math, Python tooling and Linux servers."
    ),
}

# Per-term listing pages interpolate the tag, category or author name. The surrounding text is
# sized so that a term of a realistic length lands inside the 150-160 character window.
TAG_META_DESCRIPTION = (
    "Posts on James Hoctor's blog tagged {}: notes on machine learning, mathematics and "
    "Python tooling from a machine learning engineer and data scientist."
)
CATEGORY_META_DESCRIPTION = (
    "Every post in the {} category on James Hoctor's blog covering machine learning, "
    "mathematics, Python tooling and self-hosted Linux from an ML engineer."
)
AUTHOR_META_DESCRIPTION = (
    "Every post written by {} on james.hoctor.xyz, a blog about machine learning, "
    "mathematics, Python tooling and running a self-hosted Linux server."
)

# Settings specific to the theme
BIO = "Machine learning engineer and data scientist. <nobr>BS Mathematics</nobr>, <nobr>MS Computer Science.</nobr>"
PROFILE_IMAGE = "github-profile.jpg"
COLOR_THEME = "08"

# Settings specific to my fork of the theme
FAVICON_DIR = "static"
APPLE_MOBILE_WEB_APP_TITLE = "James H"

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

# Sitemap plugin configuration. Drafts are excluded automatically (they aren't "published"),
# but drafts/ is excluded explicitly too, to match the Disallow rule in content/extra/robots.txt.
#
# These patterns are matched against the URL *relative to the output root*, with no leading
# slash: the plugin writes SITEURL + "/" + pageurl and matches pageurl. A pattern written as
# "^/drafts/" therefore matches nothing at all, which is what this one used to say.
#
# A page carrying <meta name="robots" content="noindex"> has no business in the sitemap either:
# the sitemap asks a crawler to index the URL and the page then asks it not to. The plugin drops
# anything whose status is not exactly "published" of its own accord, so only a page that stays
# published while asking to be de-indexed needs naming here. tests/check_built_site.py checks
# the built output for that contradiction, so a forgotten entry cannot ship.
SITEMAP = {
    "format": "xml",
    "exclude": [r"^drafts/", r"^test-post\.html$"],
}
