"""Tests for the front-matter parser shared by the post CLI and the mirror script."""

from __future__ import annotations

from pathlib import Path

import pytest

import frontmatter as fm

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = REPO_ROOT / "content"

QUOTED = '---\ntitle: "A post"\ndate: "2026-09-12 17:59"\ncategory: "Blog"\nstatus: "draft"\n---\n\nBody.\n'


@pytest.mark.parametrize("path", sorted(CONTENT_DIR.rglob("*.md")), ids=lambda p: p.name)
def test_every_real_post_round_trips_byte_for_byte(path: Path) -> None:
    """Parsing and re-rendering a real post must not change a single byte.

    This is what lets the CLI edit one key and leave the rest of a header alone.
    """
    text = path.read_text(encoding="utf-8")
    assert fm.render(fm.parse(text)) == text


def test_edit_touches_only_the_edited_line() -> None:
    post = fm.parse(QUOTED)
    post.metadata["status"] = fm.quoted("published")
    assert fm.render(post) == QUOTED.replace('status: "draft"', 'status: "published"')


def test_inserted_key_keeps_position_and_quoting() -> None:
    post = fm.parse(QUOTED)
    post.metadata.insert(2, "modified", fm.quoted("2026-09-17 12:00"))
    lines = fm.render(post).splitlines()
    assert lines[2:4] == ['date: "2026-09-12 17:59"', 'modified: "2026-09-17 12:00"']


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        ('status: "draft"', "draft"),
        ("status: draft", "draft"),
        ("status: 'Draft'", "draft"),
        ("status: Published", "published"),
        ("status: hidden", "hidden"),
        ("title: no status here", None),
    ],
)
def test_status_of_reads_bare_and_quoted_values(header: str, expected: str | None) -> None:
    """The incident case: a quoted status must read the same as a bare one."""
    assert fm.status_of(fm.parse(f"---\n{header}\n---\n")) == expected


def test_status_that_yaml_types_as_bool_does_not_match_a_real_status() -> None:
    assert fm.status_of(fm.parse("---\nstatus: yes\n---\n")) not in {"published", "hidden", "draft"}


@pytest.mark.parametrize(
    "text",
    [
        "Title: x\nStatus: draft\n\nbody\n",  # old Pelican header, no fence
        "---\ntitle: x\nstatus: draft\n",  # never closed
        "---\nstatus: [oops\n---\n",  # invalid YAML
        "---\n- just\n- a list\n---\n",  # not a mapping
        "",  # empty file
        "body without any header\n",
    ],
)
def test_unreadable_headers_raise(text: str) -> None:
    with pytest.raises(fm.FrontMatterError):
        fm.parse(text)


def test_empty_front_matter_is_an_empty_mapping() -> None:
    post = fm.parse("---\n---\nbody\n")
    assert dict(post.metadata) == {}
    assert post.body == "body\n"


def test_body_is_preserved_verbatim_including_leading_blank_line() -> None:
    assert fm.parse(QUOTED).body == "\nBody.\n"


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        ('notebooks: "Wordle_with_BREAD"', ["Wordle_with_BREAD"]),
        ("notebooks: a, b ,c", ["a", "b", "c"]),
        ("notebooks: [a, b]", ["a", "b"]),
        ("title: none", []),
    ],
)
def test_notebooks_of(header: str, expected: list[str]) -> None:
    """The quoted form once produced a path containing literal quote characters."""
    assert fm.notebooks_of(fm.parse(f"---\n{header}\n---\n")) == expected
