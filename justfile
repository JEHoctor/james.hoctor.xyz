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
_default:
    @just --list --unsorted --list-heading=$'Justfile for a Pelican web site\n\nAvailable recipes:\n'

# Internal helper to build options string
_pelican_opts debug relative port:
    #!/usr/bin/env bash
    opts=""
    [ "{{debug}}" == "1" ] && opts="$opts -D"
    [ "{{relative}}" == "1" ] && opts="$opts --relative-urls"
    [ "{{port}}" != "0" ] && opts="$opts -p {{port}}"
    echo -n "$opts"

# (re)generate the web site
html debug=DEBUG relative=RELATIVE:
    {{PELICAN}} "{{INPUTDIR}}" -o "{{OUTPUTDIR}}" -s "{{CONFFILE}}" $(just _pelican_opts {{debug}} {{relative}} {{PORT}})

# remove the generated files
clean:
    [ ! -d "{{OUTPUTDIR}}" ] || rm -rf "{{OUTPUTDIR}}"

# regenerate files upon modification
regenerate debug=DEBUG relative=RELATIVE:
    {{PELICAN}} -r "{{INPUTDIR}}" -o "{{OUTPUTDIR}}" -s "{{CONFFILE}}" $(just _pelican_opts {{debug}} {{relative}} {{PORT}})

# generate using production settings
publish debug=DEBUG:
    {{PELICAN}} "{{INPUTDIR}}" -o "{{OUTPUTDIR}}" -s "{{PUBLISHCONF}}" $(just _pelican_opts {{debug}} {{RELATIVE}} {{PORT}})

# serve site at http://localhost:8000
serve debug=DEBUG relative=RELATIVE port=PORT:
    {{PELICAN}} -l "{{INPUTDIR}}" -o "{{OUTPUTDIR}}" -s "{{CONFFILE}}" $(just _pelican_opts {{debug}} {{relative}} {{port}})

# serve (as root) to a 0.0.0.0:80
serve-global debug=DEBUG relative=RELATIVE port=PORT server=SERVER:
    {{PELICAN}} -l "{{INPUTDIR}}" -o "{{OUTPUTDIR}}" -s "{{CONFFILE}}" $(just _pelican_opts {{debug}} {{relative}} {{port}}) -b {{server}}

# serve and regenerate together
devserver debug=DEBUG relative=RELATIVE port=PORT:
    {{PELICAN}} -lr "{{INPUTDIR}}" -o "{{OUTPUTDIR}}" -s "{{CONFFILE}}" $(just _pelican_opts {{debug}} {{relative}} {{port}})

# regenerate and serve on 0.0.0.0
devserver-global debug=DEBUG relative=RELATIVE port=PORT:
    {{PELICAN}} -lr "{{INPUTDIR}}" -o "{{OUTPUTDIR}}" -s "{{CONFFILE}}" $(just _pelican_opts {{debug}} {{relative}} {{port}}) -b 0.0.0.0

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
    uv run --group=dev shfmt -d **/*.sh
    uv run --group=dev shellcheck **/*.sh

# initialize the repo for development
init:
    git submodule update --init
    uv run --group=dev pre-commit install
    (cd hyde-personalized/ && uv run --group=dev pre-commit install)
    npm install

# run pre-commit checks
check-precommit:
    uv run --group=dev pre-commit run --all-files

# validate generated HTML and CSS
validate:
    @if [ ! -d output ]; then echo "No output/ directory - run 'just html' or another similar recipe first" >&2; exit 1; fi
    npx htmlhint output/
    npx csslint output/
    npx stylelint $(find output -name '*.css')
    diff .csslintrc hyde-personalized/.csslintrc
    diff .stylelintrc.json hyde-personalized/.stylelintrc.json

# mirror repo without drafts
mirror-redacted:
    uv run --group=automation automation/mirror-redacted.py

# launch Jupyter Lab
notebook:
    uv run --group=notebook jupyter lab
