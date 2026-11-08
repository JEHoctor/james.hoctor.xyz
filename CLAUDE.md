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
just test            # pytest: front-matter parser and the mirror's publication rule
just validate        # htmlhint/stylelint over output/ (also runs in CI, off the deploy path)
just init            # pre-commit hooks, npm install
just new-post        # also retitle-post, publish-post, modify-post -> `blog post ...`
just mirror-preview  # what the mirror would publish if this branch were main (dry run)
```

`automation/` is a uv workspace member, `blog-automation`, providing the `blog` command
(`blog post new|retitle|publish|modify`, `blog mirror [--dry-run]`). Run it as
`uv run --group=automation blog ...` from the repository root — both subcommands refuse to run
anywhere else, and they act on the checkout you are standing in. Its code is under
`automation/src/blog_automation/` with its tests in `automation/tests/`; `tests/` at the root holds
the checks that read the real `content/` tree (every post round-trips through the parser, every
post has a recognised status). `just test` runs both.

## Post metadata

Every file under `content/` starts with a YAML front-matter block fenced by `---`, which
pandoc-reader requires. Values are double-quoted (`date: "2025-04-24 11:27"` is ambiguous YAML
unquoted, and `"True"` would become a boolean). `blog_automation/frontmatter.py` is the one parser for
this block, used by both the post CLI and the mirror script so the two cannot disagree; it uses
ruamel.yaml in round-trip mode, so editing a key preserves everything else byte for byte
(`tests/test_frontmatter.py` proves this against every real post). Do not edit headers with `sed`.

The post commands are `blog post new|retitle|publish|modify` (`blog_automation/post.py`), run via
`just`. `new` names the file with Pelican's own slugify of the title, so file, URL and any
`<slug>.bib` sidecar agree. `retitle` is deliberately careful: it writes the new file (and a copy
of the sidecar), leaves the old ones as `.old`, and prints the diff/rm commands for you to run.

Development tooling is pinned in dependency groups, so prefix with the group when calling a tool
directly: `uv run --group=dev ruff check .`. Groups are `dev`, `automation` (just the `blog`
command) and `notebook`.

Note that `uv run --group=X` syncs the environment to exactly that group, so alternating between
groups reinstalls packages each time. That is expected, not a fault.

## The mirror, and the invariant that matters

`blog mirror` (`automation/src/blog_automation/mirror.py`) publishes a filtered copy of this
repository to GitHub. The
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
branches. The `mirror` job checks out `main` regardless of which branch triggered it, so a change
to the script or to post metadata is only exercised for real after it merges. That is what the
**`mirror-preview`** job is for.

### Reviewing `mirror-preview` — required reading before merging

`mirror-preview` runs on every non-main push. It executes the *branch's* checkout of the script
with `--dry-run` against a read-only clone of the public mirror, so its log shows exactly what
the mirror would publish if that branch were `main`. It is a **required status check** for
merging into `main`, but it is designed to be *read*, not to gate: it only fails if the script
errors or refuses to push. A green tick means nothing on its own. Before merging any PR, open the
job's log (`tea api` recipe in the handbook; the job is named `mirror-preview`) and check:

1. `Publishing N post(s)` — the list must be exactly the posts you expect to be public. For a PR
   that publishes nothing, it must equal what `main` publishes today.
2. `Compared with the mirror's current main, this run newly publishes N post(s)` — normally 0; for
   a publish PR, exactly the one post being published. `WARNING:` lines here (more than one new
   post, or a post being withdrawn) need an explanation in the PR before merging.
3. `Withholding N post(s)` — every draft, each with `(status: draft)`. A different status, or
   `none`, means a header the script did not understand; that post is withheld, which is the safe
   direction, but the header should be fixed. A sidecar listed under "no post of the same name" is
   almost always a rename leftover — delete or rename it.
4. `Verified N branch(es)` present, and no `REFUSING TO PUSH`.

