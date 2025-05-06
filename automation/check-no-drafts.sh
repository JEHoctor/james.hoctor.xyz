#!/bin/bash

# This script should only be run via make to ensure correct paths!

set -euo pipefail

drafts="$(find content/ -type f -name '*.md' -execdir grep -q '^Status: draft$' '{}' \; -print)"

# If $drafts is not empty, then there are draft posts.
if [ -n "$drafts" ]; then
	echo "Failure: draft posts should not be merged into main. See the list below:"
	echo "$drafts"
	exit 1
fi
echo "Success!"
