#!/usr/bin/env -S uv run --group=automation
"""Mirror a filtered version of this repository to a remote, redacting draft posts."""

from __future__ import annotations

import os
import re
import shlex
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer
from rich.console import Console

import frontmatter

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
# Nothing under private/ is ever named explicitly, so that directory is withheld in full: it holds
# notes that discuss unpublished writing, which must not reach the mirror even though the notes
# themselves are not posts.
FILTERED_PREFIXES = ("content/", "mirror-redacted-config/", "notebooks/", "private/")

# Per-post files that sit next to a post under content/ with the same stem, such as the BibTeX
# file a post cites from. They are published only when their post is, because the filename alone
# discloses the post's title.
SIDECAR_SUFFIXES = (".bib",)

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


# Only a post whose front matter explicitly says so is published. Anything else, including a
# header this code cannot read, is withheld: the failure mode of a wrong guess must be a missing
# post on the mirror, never a draft on it. (A header conversion once quoted every value, an
# exact-string draft check matched nothing, and every draft was published.) The header is parsed
# by the same module the post CLI writes it with, so the two cannot disagree about its shape.
PUBLISHED_STATUSES = frozenset({"published", "hidden"})


class _Unreadable:
    """Sentinel for a file whose front matter cannot be read at all.

    Distinct from ``None`` (a header that parses but declares no status) so that the log can say
    which of the two it saw. Prints as ``unreadable``; never equal to any status string.
    """

    def __str__(self) -> str:
        return "unreadable"


_UNREADABLE = _Unreadable()


def publication_status(path: Path) -> str | _Unreadable | None:
    """Return the status a Markdown file declares, lower-cased.

    Args:
        path (Path): Path to the Markdown file.

    Returns:
        str | _Unreadable | None: The status value; None if the header has no status; the
            unreadable sentinel if the file has no front matter or it does not parse. Only
            ``"published"`` and ``"hidden"`` lead to publication.
    """
    try:
        return frontmatter.status_of(frontmatter.read(path))
    except (frontmatter.FrontMatterError, UnicodeDecodeError):
        return _UNREADABLE


def is_publishable(path: Path) -> bool:
    """Return True only if a Markdown file's header declares a status that means published."""
    return publication_status(path) in PUBLISHED_STATUSES


@dataclass
class ContentPlan:
    """Every file under content/, sorted into what may be published and what may not, and why.

    One walk of the tree produces this; the plan step logs it and the filter consumes it, so the
    two cannot disagree. Paths are absolute.
    """

    posts: list[Path] = field(default_factory=list)  # Markdown whose header says published/hidden
    withheld_posts: list[Path] = field(default_factory=list)  # every other Markdown file
    sidecars: list[Path] = field(default_factory=list)  # e.g. .bib next to a published post
    withheld_sidecars: list[Path] = field(default_factory=list)  # next to a withheld post
    orphan_sidecars: list[Path] = field(default_factory=list)  # next to no post at all
    assets: list[Path] = field(default_factory=list)  # images, static files: always published
    notebooks: list[Path] = field(default_factory=list)  # referenced by a published post, and present
    withheld_notebooks: list[Path] = field(default_factory=list)  # present but not referenced by one
    missing_notebooks: list[Path] = field(default_factory=list)  # referenced by a published post, absent

    def published(self) -> list[Path]:
        """Everything that may leave the repository."""
        return self.posts + self.sidecars + self.assets + self.notebooks


def associated_notebooks(content_path: Path, notebooks_dir: Path) -> list[Path]:
    """Return the notebooks a published Markdown file lists in its metadata.

    Only called for files that passed `is_publishable`, so the header is known to parse; a
    malformed `notebooks` field is reported and ignored rather than allowed to stop the run.
    """
    try:
        names = frontmatter.notebooks_of(frontmatter.read(content_path))
    except frontmatter.FrontMatterError as error:
        log(f"  {content_path.relative_to(REPO_ROOT)}: ignoring its notebooks field: {error}")
        return []
    return [notebooks_dir / f"{name}.ipynb" for name in names]