The one fact this job cannot show you is how the *merged* result differs from the branch, so
merge PRs that touch `content/` or the script one at a time.

### Developing the mirror script or its workflow

**For any other change, do not run this: read the `mirror-preview` log as described above.** That
is simpler and more reliable, because it uses the real mirror and mailmap. The recipe below is only
for changing `automation/src/blog_automation/mirror.py` or the workflow that runs it.

It never touches the real mirror: its target is a local bare repository, with a synthetic mailmap.
The first run really pushes `main`'s filtered result there, as a baseline. The second dry-runs your
commit against that baseline. Run the whole block from the repository root, with your change
committed, because the clone does not see uncommitted work:

```bash
REPO=$PWD
SB=$(mktemp -d)
git clone -q "$REPO" "$SB/clone"
cd "$SB/clone"
git fetch -q "$REPO" '+refs/remotes/origin/*:refs/remotes/origin/*'
git checkout -q --detach               # the commit under test, which `checkout -` returns to
git checkout -q -B main origin/main    # filter-repo only rewrites branches that exist locally
git init -q --bare -b main "$SB/mirror"
git push -q "$SB/mirror" main          # the script needs the mirror to have a main
# file:// because after a push, filter-repo rejects a plain path's clone as not fresh
export MIRROR_ACCESS_URL="file://$SB/mirror"
export SECRET_MAILMAP="Redacted <redacted@example.invalid> <real@example.com>"
uv run --group=automation blog mirror &&
  git checkout -q - &&
  uv run --group=automation blog mirror --dry-run
```

Only the last run's output means anything: the first compares against an unfiltered seed, so it
reports every branch as changed and warns about withdrawn posts. Git-filter-repo rewrites
deterministically, so in the last `SUMMARY`, `0 branch(es) changed` means your commit publishes
exactly what `main` does and any branch listed really differs. If a change you believe is cosmetic
moves every hash, something is wrong. To exercise a change to the push itself, replace the final
dry run with `git checkout -q -B main && uv run --group=automation blog mirror`, since the script
refuses a real run off `main`, then inspect `$SB/mirror`. Remove `$SB` when done.

## SEO: what the plugins actually do

Four things here are not guessable from the code, and each one cost real time.

- **`pelican-seo`'s `noindex:` and `disallow:` front-matter keys never emit a meta tag.** They
  only add lines to a robots.txt the plugin generates (`seo_enhancer/__init__.py`). Both sat on
  `content/pages/404.md` for months doing nothing. The real directive is
  `<meta name="robots" content="noindex, follow">`, which `base.html` now emits from the same
  `noindex` key. The value is compared as a lowercased string against `"true"`, because these
  headers are quoted and a bare truthiness test would accept `"False"` as a request to de-index;
  that makes any other spelling a silent no-op, which `tests/test_meta_descriptions.py` guards.
- **`content/extra/robots.txt` wins over the generated one by signal ordering, not by luck.** The
  plugin writes robots.txt on `all_generators_finalized`, which fires *before* static files are
  copied, so the static copy lands on top. This is what keeps the plugin's non-standard
  `Noindex:` lines (Google dropped support in 2019; Bing never had it) out of the deployed file.
  There is no setting to disable just the robots.txt generation — `SEO_ENHANCER` also drives the
  canonical tags — so the ordering is checked instead, by `tests/check_built_site.py`.
- **Sitemap `exclude` patterns have no leading slash.** The plugin writes `SITEURL + "/" + pageurl`
  and matches the patterns against `pageurl`, so `"^/drafts/"` matched nothing for as long as it
  was there; drafts stayed out only because of the plugin's separate status check. A page that is
  `published` but `noindex` must be named in `SITEMAP["exclude"]`, or the sitemap asks a crawler
  to index a URL the page then tells it not to. `tests/check_built_site.py` fails the build on
  that contradiction rather than trusting the config to be remembered.
