# Working in this repository

Notes for agents. The things here are mostly not guessable from the code, and several of them
cost real time to work out.

## What this is

A Pelican static site for a personal blog. It is built, deployed and mirrored by Forgejo Actions
running on a self-hosted forge. A **redacted** copy of the repository is published to GitHub.

## The forge is Forgejo, not GitHub

`gh` does not work here and will tell you no remote matches a known GitHub host. Use `tea`, which
is already authenticated, or `fj`.

`tea` does not automatically match this repository to its login, so **always pass `--repo`**:

```bash
tea pr ls --repo james/james.hoctor.xyz
```

`tea api` takes any REST path and expands `{owner}` and `{repo}` placeholders:

```bash
tea api --repo james/james.hoctor.xyz "repos/{owner}/{repo}/actions/runs?limit=5"
```

Useful commands beyond the obvious:

```bash
# Edit a pull request. Removing a "WIP: " title prefix is what un-drafts it;
# a draft PR reports mergeable=false and cannot be merged.
tea api --repo james/james.hoctor.xyz -X PATCH -f title="New title" "repos/{owner}/{repo}/pulls/31"

# Comment on a PR or issue.
tea api --repo james/james.hoctor.xyz -X POST -f body='text' "repos/{owner}/{repo}/issues/27/comments"

tea pr merge 30 --repo james/james.hoctor.xyz --style merge
tea pr close 27 --repo james/james.hoctor.xyz
```

`fj` has `actions tasks|variables|secrets|dispatch` but no log subcommand, so `tea api` is the
better tool for CI work.

## Reading CI logs

This is the part worth knowing. Forgejo 16 added log endpoints; on 15 they did not exist at all,
and no amount of guessing paths would have found them. Check `/swagger.v1.json` if you suspect an
endpoint is missing rather than that you have the path wrong.

Three steps, because the log is per job and jobs are per run:

```bash
R=james/james.hoctor.xyz

# 1. Find the run. Note both numbers: the web UI URL uses index_in_repo,
#    but every API call below wants id.
tea api --repo $R "repos/{owner}/{repo}/actions/runs?limit=5" \
  | jq -r '.workflow_runs[] | "id=\(.id) index=\(.index_in_repo) \(.status) \(.title)"'

# 2. Jobs for that run. Returns a bare array, not an object.
tea api --repo $R "repos/{owner}/{repo}/actions/runs/433/jobs" \
  | jq -r '.[] | "job_id=\(.id) \(.name) \(.status)"'

# 3. The log, as plain text. Download it whole before filtering.
tea api --repo $R "repos/{owner}/{repo}/actions/jobs/1833/logs" > job.log
```

The run-level `status` can still say `running` after every job has finished, so check the jobs
rather than trusting the run.

Logs are prefixed with a timestamp on every line. To read one comfortably:

```bash
sed 's/^[0-9T:.Z-]* //' job.log
```

## Building and checking locally

Everything goes through `just` (the Makefile was removed; anything telling you to run `make` is
stale). `just --list` shows all recipes. The common ones:

```bash
just html            # build to output/
just publish         # build with production settings
just check-precommit # all pre-commit hooks
just check-scripts   # shfmt + shellcheck
just validate        # htmlhint/stylelint over output/  -- CURRENTLY FAILS, see TODO.md
just init            # submodule, pre-commit hooks, npm install
```

Development tooling is pinned in dependency groups, so prefix with the group when calling a tool
directly: `uv run --group=dev ruff check .`. Groups are `dev`, `automation` and `notebook`.

Note that `uv run --group=X` syncs the environment to exactly that group, so alternating between
groups reinstalls packages each time. That is expected, not a fault.

## The mirror, and the invariant that matters

`automation/mirror-redacted.py` publishes a filtered copy of this repository to GitHub. The
invariant is simple and absolute: **unpublished drafts must never reach the mirror**. Everything
under `content/`, `notebooks/`, `mirror-redacted-config/` and `private/` is withheld unless
explicitly listed, so a new draft is private by default.

`private/` is withheld in full — nothing in it is ever added back to the published set. Notes that
name or describe an unpublished draft go there, not in the top-level `TODO.md`, which *is*
published. Remember that a filename is itself a disclosure: listing a draft's title in a public
file leaks it just as surely as publishing the post.

Before pushing, the script inspects its own output and aborts if it finds a withheld file, a
string that should have been redacted, or a pre-mailmap email address. If you change the script,
do not weaken that check.

It also runs on every branch push, not only on main, because the mirror publishes all non-draft
branches. The job checks out `main` regardless of which branch triggered it, which means **a
change to the mirror command cannot be tested before it merges** — the job runs main's checkout
with the branch's workflow file. Plan for that.

### Testing it safely

Never point this at the real mirror while experimenting. Use a local bare repository as the
target and a synthetic mailmap, with `--dry-run` so the push is printed instead of run:

```bash
SB=$(mktemp -d)
git clone -q . "$SB/source"
git -C "$SB/source" fetch -q . 'refs/remotes/origin/*:refs/remotes/origin/*'
git init -q --bare "$SB/mirror.git"
git -C "$SB/mirror.git" fetch -q . 'refs/remotes/origin/*:refs/heads/*'
git -C "$SB/mirror.git" symbolic-ref HEAD refs/heads/main   # else HEAD is an unborn 'master'

cd "$SB/source"
export MIRROR_ACCESS_URL="$SB/mirror.git"
export SECRET_MAILMAP="Redacted <redacted@example.invalid> <real@example.com>"
uv run --group=automation ./automation/mirror-redacted.py --dry-run
```

Because git-filter-repo rewrites deterministically, the summary at the end is meaningful: a
branch whose hash is unchanged genuinely did not change. If a change you believe is cosmetic
reports every branch as updated, something is wrong.

## Environment quirks that have bitten before

- **The runner image is Debian bullseye with git 2.30.** pre-commit calls
  `git ls-files --deduplicate`, added in git 2.31, so `pre-commit run --all-files` cannot work
  there. The `code-quality` job pins a bookworm image for this reason. Do not remove that pin
  without checking the runner's default image first.
- **There are two ruffs.** The `dev` group resolves one version and the pre-commit hook pins
  another, so they can disagree about which rules exist. See TODO.md.
- **Rich markup is disabled** in `mirror-redacted.py`. It would otherwise read a bracketed word,
  including the log prefix and any path containing a bracket, as a style tag and silently drop it.
- **`.claude/worktrees/` is a git worktree**, not part of the source tree. Linters will descend
  into it unless excluded.

## Conventions

- Commit messages: a short subject, then prose explaining *why*. Wrap around 88 characters. No
  bullet-point summaries of the diff.
- End commits made by an agent with a `Co-Authored-By:` trailer.
- Direct commits to `main` are allowed and normal for small content changes. Anything touching
  automation or CI should go through a pull request.
- Drafts carry `Status: draft` in their Pelican metadata. That is what keeps them off both the
  public site and the mirror.