def classify_content(content_dir: Path = CONTENT_DIR, notebooks_dir: Path = NOTEBOOKS_DIR) -> ContentPlan:
    """Walk content/ once and decide, file by file, what may be published.

    Args:
        content_dir (Path): The content tree to walk. A parameter so tests can use a scratch tree.
        notebooks_dir (Path): Where a post's listed notebooks live.

    Returns:
        ContentPlan: The classification, with every list sorted.
    """
    plan = ContentPlan()
    for path in sorted(p for p in content_dir.rglob("*") if p.is_file()):
        if path.suffix == ".md":
            if is_publishable(path):
                plan.posts.append(path)
                plan.notebooks.extend(associated_notebooks(path, notebooks_dir))
            else:
                plan.withheld_posts.append(path)
        elif path.suffix in SIDECAR_SUFFIXES:
            post = path.with_suffix(".md")
            if not post.is_file():
                plan.orphan_sidecars.append(path)
            elif is_publishable(post):
                plan.sidecars.append(path)
            else:
                plan.withheld_sidecars.append(path)
        else:
            plan.assets.append(path)
    referenced = set(plan.notebooks)
    present = {p for p in notebooks_dir.rglob("*.ipynb") if p.is_file()} if notebooks_dir.is_dir() else set()
    plan.notebooks = sorted(referenced & present)
    plan.missing_notebooks = sorted(referenced - present)
    plan.withheld_notebooks = sorted(present - referenced)
    return plan


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
        source_lookup = subprocess.run(
            args=["git", "-C", source_dir, "rev-parse", "--verify", "--quiet", f"{branch}^{{commit}}"],
            capture_output=True,
            text=True,
            check=False,
        )
        if source_lookup.returncode != 0:
            # The mirror still has a branch the source no longer does (deleted since the last run).
            # The push prunes it, so there is nothing to decide here.
            log(f"  {branch} exists on the mirror but not in the source; the push will prune it.")
            continue
        source_branch_commit = source_lookup.stdout.strip()
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
    plan = classify_content()

    def show(paths: list[Path], marker: str) -> None:
        for path in paths:
            log(f"  {marker} {path.relative_to(REPO_ROOT)}")

    log(f"Publishing {len(plan.posts)} post(s):")
    show(plan.posts, "+")
    log(f"Publishing {len(plan.notebooks)} notebook(s) referenced by those posts:")
    show(plan.notebooks, "+")
    log(f"Publishing {len(plan.sidecars)} sidecar file(s) of published posts and {len(plan.assets)} other file(s).")
    log(f"Withholding {len(plan.withheld_posts)} post(s) whose header does not say published or hidden:")
    for post in plan.withheld_posts:
        status = publication_status(post)
        log(f"  - {post.relative_to(REPO_ROOT)}  (status: {status if status is not None else 'none'})")
    log(f"Withholding {len(plan.withheld_sidecars)} sidecar file(s) belonging to withheld posts:")
    show(plan.withheld_sidecars, "-")
    log(f"Withholding {len(plan.orphan_sidecars)} sidecar file(s) with no post of the same name (a rename leftover?):")
    show(plan.orphan_sidecars, "-")
    log(f"Withholding {len(plan.withheld_notebooks)} notebook(s) that no published post references:")
    show(plan.withheld_notebooks, "-")
    if plan.missing_notebooks:
        log(f"WARNING: {len(plan.missing_notebooks)} notebook(s) referenced by a published post do not exist:")
        show(plan.missing_notebooks, "?")

    return {str(path.relative_to(REPO_ROOT)) for path in plan.published()}