- **`seo_report.html` reads front matter, not the rendered page.** It reports "You need to declare
  a description" for any post without a `description:` key, even though the theme renders a good
  one from the post's summary, and it only ever looks at articles and pages — never the home page
  or the listing templates, which is why it never flagged what Bing did. Its own recommended
  window is `range(150, 161)`, which is where the numbers in `pelicanconf.py` come from. Generated
  by `just html` (`SEO_REPORT` is on in `pelicanconf.py`, off in `publishconf.py`) and gitignored.

## Environment quirks that have bitten before

- **Every job uses `runs-on: node24`, not `docker`.** The runner maps `node24` to
  `node:24-bookworm` and `docker` to `node:20-bullseye`. Bullseye cannot run this workflow: its git
  2.30 lacks the `git ls-files --deduplicate` that `pre-commit run --all-files` calls (added in git
  2.31), and `apt-get install rsync` stops on a 404 because the `bullseye-security` index lists a
  package that has gone from Debian's pool.
- **A change to `runs-on` reaches the real mirror on push.** `ci.yml` comes from the pushed branch,
  so the `mirror` job uses a branch's new workflow and image while checking out `main`. Before
  changing the image, use the recipe under "Developing the mirror script or its workflow" with the
  baseline on the old image and the dry run on the new: a different git must not change the
  rewritten hashes, so it must report `0 branch(es) changed`.
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
- **Rich markup is disabled** in `mirror.py`. It would otherwise read a bracketed word,
  including the log prefix and any path containing a bracket, as a style tag and silently drop it.
- **Cloudflare rewrites `user@host` text into a `[email protected]` link.** The site is served through
  Cloudflare, whose email obfuscation replaces anything that looks like an address, code blocks
  included, with a link that only decodes once its JavaScript runs. `curl`, reader modes and
  no-JS clients see the placeholder, so a pasted command breaks. Wrap such a block in
  `<!--email_off-->` and `<!--/email_off-->` on their own lines, outside the code fence; Cloudflare
  removes the markers from the served page, so their absence in the live HTML is expected. A
  local build or `just serve` cannot show whether it worked, since Cloudflare is not in front of
  them; it only shows the markers survive pandoc. Check after deploying with
  `curl -s <post url> | grep -c cf_email` (want 0) and read the code block's text in the raw HTML.
  The client rsync command in the rsync-transfers post is the worked example. Explain the markers
  with a markdown comment, `[//]: # (why)`, not an HTML one: Cloudflare strips only the markers,
  so an ordinary HTML comment would ship to readers. Pandoc drops the unused reference, which
  `grep -c` on the built HTML confirms.
- **Cloudflare and browsers cache static assets for hours under their URL** (`/theme/css/*.css`
  is `max-age=14400`, `cf-cache-status: HIT`); HTML is `DYNAMIC`, so a new URL in the HTML takes
  effect at once. The theme's own stylesheets and scripts are therefore linked through the
  `hashed_theme_asset` filter (`pelicanconf.py`), which appends `?v=<hash of the file>`, so a change
  to them needs no version bump and no purge. A new stylesheet or script in `base.html` must go
  through it too. Not versioned, and so possibly stale for hours after a deploy: images, favicons
  and everything else linked by a plain URL. To check for a stale asset, request the plain URL and
  the same URL with a cache-busting query (`?nocache=$RANDOM`) and compare the bodies and `cf-cache-status`: an old
  body on `HIT` beside a new one on `MISS` is the edge cache, not a failed deploy.
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
- Every post and page declares a `status` in its front matter: `published`, `hidden` (pages that
  are built but not listed) or `draft`. The mirror **fails closed** on it: a file is published
  only if the header parses and says `published` or `hidden`; a draft, an unknown value, a missing
  status (`none`) or an unparseable header (`unreadable`) are all withheld and listed in the log
  with what the script saw. If you change how metadata is written, read the `mirror-preview` job's
  log before merging (see above) — an earlier fail-open check once matched nothing and put every
  draft on GitHub.
