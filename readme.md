# James Hoctor's blog

I use this repo to manage the content on my blog: [james.hoctor.xyz](https://james.hoctor.xyz/).
I also deploy the blog using a [Forgejo Actions workflow](.forgejo/workflows/ci.yml) running on my private git forge.
The workflow doesn't run on GitHub, and likely wouldn't work with GitHub Actions.

If you are viewing this on GitHub, then you are looking at a copy, which is downstream of the working copy on my forge.
The copy on GitHub is redacted using this [script](automation/mirror-redacted.py), whose purpose is to remove draft posts from the git history until they are published.
The redacted copy will regularly receive force pushes that rewrite its history, so it is not suitable for forking.

The site is built with [Pelican](https://getpelican.com/), a static site generator.
The Python environment and tools are managed with [uv](https://docs.astral.sh/uv).
The Node.js environment is managed with [fnm](https://github.com/Schniz/fnm).

Before beginning development, install the pre-commit hooks with `just init`.
Run `just` on its own to list the recipes.
Build recipes such as `html`, `regenerate`, `serve` and `devserver` take two optional positional
parameters, `debug` and `relative`, whose defaults come from the `DEBUG` and `RELATIVE` variables.
`just DEBUG=1 html` passes `-D` to Pelican for debug-level logging (and makes it print a full
traceback instead of a one-line `CRITICAL`), and `just RELATIVE=1 html` passes `--relative-urls` so
the output can be browsed from the local filesystem. They combine: `just DEBUG=1 RELATIVE=1 serve`.

## Credit

I generated the favicon package with https://realfavicongenerator.net/.
