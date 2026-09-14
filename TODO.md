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
- delete `.csslintrc`
- remove the csslint dependency from `package.json` and re-lock
- remove `csslint` and `csslintrc` from `cSpell.words` in `.vscode/settings.json`

The theme's own copy of `.csslintrc` and its csslint pre-commit hook went away when the theme was
vendored into `hyde-personalized/`; only the top-level ones remain.

---

## 2. Fix the stylelint errors

**Status:** analysed in full, not applied. **Blocks:** `just validate`, item 3.

`npx stylelint hyde-personalized/static/css/*.css` reports 18 errors. They fall into three groups
and need three different treatments.

### 2a. `no-descending-specificity` in `hyde.css` — 7 errors, suppress

These compare rules from different theme colour variants, e.g. `.theme-base-09 .content a`
against `.theme-base-08 .related-posts li a:hover`. `templates/base.html` puts exactly one
`theme-base-*` class on `<body>`, and there are eight variants, so two variants can never apply
to the same document and no cascade conflict is possible. These are false positives.

Reordering to satisfy the rule would mean abandoning the file's one-block-per-colour layout for
no benefit. Suppress it for this file instead, via an `overrides` entry in `.stylelintrc.json`
matching `**/hyde.css`. Use a glob rather than a fixed path: the same config is applied both to
the sources in `hyde-personalized/` and to the built copies under `output/theme/css/`.

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

The theme used to run stylelint as a pre-commit hook of its own; that hook was dropped along with
the submodule, so until this item is done nothing lints the theme's CSS at commit time.

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

## 7. Housekeeping

- Around 25 remote branches have zero commits ahead of `main` and could be deleted. Several
  `automate/*` branches were abandoned in 2025 and are superseded.
- Mirror runs leave their temporary config directory behind in `/tmp`. The secret mailmap inside
  it is deleted as soon as git-filter-repo has consumed it, so nothing sensitive persists, but the
  directories accumulate.

---

## 8. Improve `mirror-redacted.py`

- Improve the parsing of metadata at the head of content markdown files. How does Pelican do it?
- Require the presence of a status in the metadata and validate its value.
- Hide posts with statuses other than "published" defensively.
- In mirror(), source_dir is set to ".", but at the top of the script we explicitly anchor to REPO_ROOT. This looks like it could cause a mismatch.
- With `git push`, `--mirror` may imply `--prune`.
- Streamline plan_published_paths and the functions called in that call tree. The
  plan_published_paths function has a nice design where it collects information, logs some
  information, and then returns what its caller needs. But, it also repeats the rglob of CONTENT_DIR
  to find excluded drafts. The whole call tree under extra_paths_to_include exists to serve
  plan_published_paths, so it can be reworked a bit to avoid this. plan_published_paths needs
  categorized file lists/sets to log, and then it can select which to pass to its caller (caller
  does not get excluded_drafts).
