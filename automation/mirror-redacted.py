"""Mirror a filtered version of this repository to a remote, redacting draft posts."""

from __future__ import annotations

import os
import re
import shlex
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer
from rich.console import Console

if TYPE_CHECKING:
    from collections.abc import Sequence

# Markup is disabled because everything printed here is literal text: the log prefix is bracketed,
# and paths and branch names are interpolated verbatim. Rich would otherwise read a bracketed word
# as a style tag and silently drop it.
console = Console(markup=False)
err_console = Console(stderr=True, style="bold red", markup=False)

# Anchored on this file so that scanning for content does not depend on the caller's working
# directory. Paths written to the git-filter-repo config must still be repository-relative, so they
# are converted back with Path.relative_to(REPO_ROOT) before being written out.
REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = REPO_ROOT / "content"
NOTEBOOKS_DIR = REPO_ROOT / "notebooks"
REPLACE_TEXT_PATH = REPO_ROOT / "mirror-redacted-config" / "replace-text.txt"

# Everything under these directories is withheld from the mirror unless it is named explicitly, so
# that a new draft is private by default. Both the filter and the verification below work from this.
FILTERED_PREFIXES = ("content/", "mirror-redacted-config/", "notebooks/")

# Most of this job's output comes from git and git-filter-repo. Prefixing our own lines makes it
# obvious which are which, and makes the whole narration greppable. Colour is not used, because the
# job log is not a terminal and rich drops styling there.
LOG_PREFIX = "[mirror-redacted]"
RULE_WIDTH = 78


def log(message: str = "") -> None:
    """Print a line attributed to this script.

    Args:
        message (str): Text to print. Omit it to print a blank separator line.
    """
    console.print(f"{LOG_PREFIX} {message}" if message else LOG_PREFIX, soft_wrap=True)


def log_step(title: str) -> None:
    """Announce the start of a stage of the procedure, so the log can be followed as a sequence.

    Args:
        title (str): Name of the stage that is beginning.
    """
    console.print()
    log(f"--- {title} ---")


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
    for f in CONTENT_DIR.rglob("*"):
        if not f.is_file():
            continue
        if f.suffix == ".md" and is_pelican_draft(f):
            continue
        result.append(f)
    return result


def associated_notebooks(content_path: Path) -> list[Path]:
    """Return all Jupyter notebooks listed in the metadata of a Pelican Markdown file."""
    with content_path.open() as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                break  # End of Pelican metadata block
            if stripped.lower().startswith("notebooks:"):
                notebooks = stripped.split(":", maxsplit=1)[1].strip()
                return [NOTEBOOKS_DIR / f"{n.strip()}.ipynb" for n in notebooks.split(",")]
    return []


def notebooks_to_include(included_content: list[Path]) -> list[Path]:
    """Return all Jupyter notebooks that should be mirrored."""
    result = []
    for content_path in included_content:
        # Only Markdown files carry Pelican metadata. The included content also contains images and
        # other binary assets, which cannot be read as text.
        if content_path.suffix != ".md":
            continue
        result.extend(associated_notebooks(content_path))
    return list(set(result))


