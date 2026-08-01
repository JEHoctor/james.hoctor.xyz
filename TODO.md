# Loose ends

Work that is understood but not done. Each item says what the problem is, what was decided, and
what is left. Read `CLAUDE.md` first for how to operate in this repository.

This file is published to the GitHub mirror. **Anything that names or describes an unpublished
draft belongs in `private/TODO.md` instead**, which the mirroring script withholds in full.

`todo.txt` predates this file and both of its items are long finished (the favicon exists, the
theme is forked). It can be deleted.

---

## 1. Remove csslint

**Status:** decided, not started. **Blocks:** `just validate`, item 3.

`just validate` fails. One of the two causes is csslint, which cannot *parse*
`@media (width >= 48em)` — Media Queries Level 4 syntax that the theme uses in three places.
csslint has been unmaintained since 2018. All 64 reported "problems" are a single parse cascade,
not real findings.

Decision: **remove csslint entirely.** stylelint is the maintained equivalent, is already
configured, and covers the same ground.

To do, in this repository:

- drop the `npx csslint output/` line from the `validate` recipe in `justfile`
- drop the `diff .csslintrc hyde-personalized/.csslintrc` line from the same recipe
- delete `.csslintrc`
- remove the csslint dependency from `package.json` and re-lock
- remove `csslint` and `csslintrc` from `cSpell.words` in `.vscode/settings.json`

And in the `hyde-personalized` submodule (a fork at `github.com/JEHoctor/pelican-hyde`):

- delete `.csslintrc`
- remove the `mirrors-csslint` hook from `.pre-commit-config.yaml`

---

## 2. Fix the stylelint errors

**Status:** analysed in full, not applied. **Blocks:** `just validate`, item 3.

`npx stylelint hyde-personalized/static/css/*.css` reports 18 errors. They fall into three groups
and need three different treatments. All of this is in the submodule.

### 2a. `no-descending-specificity` in `hyde.css` — 7 errors, suppress

These compare rules from different theme colour variants, e.g. `.theme-base-09 .content a`
against `.theme-base-08 .related-posts li a:hover`. `templates/base.html` puts exactly one
`theme-base-*` class on `<body>`, and there are eight variants, so two variants can never apply
to the same document and no cascade conflict is possible. These are false positives.

Reordering to satisfy the rule would mean abandoning the file's one-block-per-colour layout for
no benefit. Suppress it for this file instead, via an `overrides` entry in `.stylelintrc.json`
matching `**/hyde.css`. Use a glob rather than a fixed path: the same config is applied both to
the sources in the submodule and to the built copies under `output/theme/css/` in the parent.

### 2b. `syntax.css` — 8 errors, suppress

`declaration-block-single-line-max-declarations` (7) and `block-no-empty` (1). `syntax.css` is
Pygments output, not hand-written, so hand-editing it would be undone the next time it is
regenerated. Suppress both rules for `**/syntax.css` through the same `overrides` mechanism.

### 2c. `poole.css` — 3 errors, fix properly

- Two `selector-pseudo-element-colon-notation` at `.post-tags li:after` and
  `.post-tags li:last-child:after`. Fixable with `npx stylelint --fix`.
- One `no-descending-specificity`: `a strong` (specificity 0,0,2) is declared at line 72, before
  `strong` (0,0,1) at line 116. This one is genuine. Because the specificities differ, `a strong`
  wins regardless of source order, so moving it is functionally inert. Move the `a strong` block
  down to sit immediately after `strong` in the "Body text" section, which also groups the two
  related rules together. Leave a comment saying why the order matters.

Keep the rule enabled everywhere else — it is meaningful in `poole.css` and only inapplicable in
the two files above.

Whoever does this needs to push to the theme fork and then update the submodule pointer here.

---

## 3. Run `validate` in CI, off the deployment path

**Status:** decided, blocked on items 1 and 2.

Once `just validate` passes, add it to `.forgejo/workflows/ci.yml`. It must **not** be able to
block a deployment: `deploy` should keep depending only on `build`, and the new job should sit
alongside it rather than in front of it. A regression should show as a red mark, not as an
undeployed site.

The job needs the build artifact and an `npm install`, since htmlhint and stylelint come from
`node_modules`.

---

## 4. Ruff tooling debt

**Status:** found while working on something else, not addressed. Three separate problems.

### 4a. Two different ruff versions

The `dev` dependency group resolves ruff **0.16.1**; `.pre-commit-config.yaml` pins the
ruff-pre-commit hook at **v0.15.7**. They disagree about which rules exist, so
`uv run --group=dev ruff check .` and `just check-precommit` can give different answers on the
same code. Pick one version and make both use it. Note that pinning the dev group was supposed to
end exactly this class of problem, so leaving the two out of step defeats it.

### 4b. `CPY001` fires under 0.16.1

`select = ["ALL"]` now enables `missing-copyright-notice`, which reports `pelicanconf.py`,
`publishconf.py`, `automation/mirror-redacted.py` and one notebook. A personal blog does not want
copyright headers. Add `CPY001` to the `ignore` list in `pyproject.toml`. CI does not currently
fail on this only because CI runs the older pre-commit-pinned ruff.

### 4c. ruff descends into `.claude/worktrees/`

`ruff check .` reports `RUF100` in `.claude/worktrees/devcontainer/publishconf.py`. That path is a
git worktree — a separate checkout, not part of this source tree. Add an `exclude` for `.claude`
in `pyproject.toml`.

---

## 5. Give the other automation scripts the same logging treatment

**Status:** not started.

`automation/mirror-redacted.py` writes a `[mirror-redacted]` prefix on every line it emits,
announces each stage of its work, and closes with a framed summary. This made a previously
unreadable job log usable, and the same would help elsewhere.

`automation/new-post.sh`, `retitle-post.sh`, `publish-post.sh` and `modify-post.sh` are
interactive shell scripts with plain `echo` output. Give them a consistent prefix and clearer
stage markers. They are user-facing rather than CI-facing, so the goal is legibility at a
terminal rather than greppability, and the design need not match exactly.

---

## 6. Decide about the `rich` version floor

**Status:** open question, no action needed unless you care.

The original combined branch raised the `automation` group's `rich` floor to `>=14.3.3`. When the
work was split up that change was not carried across, so `pyproject.toml` still says `>=14.0.0`
and the lockfile pins 14.0.0. The script runs fine on 14.0.0 in CI. Bump it or do not, but the
divergence was unintentional.

---

## 7. Housekeeping

- Around 25 remote branches have zero commits ahead of `main` and could be deleted. Several
  `automate/*` branches were abandoned in 2025 and are superseded.
- The old Makefile's `help` target documented the `make DEBUG=1 html` idiom. `just --list` shows
  that `html` takes `debug` and `relative` parameters but does not explain them. A line in
  `readme.md` would close the gap.
- Mirror runs leave their temporary config directory behind in `/tmp`. The secret mailmap inside
  it is deleted as soon as git-filter-repo has consumed it, so nothing sensitive persists, but the
  directories accumulate.
