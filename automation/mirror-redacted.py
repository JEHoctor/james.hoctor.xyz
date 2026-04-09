"""Mirror a filtered version of this repository to a remote, redacting draft posts."""

from __future__ import annotations

import os
import shlex
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer
from rich.console import Console

if TYPE_CHECKING:
    from collections.abc import Sequence

console = Console()
err_console = Console(stderr=True, style="bold red")


def flatten_arg_groups(arg_groups: Sequence[Sequence[str]]) -> list[str]:
    """Flatten a list of argument groups into a list of arguments."""
    return [arg for arg_group in arg_groups for arg in arg_group]


def print_for_dry_run(*, arg_groups: Sequence[Sequence[str]]) -> None:
    """Pretty print a command on multiple lines with Bash syntax highlighting.

    Args:
        arg_groups (Sequence[Sequence[str]]): The groups of arguments to display on each line
    """
    code = ""
    first_line = True
    for arg_group in arg_groups:
        if first_line:
            first_line = False
        else:
            code += " \\\n\t"
        code += " ".join(shlex.quote(arg) for arg in arg_group)
    console.print(code, soft_wrap=True)


def is_pelican_draft(path: Path) -> bool:
    """Return True if a Pelican Markdown file has Status: draft in its metadata.

    Pelican metadata is a block of key-value lines at the top of the file,
    terminated by the first blank line. Only this header section is checked,
    avoiding false positives from post body content.

    Args:
        path (Path): Path to the Markdown file.

    Returns:
        bool: True if the file is a draft.
    """
    with path.open() as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                break  # End of Pelican metadata block
            if stripped.lower() == "status: draft":
                return True
    return False


def non_draft_content_files() -> list[Path]:
    """Return all files under content/ that should be mirrored.

    Non-Markdown files (images, static assets, etc.) are always included.
    Markdown files are included only if they are not Pelican drafts.
    """
    result = []
    for f in Path("content").rglob("*"):
        if not f.is_file():
            continue
        if f.suffix == ".md" and is_pelican_draft(f):
            continue
        result.append(f)
    return result