def extra_paths_to_include() -> list[Path]:
    """Return paths under content/ or notebooks/ that should be mirrored."""
    non_draft_content = non_draft_content_files()
    notebooks = notebooks_to_include(non_draft_content)
    return non_draft_content + notebooks


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
    merge_log = subprocess.run(
        args=["git", "-C", repo_dir, "log", "--merges", "--oneline", "--no-abbrev-commit"],
        capture_output=True,
        text=True,
        check=True,
    )
    commits: list[str] = []
    for line in merge_log.stdout.splitlines():
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
        # Skip main, which is the branch everything else is compared against. Also skip the
        # "origin/HEAD -> origin/main" entry: it names a symbolic ref rather than a branch, so the
        # rev-parse below cannot resolve it.
        if not branch or branch in ("origin/main", "origin/HEAD -> origin/main"):
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

    A local branch exists only once it has been checked out, which at this point most have not been.
    Deleting one unconditionally therefore writes "error: branch not found" to the log for nearly
    every branch removed, so its existence is checked first and a real failure is not ignored.

    Args:
        target_dir (str): Path to the cloned target repository.
        branches (list[str]): Remote branch names (e.g. 'origin/my-branch') to remove.
    """
    for branch in branches:
        log(f"Removing draft-only branch: {branch}")
        subprocess.run(args=["git", "-C", target_dir, "branch", "-rD", branch], check=True)
        local_branch = branch.removeprefix("origin/")
        local_exists = subprocess.run(
            args=["git", "-C", target_dir, "show-ref", "--verify", "--quiet", f"refs/heads/{local_branch}"],
            check=False,
        )
        if local_exists.returncode == 0:
            subprocess.run(args=["git", "-C", target_dir, "branch", "-D", local_branch], check=True)


def ref_map(target_dir: str, namespace: str) -> dict[str, str]:
    """Return a mapping of branch name to commit hash for every ref under a namespace.

    Args:
        target_dir (str): Path to the cloned target repository.
        namespace (str): Ref namespace to list, e.g. 'refs/heads' or 'refs/remotes/origin'.

    Returns:
        dict[str, str]: Branch name (without the namespace prefix) to commit hash.
    """
    output = subprocess.run(
        args=["git", "-C", target_dir, "for-each-ref", "--format=%(refname) %(objectname)", namespace],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    result = {}
    for line in output:
        refname, _, commit = line.strip().partition(" ")
        name = refname.removeprefix(f"{namespace}/")
        # Skip the symbolic HEAD entry, which records the default branch rather than being one. Its
        # abbreviated form is "origin" rather than "origin/HEAD", so match on the full ref name.
        if not name or name == "HEAD":
            continue
        result[name] = commit
    return result


def redaction_search_terms() -> list[str]:
    """Return the literal strings that git-filter-repo is configured to replace.

    Lines using a regex: prefix are skipped, because they cannot be searched for literally.

    Returns:
        list[str]: Literal strings that must not survive filtering.
    """
    terms = []
    for raw_line in REPLACE_TEXT_PATH.read_text().splitlines():
        line = raw_line.strip()
        if not line:
            continue
        search = line.split("==>", maxsplit=1)[0]
        if search.startswith("regex:"):
            log(f"Not verifying regex replacement rule: {search}")
            continue
        terms.append(search.removeprefix("literal:"))
    return terms


def mailmap_replaced_emails(secret_mailmap: str) -> list[str]:
    """Return the commit email addresses that the mailmap rewrites away.

    A mailmap line carries the replacement address first and the address being replaced last, so
    only lines with more than one address contribute an address that must disappear.

    Args:
        secret_mailmap (str): Contents of the mailmap.

    Returns:
        list[str]: Email addresses that must not survive filtering.
    """
    result = []
    for raw_line in secret_mailmap.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        addresses = re.findall(r"<([^>]*)>", line)
        if len(addresses) > 1:
            result.append(addresses[-1])
    return result


def plan_published_paths() -> set[str]:
    """Decide which withheld files may be published, reporting the decision as it is made.

    This is the choice that determines what becomes public, so it is reported in full rather than
    only counted.

    Returns:
        set[str]: Repository-relative paths under a filtered prefix that may be published.
    """
    extra_paths = extra_paths_to_include()
    included_markdown = {f for f in extra_paths if f.suffix == ".md"}
    included_notebooks = sorted(f for f in extra_paths if f.suffix == ".ipynb")
    excluded_drafts = sorted(f for f in CONTENT_DIR.rglob("*.md") if f.is_file() and f not in included_markdown)

    log(f"Publishing {len(included_markdown)} post(s):")
    for post in sorted(included_markdown):
        log(f"  + {post.relative_to(REPO_ROOT)}")
    log(f"Publishing {len(included_notebooks)} notebook(s) referenced by those posts:")
    for notebook in included_notebooks:
        log(f"  + {notebook.relative_to(REPO_ROOT)}")
    log(f"Withholding {len(excluded_drafts)} draft post(s):")
    for draft in excluded_drafts:
        log(f"  - {draft.relative_to(REPO_ROOT)}")

    return {str(f.relative_to(REPO_ROOT)) for f in extra_paths}


def checkout_all_branches(target_dir: str) -> None:
    """Check out every remaining branch so that a mirror push publishes all of them.

    Args:
        target_dir (str): Path to the cloned target repository.
    """
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
        log(f"Checking out for publication: {branch}")
        subprocess.run(args=["git", "-C", target_dir, "checkout", local_branch], check=True)


def verify_redaction(target_dir: str, secret_mailmap: str, allowed_paths: set[str]) -> None:
    """Check the filtered clone and abort if anything that should have been redacted survived.

    This inspects the actual result of filtering rather than trusting its inputs, because the
    consequence of a mistake is publishing unpublished writing or personal addresses.

    Every ref is checked, not just main, because a branch tip can carry a file that main does not.
    Note that a published post legitimately brings its own history with it, including the revisions
    in which it was still a draft, so the check is on paths rather than on post metadata.

    Args:
        target_dir (str): Path to the cloned target repository.
        secret_mailmap (str): Contents of the mailmap, used to know which addresses to look for.
        allowed_paths (set[str]): Repository-relative paths that may appear under a filtered prefix.

    Raises:
        typer.Exit: If withheld files, redacted strings, or pre-mailmap addresses survived.
    """
    log("Checking the filtered result for anything that should have been withheld.")
    refs = sorted(ref_map(target_dir, "refs/heads"))
    problems = []

    for ref in refs:
        tracked = subprocess.run(
            args=["git", "-C", target_dir, "ls-tree", "-r", "--name-only", ref],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()
        problems.extend(
            f"withheld file {path} survived on branch {ref}"
            for path in tracked
            if path.startswith(FILTERED_PREFIXES) and path not in allowed_paths
        )

    for term in redaction_search_terms():
        for ref in refs:
            hits = subprocess.run(
                args=["git", "-C", target_dir, "grep", "-l", "-I", "-F", "-e", term, ref],
                capture_output=True,
                text=True,
                check=False,
            ).stdout.splitlines()
            problems.extend(f"redacted text survived in {h}" for h in hits)

    surviving_addresses = set(
        subprocess.run(
            args=["git", "-C", target_dir, "log", "--all", "--format=%ae%n%ce"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.split(),
    )
    problems.extend(
        f"pre-mailmap address {address} survived in the commit history"
        for address in mailmap_replaced_emails(secret_mailmap)
        if address in surviving_addresses
    )

    if problems:
        err_console.print(f"{LOG_PREFIX} REFUSING TO PUSH. The filtered repository still contains:")
        for problem in problems:
            err_console.print(f"{LOG_PREFIX}   {problem}")
        raise typer.Exit(1)
    log(f"Verified {len(refs)} branch(es): no withheld files, redacted text, or old addresses.")


def report_changes(before: dict[str, str], after: dict[str, str]) -> None:
    """Print a high level summary of how the mirror will differ from its current state.

    git-filter-repo rewrites deterministically, so a branch whose commit hash is unchanged really
    did not change, and the summary is a description of this run's effect rather than of its inputs.

    Args:
        before (dict[str, str]): Branch to commit hash as currently published on the mirror.
        after (dict[str, str]): Branch to commit hash about to be pushed.
    """
    added = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    updated = sorted(b for b in set(before) & set(after) if before[b] != after[b])
    changed_count = len(added) + len(removed) + len(updated)
    unchanged = len(set(before) & set(after)) - len(updated)

    # This is the part of the log most worth reading, and it competes with hundreds of lines of git
    # output, so it is framed rather than merely printed.
    console.print()
    log("=" * RULE_WIDTH)
    log(f"SUMMARY: {changed_count} branch(es) changed")
    log("=" * RULE_WIDTH)
    for branch in added:
        log(f"  added    {branch}")
    for branch in removed:
        log(f"  removed  {branch}")
    for branch in updated:
        log(f"  updated  {branch}  {before[branch][:8]} -> {after[branch][:8]}")
    if not changed_count:
        log("  Nothing changed. The mirror is already up to date and the push is a no-op.")
    log("-" * RULE_WIDTH)
    log(f"  {unchanged} branch(es) unchanged. {len(after)} branch(es) published in total.")
    log("=" * RULE_WIDTH)


def check_preconditions() -> tuple[str, str]:
    """Check that the required secrets are present and that we are somewhere safe to mirror from.

    Returns:
        tuple[str, str]: The mirror access URL and the contents of the secret mailmap.

    Raises:
        typer.Exit: If a secret is missing, or this is not the root of a checkout of main.
    """
    mirror_access_url = os.environ.get("MIRROR_ACCESS_URL")
    secret_mailmap = os.environ.get("SECRET_MAILMAP")
    if not mirror_access_url:
        err_console.print(f"{LOG_PREFIX} MIRROR_ACCESS_URL environment variable is not set.")
        raise typer.Exit(1)
    if not secret_mailmap:
        err_console.print(f"{LOG_PREFIX} SECRET_MAILMAP environment variable is not set.")
        raise typer.Exit(1)

    branch_result = subprocess.run(
        args=["git", "branch", "--show-current"],
        capture_output=True,
        text=True,
        check=True,
    )
    if branch_result.stdout.strip() != "main":
        err_console.print(f"{LOG_PREFIX} Must mirror from the main branch.")
        raise typer.Exit(1)

    toplevel = subprocess.run(
        args=["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )
    if toplevel.returncode != 0 or Path(toplevel.stdout.strip()) != Path.cwd():
        err_console.print(f"{LOG_PREFIX} Must be run from the root of the repository.")
        raise typer.Exit(1)

    log("Secrets present, on main, at the repository root.")
    return mirror_access_url, secret_mailmap


def mirror(
    *,
    dry_run: Annotated[bool, typer.Option(help="Print the final push command instead of running it")] = False,
) -> None:
    """Mirror a filtered version of this repository to a remote."""
    log_step("Checking preconditions")
    mirror_access_url, secret_mailmap = check_preconditions()

    # Create separate temp dirs: one for the git clone, one for filter-repo config files.
    source_dir = "."
    target_dir = tempfile.mkdtemp()
    config_dir = tempfile.mkdtemp()
    log(f"Clone directory: {target_dir}")
    log(f"Config directory: {config_dir}")

    # Clone the target repository. The URL carries an access token, so it is never printed.
    log_step("Fetching the current mirror")
    log("Cloning the current state of the mirror.")
    subprocess.run(args=["git", "clone", mirror_access_url, target_dir], check=True)
    published_before = ref_map(target_dir, "refs/remotes/origin")
    log(f"The mirror currently publishes {len(published_before)} branch(es).")

    # Write filter-repo config files to the config temp dir.
    mailmap_path = Path(config_dir) / "mailmap.txt"
    mailmap_path.write_text(secret_mailmap)

    log_step("Deciding what may be published")
    allowed_paths = plan_published_paths()
    paths_lines = [f"regex:^(?!{'|'.join(FILTERED_PREFIXES)}).*$", ""]
    paths_lines.extend(f"literal:{path}" for path in sorted(allowed_paths))
    paths_path = Path(config_dir) / "paths.txt"
    paths_path.write_text("\n".join(paths_lines))

    # Run git-filter-repo to redact draft posts.
    log_step("Rewriting history to remove withheld content")
    try:
        subprocess.run(
            args=[
                "uv",
                "run",
                "--group=automation",
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
    finally:
        # The mailmap maps real email addresses and is passed in as a secret, so it should not be
        # left behind in the temp directory after it has served its purpose.
        mailmap_path.unlink(missing_ok=True)

    # Remove branches that heuristically contain only draft content.
    log_step("Removing branches that hold only withheld content")
    remove_branches(target_dir, find_unmerged_draft_branches(source_dir, target_dir))
    remove_branches(target_dir, find_merged_draft_branches(source_dir, target_dir))

    log_step("Checking out the branches to publish")
    checkout_all_branches(target_dir)

    # Refuse to publish anything that should have been redacted. This runs before the push so that
    # a bad filter result fails the job instead of reaching the mirror.
    log_step("Verifying the result")
    verify_redaction(target_dir, secret_mailmap, allowed_paths)

    # Push the changes to the target repository.
    log_step("Publishing" if not dry_run else "Publishing (skipped: dry run)")
    push_arg_groups: list[list[str]] = [["git", "-C", target_dir, "push", "--force", "--mirror", "--prune", "origin"]]
    if dry_run:
        print_for_dry_run(arg_groups=push_arg_groups)
    else:
        subprocess.run(args=flatten_arg_groups(push_arg_groups), check=True)

    report_changes(published_before, ref_map(target_dir, "refs/heads"))


def main() -> None:
    """Entrypoint for the script."""
    typer.run(mirror)


if __name__ == "__main__":
    main()
