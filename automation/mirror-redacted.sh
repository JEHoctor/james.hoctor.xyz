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
uvx --with='git-filter-repo' git-filter-repo --source . --target "$tmpdir" --paths-from-file <(cat <<- EOF
	regex:^(?!content/).*$

	$(while read -r file; do
		echo "literal:$file"
	done < <(find content/ -type f -not -execdir grep -q '^Status: draft$' '{}' \; -print))
EOF
)

# Remove branches that are merged into main in the target repository, but not in the local repository.
while read -r branch; do
	local_branch="$(echo "$branch" | sed 's/origin\///')"
	if git -C "$tmpdir" merge-base --is-ancestor "$branch" origin/main; then
		echo "Removing merged branch: $branch"
		git -C "$tmpdir" branch -rD "$branch"
		git -C "$tmpdir" branch -D "$local_branch" || true
	fi
done < <(git branch -r --no-merged origin/main 'origin/*')

# We have to check out each of the branches that wasn't removed in the previous step.
while read -r branch; do
	local_branch="$(echo "$branch" | sed 's/origin\///')"
	echo "Checking out branch: $branch"
	git -C "$tmpdir" checkout "$local_branch"
done < <(git -C "$tmpdir" branch -r --list 'origin/*' | grep -v 'HEAD')

# Push the changes to the target repository.
git -C "$tmpdir" push --force --mirror --prune origin

# Remove the temporary directory.
rm -rf "$tmpdir"
