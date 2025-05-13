#!/bin/bash

# This script should only be run via make to ensure correct paths!

set -euxo pipefail

# This script should only be run from the main branch.
if [[ $(git branch --show-current) != "main" ]]; then
  echo "Must mirror from the main branch." >&2
  exit 1
fi

# Create a clone of the target repository in a temporary directory.
tmpdir=$(mktemp -d)
git clone "$MIRROR_ACCESS_URL" "$tmpdir"

# Run git-filter-repo to redact draft posts.
uvx --with='git-filter-repo' git-filter-repo --source . --target "$tmpdir" \
  --mailmap <(echo "$SECRET_MAILMAP") \
  --paths-from-file <(
    cat <<- EOF
	regex:^(?!content/).*$

	$(while read -r file; do
      echo "literal:$file"
    done < <(find content/ -type f -not -execdir grep -q '^Status: draft$' '{}' \; -print))
EOF
  )

# Remove branches that are merged into main in the target repository, but not in the source repository.
while read -r branch; do
  if git -C "$tmpdir" merge-base --is-ancestor "$branch" origin/main; then
    echo "Removing merged branch: $branch"
    git -C "$tmpdir" branch -rD "$branch"
    local_branch=$(echo "$branch" | sed 's/origin\///')
    git -C "$tmpdir" branch -D "$local_branch" || true
  fi
done < <(git branch -r --no-merged origin/main 'origin/*')

#######################################
# Find commits that are parents of a merge commit, other than the merge base. In other words, heads of merged branches.
# Only commits that are reachable from HEAD are included, so an appropriate branch should be checked out first.
# Arguments:
#   Path to the repository
# Outputs:
#   Writes commit hashes one per line to stdout
#######################################
merged_commits() {
  git -C "$1" log --merges --oneline --no-abbrev-commit \
    | cut -d' ' -f1 \
    | xargs -n1 git -C "$1" rev-list --parents -n1 \
    | cut -d' ' -f3- \
    | xargs -n1
}

# Remove branches that are merged into main via a merge commit in the source repository, but merged without
# a merge commit in the target repository.
source_merged_commits=$(merged_commits .)
target_merged_commits=$(merged_commits "$tmpdir")
while read -r branch; do
  source_branch_commit=$(git rev-parse --verify "$branch^{commit}")
  target_branch_commit=$(git -C "$tmpdir" rev-parse --verify "$branch^{commit}")
  if (echo "$source_merged_commits" | grep -q "$source_branch_commit") \
    && ! (echo "$target_merged_commits" | grep -q "$target_branch_commit"); then
    echo "Removing merged branch: $branch"
    git -C "$tmpdir" branch -rD "$branch"
    local_branch=$(echo "$branch" | sed 's/origin\///')
    git -C "$tmpdir" branch -D "$local_branch" || true
  fi
done < <(git -C "$tmpdir" branch -r --merged origin/main 'origin/*' | grep -v 'origin/main')

# We have to check out each of the branches that wasn't removed in the previous steps.
while read -r branch; do
  local_branch="$(echo "$branch" | sed 's/origin\///')"
  echo "Checking out branch: $branch"
  git -C "$tmpdir" checkout "$local_branch"
done < <(git -C "$tmpdir" branch -r --list 'origin/*' | grep -v 'HEAD')

# Push the changes to the target repository.
git -C "$tmpdir" push --force --mirror --prune origin

# Remove the temporary directory.
rm -rf "$tmpdir"
