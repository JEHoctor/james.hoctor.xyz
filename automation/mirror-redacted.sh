#!/bin/bash

# This script should only be run via make to ensure correct paths!

set -euxo pipefail

# This script should only be run from the main branch.
if [ "$(git branch --show-current)" != "main" ]; then
	echo "Must mirror from the main branch."
	exit 1
fi

# Create a clone of the target repository in a temporary directory.
tmpdir=$(mktemp -d)
git clone "$MIRROR_ACCESS_URL" "$tmpdir"

# Run git-filter-repo to redact draft posts.
uvx --with='git-filter-repo' git-filter-repo --source . --target "$tmpdir" --paths-from-file <<- EOF
	regex:^(?!content/).*$

	$(while read -r file; do
		echo "literal:$file"
	done < <(find content/ -type f -not -execdir grep -q '^Status: draft$' '{}' \; -print))
EOF

# Push the changes to the target repository.
git -C "$tmpdir" push

# Remove the temporary directory.
rm -rf "$tmpdir"
