# Loose ends

Work that is understood but not done. Each item says what the problem is, what was decided, and
what is left. Read `CLAUDE.md` first for how to operate in this repository.

This file is published to the GitHub mirror. **Anything that names or describes an unpublished
draft belongs in `private/TODO.md` instead**, which the mirroring script withholds in full.

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