def find_unmerged_draft_branches(source_dir: str, target_dir: str) -> list[str]:
    """Find branches that are merged into main in the target repository, but not in the source repository.

    After git-filter-repo removes draft content, a branch that contains only drafts will have
    its unique commits filtered away, making its tip an ancestor of main.

    Args:
        source_dir (str): Path to the source repository.
        target_dir (str): Path to the target repository.

    Returns:
        list[str]: Remote branch names (e.g. 'origin/my-branch') to remove.
    """
    unmerged_source_branches = subprocess.run(
        args=["git", "-C", source_dir, "branch", "-r", "--no-merged", "origin/main", "origin/*"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    unmerged_source_branches = [b.strip() for b in unmerged_source_branches if b.strip()]
    result = []
    for branch in unmerged_source_branches:
        is_ancestor = subprocess.run(
            args=["git", "-C", target_dir, "merge-base", "--is-ancestor", branch, "origin/main"],
            check=False,
        )
        if is_ancestor.returncode == 0:
            result.append(branch)
    return result


def merged_commits(repo_dir: str) -> list[str]:
    """Return commit hashes that are heads of branches merged via merge commits.

    This finds commits that are parents of a merge commit, but are not the merge base (which is the first parent).
    Only commits that are reachable from HEAD are included, so an appropriate branch should be checked out first.

    Args:
        repo_dir (str): Path to the repository to inspect.

    Returns:
        list[str]: Commit hashes of merged branch tips.
    """
    log = subprocess.run(
        args=["git", "-C", repo_dir, "log", "--merges", "--oneline", "--no-abbrev-commit"],
        capture_output=True,
        text=True,
        check=True,
    )
    commits: list[str] = []
    for line in log.stdout.splitlines():
        merge_commit = line.split()[0]
        parents = subprocess.run(
            args=["git", "-C", repo_dir, "rev-list", "--parents", "-n1", merge_commit],
            capture_output=True,
            text=True,
            check=True,
        )
        # Output is: <commit> <parent1> <parent2> ...
        # We want all parents beyond the first (i.e. merged branch heads).
        commits.extend(parents.stdout.strip().split()[2:])
    return commits


def find_merged_draft_branches(source_dir: str, target_dir: str) -> list[str]:
    """Find branches that were merge-committed in the source repo but lost their merge commit after filtering.

    A branch containing only drafts will have its merge commit removed by git-filter-repo, making
    it appear to have been fast-forward merged in the clone. This discrepancy between source and
    clone identifies it as a draft-only branch.

    Args:
        source_dir (str): Path to the source repository.
        target_dir (str): Path to the target repository.

    Returns:
        list[str]: Remote branch names (e.g. 'origin/my-branch') to remove.
    """
    source_merged = merged_commits(source_dir)
    target_merged = merged_commits(target_dir)
    target_ancestor_branches = subprocess.run(
        args=["git", "-C", target_dir, "branch", "-r", "--merged", "origin/main", "origin/*"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    target_ancestor_branches = [b.strip() for b in target_ancestor_branches if b.strip()]
    result = []
    for branch in target_ancestor_branches:
        if not branch or branch == "origin/main":
            continue
        source_branch_commit = subprocess.run(
            args=["git", "-C", source_dir, "rev-parse", "--verify", f"{branch}^{{commit}}"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        target_merged_commit = subprocess.run(
            args=["git", "-C", target_dir, "rev-parse", "--verify", f"{branch}^{{commit}}"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        if source_branch_commit in source_merged and target_merged_commit not in target_merged:
            result.append(branch)
    return result


def remove_branches(target_dir: str, branches: list[str]) -> None:
    """Remove a list of branches from the clone.

    The branches must be provided as remote branch names (e.g. 'origin/my-branch'), but both the remote
    and the local branch will be removed for each.

    Args:
        target_dir (str): Path to the cloned target repository.
        branches (list[str]): Remote branch names (e.g. 'origin/my-branch') to remove.
    """
    for branch in branches:
        console.print(f"Removing draft branch: {branch}")
        subprocess.run(args=["git", "-C", target_dir, "branch", "-rD", branch], check=True)
        local_branch = branch.removeprefix("origin/")
        subprocess.run(args=["git", "-C", target_dir, "branch", "-D", local_branch], check=False)


def mirror(
    *,
    dry_run: Annotated[bool, typer.Option(help="Print the final push command instead of running it")] = False,
) -> None:
    """Mirror a filtered version of this repository to a remote."""
    # Verify environment variables are set.
    mirror_access_url = os.environ.get("MIRROR_ACCESS_URL")
    secret_mailmap = os.environ.get("SECRET_MAILMAP")
    if not mirror_access_url:
        err_console.print("MIRROR_ACCESS_URL environment variable is not set.")
        raise typer.Exit(1)
    if not secret_mailmap:
        err_console.print("SECRET_MAILMAP environment variable is not set.")
        raise typer.Exit(1)

    # Verify we are on the main branch.
    branch_result = subprocess.run(
        args=["git", "branch", "--show-current"],
        capture_output=True,
        text=True,
        check=True,
    )
    if branch_result.stdout.strip() != "main":
        err_console.print("Must mirror from the main branch.")
        raise typer.Exit(1)

    # Verify we are running from the root of the repository.
    toplevel = subprocess.run(
        args=["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )
    if toplevel.returncode != 0 or Path(toplevel.stdout.strip()) != Path.cwd():
        err_console.print("Must be run from the root of the repository.")
        raise typer.Exit(1)

    # Create separate temp dirs: one for the git clone, one for filter-repo config files.
    source_dir = "."
    target_dir = tempfile.mkdtemp()
    config_dir = tempfile.mkdtemp()
    console.print(f"Clone directory: {target_dir}")
    console.print(f"Config directory: {config_dir}")

    # Clone the target repository.
    subprocess.run(args=["git", "clone", mirror_access_url, target_dir], check=True)

    # Write filter-repo config files to the config temp dir.
    mailmap_path = Path(config_dir) / "mailmap.txt"
    mailmap_path.write_text(secret_mailmap)

    paths_lines = ["regex:^(?!content/|mirror-redacted-config/).*$", ""]
    paths_lines.extend(f"literal:{f}" for f in non_draft_content_files())
    paths_path = Path(config_dir) / "paths.txt"
    paths_path.write_text("\n".join(paths_lines))

    # Run git-filter-repo to redact draft posts.
    subprocess.run(
        args=[
            "uvx",
            "--with=git-filter-repo",
            "git-filter-repo",
            "--source",
            ".",
            "--target",
            target_dir,
            "--mailmap",
            str(mailmap_path),
            "--replace-text",
            "mirror-redacted-config/replace-text.txt",
            "--paths-from-file",
            str(paths_path),
        ],
        check=True,
    )

    # Remove branches that heuristically contain only draft content.
    remove_branches(target_dir, find_unmerged_draft_branches(source_dir, target_dir))
    remove_branches(target_dir, find_merged_draft_branches(source_dir, target_dir))

    # Checkout all remaining branches.
    remaining = subprocess.run(
        args=["git", "-C", target_dir, "branch", "-r", "--list", "origin/*"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    remaining = [b.strip() for b in remaining if b.strip()]
    remaining = [b for b in remaining if not b.startswith("origin/HEAD")]  # Remove line: "origin/HEAD -> origin/main"
    for branch in remaining:
        local_branch = branch.removeprefix("origin/")
        console.print(f"Checking out branch: {branch}")
        subprocess.run(args=["git", "-C", target_dir, "checkout", local_branch], check=True)

    # Push the changes to the target repository.
    push_arg_groups: list[list[str]] = [["git", "-C", target_dir, "push", "--force", "--mirror", "--prune", "origin"]]
    if dry_run:
        print_for_dry_run(arg_groups=push_arg_groups)
    else:
        subprocess.run(args=flatten_arg_groups(push_arg_groups), check=True)


def main() -> None:
    """Entrypoint for the script."""
    typer.run(mirror)


if __name__ == "__main__":
    main()
