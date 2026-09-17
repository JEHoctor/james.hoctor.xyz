#!/usr/bin/env -S uv run --group=automation
"""Create and update posts: `new`, `retitle`, `publish`, `modify`.

Each command edits a post's YAML front matter through `frontmatter`, so a change to one key leaves
the rest of the header exactly as it was. Run through just (`just new-post` and friends) or
directly; every command is interactive and prints what it did with a `[post]` prefix.
"""

from __future__ import annotations

import datetime
import shutil
from pathlib import Path
from typing import Annotated, NoReturn

import typer
from pelican.settings import DEFAULT_CONFIG
from pelican.utils import slugify
from rich.console import Console

import frontmatter as fm

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = REPO_ROOT / "content"
DATE_FORMAT = "%Y-%m-%d %H:%M"
LOG_PREFIX = "[post]"

# Files that sit next to a post under the same stem and must follow it when it is renamed.
SIDECAR_SUFFIXES = (".bib",)

app = typer.Typer(add_completion=False, no_args_is_help=True, help=__doc__)
console = Console(markup=False, highlight=False, soft_wrap=True)
err_console = Console(markup=False, highlight=False, stderr=True, soft_wrap=True)


def log(message: str) -> None:
    """Print a line of progress."""
    console.print(f"{LOG_PREFIX} {message}")


def fail(message: str) -> NoReturn:
    """Print an error and exit with status 1."""
    err_console.print(f"{LOG_PREFIX} {message}", style="red")
    raise typer.Exit(1)


def now() -> str:
    """The current local time in the format the headers use."""
    return datetime.datetime.now().astimezone().strftime(DATE_FORMAT)


def slug_for(title: str) -> str:
    """Return the slug Pelican itself would derive from this title.

    Pelican builds a post's URL from its title, not from its filename, so naming the file the same
    way keeps file, URL and the `<slug>.bib` sidecar in agreement.
    """
    return slugify(title, regex_subs=DEFAULT_CONFIG["SLUG_REGEX_SUBSTITUTIONS"])


def all_posts() -> list[Path]:
    """Every Markdown file under content/, pages included."""
    return sorted(p for p in CONTENT_DIR.rglob("*.md") if p.is_file())


def posts_titled(title: str) -> list[Path]:
    """Return the posts whose title is exactly `title`."""
    matches = []
    for path in all_posts():
        try:
            post = fm.read(path)
        except fm.FrontMatterError:
            continue  # an unreadable header cannot claim the title; the mirror withholds it anyway
        if str(post.metadata.get("title", "")) == title:
            matches.append(path)
    return matches


def load(path: Path) -> fm.Post:
    """Read a post or exit with a message naming what is wrong with it."""
    if not path.is_file():
        fail(f"File does not exist: {path}")
    try:
        return fm.read(path)
    except fm.FrontMatterError as error:
        fail(f"Cannot read the front matter of {path}: {error}")


def relative(path: Path) -> Path:
    """A path as it should be shown to the user: relative to the repository root."""
    try:
        return path.resolve().relative_to(REPO_ROOT)
    except ValueError:
        return path


PathArgument = Annotated[Path | None, typer.Argument(help="Path to the post; prompted for if omitted.")]


def prompt_for_path(path: Path | None, prompt: str) -> Path:
    """Use the given path or ask for one, defaulting the prompt to the content directory."""
    if path is None:
        path = Path(typer.prompt(prompt, default="content/"))
    return path


@app.command()
def new(title: Annotated[str | None, typer.Option(help="Title; prompted for if omitted.")] = None) -> None:
    """Create an empty draft post from a title."""
    if title is None:
        title = typer.prompt("Title")
    title = title.strip()
    if not title:
        fail("A post needs a title.")

    duplicates = posts_titled(title)
    if duplicates:
        fail("A post with this title already exists: " + ", ".join(str(relative(p)) for p in duplicates))
    path = CONTENT_DIR / f"{slug_for(title)}.md"
    if path.exists():
        fail(f"File already exists: {relative(path)}")

    metadata = fm.CommentedMap()
    metadata["title"] = fm.quoted(title)
    metadata["date"] = fm.quoted(now())
    metadata["category"] = fm.quoted("Blog")
    metadata["status"] = fm.quoted("draft")
    fm.write(path, fm.Post(metadata=metadata, body="\n"))
    log(f"Created {relative(path)} as a draft.")


