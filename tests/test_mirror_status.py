"""Tests for the mirror script's fail-closed publication rule.

The script is a typer application in a file with a hyphen in its name, so it is loaded from its
path rather than imported.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "automation" / "mirror-redacted.py"


@pytest.fixture(scope="module")
def mirror() -> ModuleType:
    spec = importlib.util.spec_from_file_location("mirror_redacted", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("header", "publishable"),
    [
        ('status: "published"', True),
        ("status: published", True),
        ("status: Hidden", True),
        ('status: "draft"', False),
        ("status: draft", False),
        ("status: publishedd", False),
        ("title: no status", False),
    ],
)
def test_only_an_explicit_published_or_hidden_status_publishes(
    mirror: ModuleType,
    tmp_path: Path,
    header: str,
    *,
    publishable: bool,
) -> None:
    path = write(tmp_path, "post.md", f"---\n{header}\n---\n")
    assert mirror.is_publishable(path) is publishable


@pytest.mark.parametrize(
    "text",
    [
        "Title: x\nStatus: published\n\nbody\n",  # the old header style is no longer accepted
        "---\nstatus: [oops\n---\n",
        "no header at all\n",
    ],
)
def test_unreadable_files_are_withheld_and_reported_as_such(mirror: ModuleType, tmp_path: Path, text: str) -> None:
    path = write(tmp_path, "post.md", text)
    assert mirror.publication_status(path) == mirror.UNREADABLE
    assert mirror.is_publishable(path) is False


def test_sidecar_follows_its_post(mirror: ModuleType, tmp_path: Path) -> None:
    write(tmp_path, "a.md", '---\nstatus: "published"\n---\n')
    write(tmp_path, "b.md", '---\nstatus: "draft"\n---\n')
    assert mirror.is_withheld_sidecar(write(tmp_path, "a.bib", "")) is False
    assert mirror.is_withheld_sidecar(write(tmp_path, "b.bib", "")) is True
    assert mirror.is_withheld_sidecar(write(tmp_path, "orphan.bib", "")) is True


def test_every_current_post_is_classified_and_drafts_outnumber_nothing_silently(mirror: ModuleType) -> None:
    """A regression guard against the incident: the real content tree must yield some withheld drafts.

    If every post suddenly reads as publishable, or none does, the parser and the headers have
    drifted apart again.
    """
    posts = sorted(p for p in (REPO_ROOT / "content").rglob("*.md"))
    statuses = {p.name: mirror.publication_status(p) for p in posts}
    assert mirror.UNREADABLE not in statuses.values(), statuses
    assert None not in statuses.values(), statuses
    assert "draft" in statuses.values()
    assert "published" in statuses.values()
