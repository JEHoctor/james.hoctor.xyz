#!/usr/bin/bash

# This script should only be run via make to ensure correct paths!

# Not using -x because this script interacts with the user.
set -euo pipefail

# Collect old file name from the user.
read -i "content/" -erp "Old file name: " old_filename

# Verify that the file exists.
if [ ! -f "$old_filename" ]; then
	echo "File does not exist: $old_filename"
	exit 1
fi

# Collect new blog post title from the user.
read -erp "New title: " new_title

# Rename the old file so it won't be searched by grep, and is available for the user to recover.
mv "$old_filename" "$old_filename".old

# Check for collision with titles of existing posts and pages, which can prevent Pelican from building the site.
if grep -q "^Title: $new_title$" content/{*,**/*}.md; then
	set +e # Don't exit if grep (or echo) fails
	echo "Duplicate post title identified by grep:"
	grep "^Title: $new_title$" content/{*,**/*}.md
	set -e
	mv "$old_filename".old "$old_filename"
	exit 1
fi

# Prepare a file path from the title by:
# - replacing spaces with hyphens
# - converting to lowercase
# - prepending "content/"
# - appending ".md"
# For example, "Hello World" becomes "content/hello-world.md"
filename=content/$(echo "$new_title" | sed 's/ /-/g' | tr '[:upper:]' '[:lower:]').md

# Verify that the file doesn't already exist.
if [ -f "$filename" ]; then
	set +e # Don't exit if echo fails
	echo "File already exists: $filename"
	set -e
	mv "$old_filename".old "$old_filename"
	exit 1
fi

# Replace the old title with the new title, and write to the new filename.
sed "s/^Title: .*$/Title: $new_title/" "$old_filename".old > "$filename"

# Print next steps for the user.
echo "Next steps:"
echo "  - diff $filename $old_filename.old"
echo "  - git add $filename $old_filename"
echo "  - rm $old_filename.old"