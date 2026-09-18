"""The `blog` command: `blog post ...` and `blog mirror ...`."""

from __future__ import annotations

import typer

from blog_automation import mirror, post

app = typer.Typer(add_completion=False, no_args_is_help=True, help=__doc__)
app.add_typer(post.app, name="post")
app.command("mirror")(mirror.mirror)
