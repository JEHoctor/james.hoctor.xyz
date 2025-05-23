AUTHOR = "James Hoctor"
SITENAME = "James Hoctor"
SITEURL = "https://james.hoctor.xyz"

PATH = "content"

TIMEZONE = "America/New_York"

DEFAULT_LANG = "en"

THEME = "hyde-personalized"

# Settings specific to the theme
BIO = """
I am a machine learning engineer and a data scientist.
My interests include natural language processing, computer vision, and interpretable machine learning.
I hold an MS in Computer Science from Duke University, and a BS in Mathematics from Rensselaer Polytechnic Institute.
"""
PROFILE_IMAGE = "github-profile.jpg"

# Feed generation is usually not desired when developing
FEED_ALL_ATOM = None
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None

# Blogroll
LINKS = ()

# Social widget
SOCIAL = (
    ("github", "https://github.com/JEHoctor/"),
    ("file-pdf-o", "https://drive.google.com/file/d/1dtkw-Jbo9DwJQrXAMmUa1jVqRovOlD3d/view?usp=share_link"),  # Resume
    ("linkedin", "https://www.linkedin.com/in/james-hoctor/"),
    ("cubes", "https://www.thingiverse.com/jehoctor/designs/"),  # Thingiverse
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
