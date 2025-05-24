# James Hoctor's blog

I use this repo to manage the content on my blog: [james.hoctor.xyz](https://james.hoctor.xyz/).
I also deploy the blog using a [Forgejo Actions workflow](.forgejo/workflows/ci.yml) running on my private git forge.
The workflow doesn't run on GitHub, and likely wouldn't work with GitHub Actions.

If you are viewing this on GitHub, then you are looking at a copy, which is downstream of the working copy on my forge.
The copy on GitHub is redacted using this [script](automation/mirror-redacted.sh), whose purpose is to remove draft posts from the git history until they are published.
The redacted copy will regularly receive force pushes that rewrite its history, so it is not suitable for forking.

The site is built with [Pelican](https://getpelican.com/), a static site generator.
The Python environment and tools are managed with [uv](https://docs.astral.sh/uv).

Before beginning development, install the pre-commit hooks and the submodule with `make init`.

## Credit

I generated the favicon package with https://realfavicongenerator.net/.
