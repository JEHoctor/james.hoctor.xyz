"""Tests for `blog post`: what `publish` changes and what it reminds you to do afterwards."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from blog_automation import frontmatter as fm
from blog_automation import post
from typer.testing import CliRunner

if TYPE_CHECKING:
    from pathlib import Path

REMINDER = "META_DESCRIPTIONS and the tag, category and author templates in pelicanconf.py"


@pytest.fixture
def site(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A scratch checkout root with a content/ directory, standing in for the real repository."""
    (tmp_path / "content").mkdir()
    monkeypatch.setattr(post, "repo_root", lambda: tmp_path)
    return tmp_path


def write_post(site: Path, status: str) -> Path:
    path = site / "content" / "a-post.md"
    path.write_text(f'---\ntitle: "A post"\ndate: "2026-01-01 00:00"\nstatus: "{status}"\n---\n\nBody.\n')
    return path


def test_publish_reminds_to_reread_the_meta_descriptions(site: Path) -> None:
    path = write_post(site, "draft")
    result = CliRunner().invoke(post.app, ["publish", str(path)])
    assert result.exit_code == 0, result.output
    assert fm.status_of(fm.read(path)) == "published"
    assert REMINDER in " ".join(result.output.split())


def test_a_refused_publish_does_not_remind(site: Path) -> None:
    path = write_post(site, "published")
    result = CliRunner().invoke(post.app, ["publish", str(path)])
    assert result.exit_code == 1
    assert REMINDER not in " ".join(result.output.split())
