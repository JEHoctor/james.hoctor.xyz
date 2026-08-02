#!/bin/bash

# This script should only be run via just to ensure correct paths!

# Not using -x because this script interacts with the user.
set -euo pipefail

# These scripts are read at a terminal rather than in a job log, so the prefix is here to separate
# the script's own words from the output of anything it calls, not to be grepped for.
readonly LOG_PREFIX="[new-post]"

log() {
  printf '%s %s\n' "$LOG_PREFIX" "$*"
}

err() {
  printf '%s %s\n' "$LOG_PREFIX" "$*" >&2
}

# Collect blog post title from the user.
read -erp "Title: " title

# Check for collision with titles of existing posts and pages, which can prevent Pelican from building the site.
if grep -q "^Title: $title$" content/{*,**/*}.md; then
  err "A post or page already uses that title:"
  grep --line-number --with-filename "^Title: $title$" content/{*,**/*}.md >&2
  exit 1
fi

# Prepare a file path from the title by:
# - replacing spaces with hyphens
# - converting to lowercase
# - prepending "content/"
# - appending ".md"
# For example, "Hello World" becomes "content/hello-world.md"
filename=content/$(echo "$title" | sed 's/ /-/g' | tr '[:upper:]' '[:lower:]').md

# Verify that the file doesn't already exist.
if [[ -f $filename ]]; then
  err "File already exists: $filename"
  exit 1
fi

# Create a new post file using a heredoc as a template.
cat <<- EOF > "$filename"
	Title: $title
	Date: $(date '+%Y-%m-%d %H:%M')
	Category: Blog
	Status: draft
EOF

log "Created $filename"
log "It is a draft, so it will not be published or mirrored until you change Status."
