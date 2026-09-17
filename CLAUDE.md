# Working in this repository

Notes for agents. The things here are mostly not guessable from the code, and several of them
cost real time to work out.

## What this is

A Pelican static site for a personal blog. It is built, deployed and mirrored by Forgejo Actions
running on a self-hosted forge. A **redacted** copy of the repository is published to GitHub.

## Building and checking locally

Everything goes through `just` (the Makefile was removed; anything telling you to run `make` is
stale). `just --list` shows all recipes. The common ones:

```bash
just html            # build to output/
just publish         # build with production settings
just check-precommit # all pre-commit hooks
just check-scripts   # shfmt + shellcheck
just validate        # htmlhint/stylelint over output/ (also runs in CI, off the deploy path)
just init            # pre-commit hooks, npm install
```

Development tooling is pinned in dependency groups, so prefix with the group when calling a tool
directly: `uv run --group=dev ruff check .`. Groups are `dev`, `automation` and `notebook`.

Note that `uv run --group=X` syncs the environment to exactly that group, so alternating between
groups reinstalls packages each time. That is expected, not a fault.

## The mirror, and the invariant that matters

`automation/mirror-redacted.py` publishes a filtered copy of this repository to GitHub. The
invariant is simple and absolute: **unpublished drafts must never reach the mirror**. Everything
under `content/`, `notebooks/`, `mirror-redacted-config/` and `private/` is withheld unless
explicitly listed, so a new draft is private by default. Non-Markdown files under `content/`
(images, static assets) are listed unconditionally, with one exception: a per-post sidecar such
as `content/<slug>.bib` follows its post — published only when `content/<slug>.md` exists and is
not a draft — because its filename alone is a disclosure.

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
- **ruff is pinned in two places.** The `dev` and `notebook` groups pin `ruff==X.Y.Z` in
  `pyproject.toml` and the pre-commit hook pins `rev: vX.Y.Z`. They must move together, or
  `ruff check .` and `just check-precommit` start disagreeing about which rules exist.
- **`just html debug=1` silently does nothing.** just passes `debug=1` as the literal positional
  value, so `-D` is never emitted and a failing build shows a one-line `CRITICAL` with no
  traceback. Use `just DEBUG=1 html` (variable override) or positional `just html 1`.
- **`uv run` syncs inexactly**: it installs what the lockfile needs but leaves packages that are
  no longer in it. After switching between branches with different dependencies, run `uv sync`
  (exact) or the leftovers stay importable — and Pelican auto-discovers every installed
  `pelican.plugins.*` package unless `PLUGINS` is set explicitly, so a stale plugin can crash a
  build that is fine in a fresh checkout.
- **Rich markup is disabled** in `mirror-redacted.py`. It would otherwise read a bracketed word,
  including the log prefix and any path containing a bracket, as a style tag and silently drop it.
- **`.claude/worktrees/` holds git worktrees**, not part of the source tree. ruff excludes
  `.claude` via `extend-exclude`; any other linter you add needs the same exclusion.

## Conventions

- Agent PRs start with a bold line that makes them identifiable at a glance, for example
  **This PR was written by an agent (Claude Code).**
- Commit messages: a short subject, then prose explaining *why*. Wrap around 88 characters. Avoid
  bullet-point summaries of the diff.
- End commits made by an agent with the `Co-Authored-By:` and `Claude-Session:` trailers.
- `main` is a protected branch and the `claude` user cannot push to it (`Forgejo: Not allowed to
  push to protected branch main`); that is deliberate. Everything an agent does lands through a
  pull request, including one-line documentation fixes. The human commits content directly to
  `main` themselves.
- Drafts carry `Status: draft` in their Pelican metadata. That is what keeps them off both the
  public site and the mirror.
