"""Tests for the mirror's fail-closed publication rule and its classification of content/."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from blog_automation import mirror

if TYPE_CHECKING:
    from pathlib import Path


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
def test_unreadable_files_are_withheld_and_reported_as_such(tmp_path: Path, text: str) -> None:
    path = write(tmp_path, "post.md", text)
    status = mirror.publication_status(path)
    assert str(status) == "unreadable"
    assert status not in {"published", "hidden", "draft", None}
    assert mirror.is_publishable(path) is False


def test_classify_content_sorts_every_kind_of_file(tmp_path: Path) -> None:
    content = tmp_path / "content"
    notebooks = tmp_path / "notebooks"
    (content / "pages").mkdir(parents=True)
    write(content, "pub.md", '---\nstatus: "published"\nnotebooks: "nb"\n---\n')
    write(content, "pub.bib", "")
    write(content, "draft.md", '---\nstatus: "draft"\n---\n')
    write(content, "draft.bib", "")
    write(content, "orphan.bib", "")
    write(content / "pages", "hidden.md", '---\nstatus: "hidden"\n---\n')
    write(content, "broken.md", "no front matter\n")
    write(content, "image.png", "")
    write(content, "wants-missing.md", '---\nstatus: "published"\nnotebooks: [nb, gone]\n---\n')
    notebooks.mkdir()
    write(notebooks, "nb.ipynb", "{}")
    write(notebooks, "unreferenced.ipynb", "{}")

    plan = mirror.classify_content(content, notebooks)

    names = lambda paths: [p.relative_to(tmp_path).as_posix() for p in paths]  # noqa: E731
    assert names(plan.posts) == ["content/pages/hidden.md", "content/pub.md", "content/wants-missing.md"]
    assert names(plan.withheld_posts) == ["content/broken.md", "content/draft.md"]
    assert names(plan.sidecars) == ["content/pub.bib"]
    assert names(plan.withheld_sidecars) == ["content/draft.bib"]
    assert names(plan.orphan_sidecars) == ["content/orphan.bib"]
    assert names(plan.assets) == ["content/image.png"]
    assert names(plan.notebooks) == ["notebooks/nb.ipynb"]
    assert names(plan.withheld_notebooks) == ["notebooks/unreferenced.ipynb"]
    assert names(plan.missing_notebooks) == ["notebooks/gone.ipynb"]
    assert set(names(plan.published())) == {
        "content/pages/hidden.md",
        "content/pub.md",
        "content/wants-missing.md",
        "content/pub.bib",
        "content/image.png",
        "notebooks/nb.ipynb",
    }
