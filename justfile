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

# AI agent sandbox (sandcat: https://github.com/VirtusLab/sandcat) -- a
# network-isolated, credential-scrubbed container for running coding agents in
# autonomous mode.
#
# Host requirements:
#   * the sandcat CLI on PATH. It has no tagged releases (rolling main); these
#     recipes were tested against commit 53089985b506f5cb82886eb4e08b6ce6fc2fb8c8.
#   * Mike Farah's Go yq (https://github.com/mikefarah/yq), which sandcat uses
#     to edit compose files. The unrelated Python yq (kislyuk/yq) will not work,
#     and is what `apt install yq` gives you on Debian/Ubuntu.
#
# Assumes a conventional rootful Docker daemon. Rootless Docker is not
# supported: it remaps container UIDs, which leaves the bind-mounted workspace
# read-only inside the sandbox, and sandcat has no handling for it.
#
# Commands go through sudo so this works whether or not the invoking user is in
# the docker group. PATH and HOME are passed through because sudo's secure_path
# hides sandcat and yq, and a reset HOME points sandcat at the wrong settings.
SANDBOX_NAME := "james-hoctor-xyz"
SANDCAT      := 'sudo env "PATH=$PATH" "HOME=$HOME" "DOCKER_HOST=unix:///var/run/docker.sock"'

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

# open a shell in the network-isolated AI agent sandbox
sandbox:
    {{SANDCAT}} sandcat run

# rebuild the sandbox image, then open a shell in it
sandbox-build:
    {{SANDCAT}} sandcat run --build

# open an extra shell in an already-running sandbox
sandbox-attach:
    {{SANDCAT}} sandcat attach

# stop the sandbox
sandbox-down:
    {{SANDCAT}} sandcat compose down

# show the mitmproxy UI for inspecting sandbox traffic
sandbox-proxy:
    {{SANDCAT}} sandcat proxy

# (re)generate the sandbox config, re-applying our hardening patch
sandbox-init:
    #!/usr/bin/env bash
    set -euo pipefail
    sandcat init --agent claude --ide vscode --stacks "python" --name {{SANDBOX_NAME}} --features no-shared-cache
    # sandcat regenerates .devcontainer/ on every init and only devbox.tools.json
    # is tracked, so the hardening has to be re-applied each time. See the
    # SANDCAT comment block above for why this matters.
    if grep -q 'sandcat hardening' .devcontainer/Dockerfile.app; then
        echo "hardening already present"
    else
        printf '\n%s\n%s\n%s\n%s\n%s\n' \
            '# --- sandcat hardening (re-applied by `just sandbox-init`) ---' \
            '# The devcontainers base image grants vscode passwordless sudo, and' \
            '# under a rootful daemon container root IS host root. Drop both the' \
            '# sudoers grant and the setuid bit so the agent cannot escalate.' \
            'USER root' \
            'RUN rm -f /etc/sudoers.d/vscode && chmod u-s /usr/bin/sudo' \
            >> .devcontainer/Dockerfile.app
        echo "hardening appended to .devcontainer/Dockerfile.app"
    fi
