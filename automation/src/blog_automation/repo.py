"""Where the repository is.

Both subcommands operate on the checkout they are run from, and refuse to run anywhere but its
root: `post` so that a scratch copy is edited when you are standing in one, `mirror` because
git-filter-repo and the content scan must agree on which checkout they are looking at.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


class NotAtRepositoryRootError(RuntimeError):
    """The working directory is not the root of a checkout of the site."""


def repo_root() -> Path:
    """Return the working directory, having checked that it is the root of the site's checkout.

    Raises:
        NotAtRepositoryRootError: If the working directory is not a git top level, or the checkout
            does not look like this site (no content/ directory).
    """
    toplevel = subprocess.run(
        args=["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )
    cwd = Path.cwd().resolve()
    if toplevel.returncode != 0 or Path(toplevel.stdout.strip()).resolve() != cwd:
        msg = "run this from the root of the repository"
        raise NotAtRepositoryRootError(msg)
    if not (cwd / "content").is_dir():
        msg = f"{cwd} has no content/ directory; is this the site's checkout?"
        raise NotAtRepositoryRootError(msg)
    return cwd
