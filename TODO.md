# Loose ends

Work that is understood but not done. Each item says what the problem is, what was decided, and
what is left. Read `CLAUDE.md` first for how to operate in this repository.

This file is published to the GitHub mirror. **Anything that names or describes an unpublished
draft belongs in `private/TODO.md` instead**, which the mirroring script withholds in full.

`todo.txt` predates this file and both of its items are long finished (the favicon exists, the
theme is forked). It can be deleted.

---

## 1. Housekeeping

- The actions in `.forgejo/workflows/ci.yml` are pinned to commit SHAs, with the tag they
  corresponded to in a trailing comment. Nothing bumps them automatically (no Renovate on the
  forge), so re-resolve them now and then: `git ls-remote --tags <action-url>` for the
  code.forgejo.org ones, `gh api repos/astral-sh/setup-uv/git/ref/tags/v6` (then peel the tag
  object) for setup-uv. Newer majors already exist for all four (checkout v7, upload-artifact v5,
  download-artifact v7); moving majors is a separate decision from refreshing pins.
- Around 25 remote branches have zero commits ahead of `main` and could be deleted. Several
  `automate/*` branches were abandoned in 2025 and are superseded.
- Mirror runs leave their temporary config directory behind in `/tmp`. The secret mailmap inside
  it is deleted as soon as git-filter-repo has consumed it, so nothing sensitive persists, but the
  directories accumulate.

---

## 2. Improve `mirror-redacted.py`

- In mirror(), source_dir is set to ".", but at the top of the script we explicitly anchor to REPO_ROOT. This looks like it could cause a mismatch.
- With `git push`, `--mirror` may imply `--prune`.
- Streamline plan_published_paths and the functions called in that call tree. The
  plan_published_paths function has a nice design where it collects information, logs some
  information, and then returns what its caller needs. But, it also repeats the rglob of CONTENT_DIR
  to find excluded drafts. The whole call tree under extra_paths_to_include exists to serve
  plan_published_paths, so it can be reworked a bit to avoid this. plan_published_paths needs
  categorized file lists/sets to log, and then it can select which to pass to its caller (caller
  does not get excluded_drafts).
