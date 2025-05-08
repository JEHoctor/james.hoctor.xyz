#!/bin/bash

# This script should only be run via make to ensure correct paths!

# Using -x because this script runs a bunch of git commands.
set -euxo pipefail

# Check for an environment variable containing the git ssh url of the deployment remote.
if [ -z "${REMOTE_URL:-}" ]; then
    # Ask the user for the git ssh url of the deployment remote.
    read -erp "Deployment remote (ssh clone url as displayed on Forgejo): " REMOTE_URL
fi

# Ensure that this url is associated with a git remote called "deploy".
if ! git remote add deploy "$REMOTE_URL"; then
    if [ "$(git remote get-url deploy)" != "$REMOTE_URL" ]; then
        echo 'Failed to add remote "deploy": remote already exists with a different url.'
        exit 1
    fi
fi

# Fetch the remote, including all branches.
# From the git-fetch(1) man page, it would seem like --depth=1 would work here, but I think --deepen=1 is working better for me.
git fetch --no-tags --deepen=1 deploy "+refs/heads/*:refs/remotes/deploy/*"

# Fetch the remote's main branch at full depth. git interprets 2147483647 to mean "infinite depth".
git fetch --no-tags --depth=2147483647 deploy "+refs/heads/main:refs/remotes/deploy/main"

# Create a temporary directory for git worktrees.
temp_dir=$(mktemp -d)

# Create a git worktree for the remote's main branch in the temp dir.
git worktree add -fd "$temp_dir/main" "deploy/main"

for branch in $(git branch -r --no-merged deploy/main 'deploy/*' | grep -v '^deploy/HEAD'); do
    # Extract the branch name.
    branch_name=$(echo "$branch" | sed 's/deploy\///')

    # Create a git worktree for this branch in the temp dir.
    git worktree add -fd "$temp_dir/$branch_name" "$branch"

    # Find drafts in the worktree and copy them to the main worktree.
	find "$temp_dir/$branch_name/content/" -type f -name '*.md' -execdir grep -q '^Status: draft$' '{}' \; -print0 | xargs -0 -I'{}' cp '{}' "$temp_dir/main/content/"

    # Clean up the worktree.
    git worktree remove "$temp_dir/$branch_name"
done

# Run make publish in the worktree for branch "main".
make -C "$temp_dir/main" -f "$temp_dir/main/Makefile" "${DRAFTS_BUILD_TARGET:-html}"

# Copy drafts in the temp dir to the output dir.
mkdir -p "$temp_dir/main/output/drafts" output/drafts
cp -rT "$temp_dir/main/output/drafts" output/drafts

# Clean up the main worktree. We have to use force because the worktree will contain uncommitted changes.
git worktree remove --force "$temp_dir/main"

# Remove the temp dir.
rm -rf "$temp_dir"