@app.command()
def retitle(path: PathArgument = None) -> None:
    """Give a post a new title and rename its file (and any sidecar) to match.

    Deliberately careful: the old files are kept as `.old` copies for you to diff and remove.
    """
    old_path = prompt_for_path(path, "Old file name")
    post = load(old_path)
    log(f"Old title: {post.metadata.get('title', '')}")
    new_title = typer.prompt("New title").strip()
    if not new_title:
        fail("A post needs a title.")

    duplicates = [p for p in posts_titled(new_title) if p.resolve() != old_path.resolve()]
    if duplicates:
        fail("A post with this title already exists: " + ", ".join(str(relative(p)) for p in duplicates))
    new_path = old_path.with_name(f"{slug_for(new_title)}.md")
    if new_path.exists() and new_path.resolve() != old_path.resolve():
        fail(f"File already exists: {relative(new_path)}")

    sidecars = [old_path.with_suffix(suffix) for suffix in SIDECAR_SUFFIXES if old_path.with_suffix(suffix).is_file()]
    for sidecar in sidecars:
        target = new_path.with_suffix(sidecar.suffix)
        if target.exists() and target.resolve() != sidecar.resolve():
            fail(f"File already exists: {relative(target)}")

    post.metadata["title"] = fm.quoted(new_title)
    fm.write(new_path, post)
    if new_path.resolve() != old_path.resolve():
        old_path.rename(old_path.with_name(old_path.name + ".old"))
    for sidecar in sidecars:
        target = new_path.with_suffix(sidecar.suffix)
        if target.resolve() != sidecar.resolve():
            shutil.copy2(sidecar, target)
            sidecar.rename(sidecar.with_name(sidecar.name + ".old"))

    log(f"Wrote {relative(new_path)} with the new title.")
    log("Next steps:")
    log(f"  - diff {relative(new_path)} {relative(old_path)}.old")
    for sidecar in sidecars:
        log(f"  - diff {relative(new_path.with_suffix(sidecar.suffix))} {relative(sidecar)}.old")
    log(f"  - git add {relative(new_path.parent)}")
    log(f"  - rm {relative(old_path)}.old" + "".join(f" {relative(s)}.old" for s in sidecars))


@app.command()
def publish(path: PathArgument = None) -> None:
    """Turn a draft into a published post, dating it now."""
    path = prompt_for_path(path, "File name of post")
    post = load(path)
    status = fm.status_of(post)
    if status != "draft":
        fail(f"File is not a draft: {relative(path)} (status: {status if status is not None else 'none'})")
    post.metadata["status"] = fm.quoted("published")
    post.metadata["date"] = fm.quoted(now())
    fm.write(path, post)
    log(f"Published {relative(path)} with date {post.metadata['date']}.")
    log("Remember that publishing also lets the mirror publish the post and its .bib, if any.")


@app.command()
def modify(path: PathArgument = None) -> None:
    """Stamp a published post's `modified` date with the current time."""
    path = prompt_for_path(path, "File name of post")
    post = load(path)
    status = fm.status_of(post)
    if status != "published":
        fail(f"File is not published: {relative(path)} (status: {status if status is not None else 'none'})")
    stamp = fm.quoted(now())
    if "modified" in post.metadata:
        post.metadata["modified"] = stamp
    else:
        keys = list(post.metadata)
        position = keys.index("date") + 1 if "date" in keys else len(keys)
        post.metadata.insert(position, "modified", stamp)
    fm.write(path, post)
    log(f"Set modified date of {relative(path)} to {stamp}.")


if __name__ == "__main__":
    app()
