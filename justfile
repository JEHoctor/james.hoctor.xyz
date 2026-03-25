# Variables
PELICAN      := "uv run pelican -v"
BASEDIR      := justfile_directory()
INPUTDIR     := BASEDIR / "content"
OUTPUTDIR    := BASEDIR / "output"
CONFFILE     := BASEDIR / "pelicanconf.py"
PUBLISHCONF  := BASEDIR / "publishconf.py"

# Default flags
DEBUG        := "0"
RELATIVE     := "0"
SERVER       := "0.0.0.0"
PORT         := "0"

# List available recipes
default:
    @just --list

# Internal helper to build options string
pelican_opts:
    #!/usr/bin/env bash
    opts=""
    [ "{{DEBUG}}" == "1" ] && opts="$opts -D"
    [ "{{RELATIVE}}" == "1" ] && opts="$opts --relative-urls"
    [ "{{PORT}}" != "0" ] && opts="$opts -p {{PORT}}"
    echo -n "$opts"

# (re)generate the web site
html:
    {{PELICAN}} "{{INPUTDIR}}" -o "{{OUTPUTDIR}}" -s "{{CONFFILE}}" $(just pelican_opts)

# remove the generated files
clean:
    [ ! -d "{{OUTPUTDIR}}" ] || rm -rf "{{OUTPUTDIR}}"

# regenerate files upon modification
regenerate:
    {{PELICAN}} -r "{{INPUTDIR}}" -o "{{OUTPUTDIR}}" -s "{{CONFFILE}}" $(just pelican_opts)

# generate using production settings
publish:
    {{PELICAN}} "{{INPUTDIR}}" -o "{{OUTPUTDIR}}" -s "{{PUBLISHCONF}}" $(just pelican_opts)

# serve site locally
serve port="8000":
    {{PELICAN}} -l "{{INPUTDIR}}" -o "{{OUTPUTDIR}}" -s "{{CONFFILE}}" $(just pelican_opts) -p {{port}}

# serve (as root) to a specific server
serve-global server=SERVER:
    {{PELICAN}} -l "{{INPUTDIR}}" -o "{{OUTPUTDIR}}" -s "{{CONFFILE}}" $(just pelican_opts) -b {{server}}

# serve and regenerate together
devserver port="8000":
    {{PELICAN}} -lr "{{INPUTDIR}}" -o "{{OUTPUTDIR}}" -s "{{CONFFILE}}" $(just pelican_opts) -p {{port}}

# regenerate and serve on 0.0.0.0
devserver-global:
    {{PELICAN}} -lr "{{INPUTDIR}}" -o "{{OUTPUTDIR}}" -s "{{CONFFILE}}" $(just pelican_opts) -b 0.0.0.0

# create an empty blog post
new-post:
    @./automation/new-post.sh

# rename a blog post
retitle-post:
    @./automation/retitle-post.sh

# remove draft status and set date
publish-post:
    @./automation/publish-post.sh

# set modified date
modify-post:
    @./automation/modify-post.sh

# run ShellCheck+shfmt on all scripts
check-scripts:
    uvx --from='shfmt-py' shfmt -d **/*.sh
    uvx --from='shellcheck-py' shellcheck **/*.sh

# initialize the repo for development
init:
    git submodule update --init
    uvx --from='pre-commit' pre-commit install
    (cd hyde-personalized/ && uvx --from='pre-commit' pre-commit install)
    npm install

# run pre-commit checks
check-precommit:
    uvx --from='pre-commit' pre-commit run --all-files

# validate generated HTML and CSS
validate:
    @if [ ! -d output ]; then echo "No output/ directory - run 'just html' first" >&2; exit 1; fi
    npx htmlhint output/
    npx csslint output/
    npx stylelint $(find output -name '*.css')
    diff .csslintrc hyde-personalized/.csslintrc
    diff .stylelintrc.json hyde-personalized/.stylelintrc.json

# mirror repo without drafts
mirror-redacted:
    @./automation/mirror-redacted.sh

# launch Jupyter Lab
notebook:
    uv run --group=notebook jupyter lab
