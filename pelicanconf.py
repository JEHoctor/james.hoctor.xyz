AUTHOR = "James Hoctor"
SITENAME = "James Hoctor"
SITEURL = "https://james.hoctor.xyz"

PATH = "content"

TIMEZONE = "America/New_York"

DEFAULT_LANG = "en"

THEME = "hyde-personalized"

# Settings specific to the theme
BIO = "Machine learning engineer and data scientist. <nobr>BS Mathematics</nobr>, <nobr>MS Computer</nobr> Science."
PROFILE_IMAGE = "github-profile.jpg"
COLOR_THEME = "08"

# Settings specific to my fork of the theme
FAVICON_DIR = "static"
APPLE_MOBILE_WEB_APP_TITLE = "James H"

# Tell Pelican that content/static/ should be copied to the output. The default is just content/images/.
STATIC_PATHS = ["images", "static"]

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
