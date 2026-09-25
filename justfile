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

# The `blog` command lives in the automation/ workspace member; `uv run` keeps it in sync.
BLOG := "uv run --group=automation blog"

# create an empty blog post
new-post:
    @{{BLOG}} post new

# rename a blog post (keeps .old copies for you to diff and remove)
retitle-post:
    @{{BLOG}} post retitle

# remove draft status and set date
publish-post:
    @{{BLOG}} post publish

# set modified date
modify-post:
    @{{BLOG}} post modify

# initialize the repo for development
init:
    uv run --group=dev pre-commit install
    npm install

# run pre-commit checks
check-precommit:
    uv run --group=dev pre-commit run --all-files

# run the test suite (front matter parser, mirror publication rule)
test:
    uv run --group=dev --group=automation pytest

# validate generated HTML and CSS, and check robots.txt and sitemap.xml against the built pages
# (see tests/check_built_site.py for what those last checks are defending)
validate:
    @if [ ! -d output ]; then echo "No output/ directory - run 'just html' or another similar recipe first" >&2; exit 1; fi
    npx htmlhint output/
    npx stylelint $(find output -name '*.css')
    uv run --group=dev python tests/check_built_site.py

# mirror repo without drafts
mirror-redacted:
    {{BLOG}} mirror

# show what the mirror would publish if this branch were main (what CI's mirror-preview job runs)
mirror-preview:
    {{BLOG}} mirror --dry-run

# launch Jupyter Lab
notebook:
    uv run --group=notebook jupyter lab