def report_publication_delta(target_dir: str, allowed_paths: set[str]) -> None:
    """Say which posts this run would publish or withdraw compared with the mirror's current main.

    This is the line a reviewer needs: a pull request that is not meant to publish anything should
    show no change here, and one that publishes should name exactly the post it publishes. More
    than one newly published post in a single run is unusual enough to be flagged.

    Args:
        target_dir (str): Path to the clone of the mirror, before filtering.
        allowed_paths (set[str]): Repository-relative paths this run allows under filtered prefixes.
    """
    on_mirror = {
        path
        for path in subprocess.run(
            args=["git", "-C", target_dir, "ls-tree", "-r", "--name-only", "refs/remotes/origin/main"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()
        if path.startswith("content/") and path.endswith(".md")
    }
    planned = {path for path in allowed_paths if path.startswith("content/") and path.endswith(".md")}
    newly_published = sorted(planned - on_mirror)
    withdrawn = sorted(on_mirror - planned)

    log(f"Compared with the mirror's current main, this run newly publishes {len(newly_published)} post(s):")
    for path in newly_published:
        log(f"  + {path}")
    log(f"and withdraws {len(withdrawn)} post(s) that the mirror currently shows:")
    for path in withdrawn:
        log(f"  - {path}")
    if len(newly_published) > 1:
        log(f"WARNING: {len(newly_published)} posts would be newly published at once. Publishing is normally")
        log("WARNING: one post per change; more than that deserves an explanation before merging.")
    if withdrawn:
        log("WARNING: withdrawing a post from the mirror is unusual. Intended retraction, or a status regression?")


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


def check_preconditions(*, dry_run: bool) -> tuple[str, str]:
    """Check that the required secrets are present and that we are somewhere safe to mirror from.

    Args:
        dry_run (bool): Whether this run will only print the push. A dry run may start from any
            branch, since that is how a pull request is previewed; a real run must start from main.

    Returns:
        tuple[str, str]: The mirror access URL and the contents of the secret mailmap.

    Raises:
        typer.Exit: If a secret is missing; if the working directory is not the root of the
            checkout this script lives in; or if the checkout is not on main and this is not a dry
            run.
    """
    mirror_access_url = os.environ.get("MIRROR_ACCESS_URL")
    secret_mailmap = os.environ.get("SECRET_MAILMAP")
    if not mirror_access_url:
        err_console.print(f"{LOG_PREFIX} MIRROR_ACCESS_URL environment variable is not set.")
        raise typer.Exit(1)
    if not secret_mailmap:
        err_console.print(f"{LOG_PREFIX} SECRET_MAILMAP environment variable is not set.")
        raise typer.Exit(1)

    toplevel = subprocess.run(
        args=["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )
    if toplevel.returncode != 0 or Path(toplevel.stdout.strip()).resolve() != Path.cwd().resolve():
        err_console.print(f"{LOG_PREFIX} Must be run from the root of the repository.")
        raise typer.Exit(1)
    if Path.cwd().resolve() != REPO_ROOT:
        # Content is scanned relative to this file's checkout while git runs against the working
        # directory's; if those are two different checkouts the plan and the filter would disagree.
        err_console.print(f"{LOG_PREFIX} Must be run from the checkout that contains this script ({REPO_ROOT}).")
        raise typer.Exit(1)

    branch_result = subprocess.run(
        args=["git", "branch", "--show-current"],
        capture_output=True,
        text=True,
        check=False,
    )
    branch = branch_result.stdout.strip()
    if branch != "main":
        if not dry_run:
            err_console.print(f"{LOG_PREFIX} Must mirror from the main branch.")
            raise typer.Exit(1)
        log(f"On branch {branch!r}, not main. Allowed for a dry run: the result shows what the mirror")
        log("would publish if this branch were main, which is the point of previewing a pull request.")

    log("Secrets present, at the repository root.")
    return mirror_access_url, secret_mailmap


def mirror(
    *,
    dry_run: Annotated[bool, typer.Option(help="Print the final push command instead of running it")] = False,
    keep_temp_dirs: Annotated[
        bool,
        typer.Option(help="Leave the filtered clone and config directory behind for inspection"),
    ] = False,
) -> None:
    """Mirror a filtered version of this repository to a remote."""
    log_step("Checking preconditions")
    mirror_access_url, secret_mailmap = check_preconditions(dry_run=dry_run)

    # Two temp dirs: one for the clone of the mirror, one for filter-repo's config files. Both are
    # removed on exit unless asked otherwise; the mailmap inside the second is removed earlier still.
    with (
        tempfile.TemporaryDirectory(delete=not keep_temp_dirs) as target_dir,
        tempfile.TemporaryDirectory(
            delete=not keep_temp_dirs,
        ) as config_dir,
    ):
        log(f"Clone directory: {target_dir}")
        log(f"Config directory: {config_dir}")
        _mirror_into(target_dir, config_dir, mirror_access_url, secret_mailmap, dry_run=dry_run)
        if keep_temp_dirs:
            log("Temporary directories kept, as requested.")


def _mirror_into(
    target_dir: str,
    config_dir: str,
    mirror_access_url: str,
    secret_mailmap: str,
    *,
    dry_run: bool,
) -> None:
    """The body of `mirror`, once the temporary directories exist."""
    source_dir = str(REPO_ROOT)

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
    report_publication_delta(target_dir, allowed_paths)
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
                source_dir,
                "--target",
                target_dir,
                "--mailmap",
                str(mailmap_path),
                "--replace-text",
                str(REPLACE_TEXT_PATH),
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

    # Make the remote's refs match the filtered clone's exactly: refs the clone has and the remote
    # lacks are created, refs whose history was rewritten are overwritten rather than rejected as
    # non-fast-forward, and refs the remote has but the clone no longer does are deleted. All of
    # that is what --mirror means on its own.
    log_step("Publishing" if not dry_run else "Publishing (skipped: dry run)")
    push_arg_groups: list[list[str]] = [["git", "-C", target_dir, "push", "--mirror", "origin"]]
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
