"""Guards on how the theme links its own stylesheets and scripts, checked without building the site."""

from __future__ import annotations

import hashlib
import importlib.util
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# The settings file is not on sys.path under pytest, and is not a package to install.
_spec = importlib.util.spec_from_file_location("pelicanconf", REPO_ROOT / "pelicanconf.py")
assert _spec is not None
assert _spec.loader is not None
pelicanconf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pelicanconf)

THEME_DIR = REPO_ROOT / pelicanconf.THEME


def test_hash_is_of_the_file_content() -> None:
    path = "css/poole.css"
    digest = hashlib.sha256((THEME_DIR / "static" / path).read_bytes()).hexdigest()
    assert pelicanconf.hashed_theme_asset(path) == f"{path}?v={digest[:12]}"


def test_a_missing_asset_is_an_error() -> None:
    with pytest.raises(FileNotFoundError):
        pelicanconf.hashed_theme_asset("css/no-such-file.css")


@pytest.mark.parametrize("template", sorted((THEME_DIR / "templates").rglob("*.html")), ids=lambda p: p.name)
def test_no_template_links_an_unversioned_theme_asset(template: Path) -> None:
    """A plain URL here would be cached by Cloudflare and browsers under a URL that never changes."""
    assert not re.findall(r"THEME_STATIC_DIR \}\}/[^\"']*\.(?:css|js)[\"']", template.read_text(encoding="utf-8"))


def test_every_theme_stylesheet_and_script_is_linked_through_the_filter() -> None:
    base = (THEME_DIR / "templates" / "base.html").read_text(encoding="utf-8")
    linked = set(re.findall(r"\{\{ '((?:css|js)/[^']+)'\|hashed_theme_asset \}\}", base))
    static = THEME_DIR / "static"
    assert linked == {p.relative_to(static).as_posix() for p in [*static.glob("css/*.css"), *static.glob("js/*.js")]}
