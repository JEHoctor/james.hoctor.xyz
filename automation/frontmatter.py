"""Read and write the YAML front matter at the top of a post.

Every post and page under content/ starts with a block fenced by `---` lines, which pandoc-reader
requires and which carries Pelican's metadata (title, date, status, ...). This module is the one
place that knows the block's shape, shared by the post CLI and the mirror script, so that the two
cannot drift apart in what they consider a header. Parsing is done by ruamel.yaml in round-trip
mode: editing one key and writing the file back preserves the order, quoting and comments of
everything else.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.scalarstring import DoubleQuotedScalarString

if TYPE_CHECKING:
    from pathlib import Path

FENCE = "---"


class FrontMatterError(ValueError):
    """The file does not start with a well-formed YAML front-matter block."""


@dataclass
class Post:
    """A post split into its metadata mapping and the Markdown body that follows the header.

    Attributes:
        metadata: The front matter as a mapping. In round-trip mode this is a CommentedMap, which
            behaves like a dict and remembers formatting.
        body: Everything after the closing fence, including its leading newline if any.
    """

    metadata: CommentedMap
    body: str


def _yaml() -> YAML:
    yaml = YAML(typ="rt")
    yaml.preserve_quotes = True
    yaml.width = 4096  # never wrap long titles
    return yaml


def parse(text: str) -> Post:
    """Split a post's source into front matter and body.

    Args:
        text: The whole file.

    Returns:
        Post: Parsed metadata and the body.

    Raises:
        FrontMatterError: If the file does not start with `---`, the block is not closed, the
            YAML does not parse, or it parses to something other than a mapping.
    """
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != FENCE:
        msg = "file does not start with a '---' front-matter fence"
        raise FrontMatterError(msg)
    for index in range(1, len(lines)):
        if lines[index].rstrip("\r\n") in (FENCE, "..."):
            header = "".join(lines[1:index])
            body = "".join(lines[index + 1 :])
            break
    else:
        msg = "front-matter block is never closed"
        raise FrontMatterError(msg)

    try:
        metadata = _yaml().load(header)
    except Exception as error:  # ruamel raises a family of parser/scanner errors
        msg = f"front matter is not valid YAML: {error}"
        raise FrontMatterError(msg) from error
    if metadata is None:
        metadata = CommentedMap()
    if not isinstance(metadata, CommentedMap):
        msg = f"front matter is a {type(metadata).__name__}, not a mapping"
        raise FrontMatterError(msg)
    return Post(metadata=metadata, body=body)


def render(post: Post) -> str:
    """Serialise a post back to source form, front matter first.

    Args:
        post: The post to render.

    Returns:
        str: The file contents.
    """
    buffer = io.StringIO()
    _yaml().dump(post.metadata, buffer)
    return f"{FENCE}\n{buffer.getvalue()}{FENCE}\n{post.body}"


def read(path: Path) -> Post:
    """Read and parse a post from disk."""
    return parse(path.read_text(encoding="utf-8"))


def write(path: Path, post: Post) -> None:
    """Write a post to disk."""
    path.write_text(render(post), encoding="utf-8")


def quoted(value: str) -> DoubleQuotedScalarString:
    """Return a string that ruamel will emit double-quoted.

    The existing headers quote every value, and quoting is also the safe choice: unquoted,
    "2025-04-24 11:27" is ambiguous YAML and "True" becomes a boolean.
    """
    return DoubleQuotedScalarString(value)


def status_of(post: Post) -> str | None:
    """Return the post's status, lower-cased, or None if it has none.

    A non-string value (say, a bare YAML boolean) is returned as its string form so that the
    caller can log what it saw; it will not match any known status.
    """
    value = post.metadata.get("status")
    if value is None:
        return None
    return str(value).strip().lower()


def notebooks_of(post: Post) -> list[str]:
    """Return the notebook names listed in the post's `notebooks` field, if any.

    The field is a comma-separated string, as Pelican metadata conventionally is; a YAML list is
    accepted too.
    """
    value = post.metadata.get("notebooks")
    if value is None:
        return []
    if isinstance(value, str):
        return [name.strip() for name in value.split(",") if name.strip()]
    return [str(name).strip() for name in value]
