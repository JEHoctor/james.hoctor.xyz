#!/usr/bin/bash

# This script should only be run via make to ensure correct paths!

# Not using -x because this script interacts with the user.
set -euo pipefail

# Collect blog post title from the user.
read -erp "Title: " title

# Check for collision with titles of existing posts and pages, which can prevent Pelican from building the site.
if grep -q "^Title: $title$" content/{*,**/*}.md; then
	echo "Duplicate post title identified by grep:"
	grep "^Title: $title$" content/{*,**/*}.md
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
if [ -f "$filename" ]; then
	echo "File already exists: $filename"
	exit 1
fi

# Create a new post file using a heredoc as a template.
cat <<- EOF > "$filename"
	Title: $title
	Date: $(date '+%Y-%m-%d %H:%M')
	Category: Blog
	Status: draft
EOF
