#!/bin/bash

# This script should only be run via make to ensure correct paths!

# Not using -x because this script interacts with the user.
set -euo pipefail

# Collect file name from the user.
read -i "content/" -erp "File name of post: " filename

# Verify that the file exists.
if [[ ! -f $filename ]]; then
  echo "File does not exist: $filename" >&2
  exit 1
fi

# Verify that there is exactly one status line and one date line in the file.
if [[ $(grep -c '^Status: ' "$filename") != 1 ]]; then
  echo "File does not have exactly one status line: $filename" >&2
  grep --line-number --context=2 '^Status: ' "$filename" >&2
  exit 1
fi
if [[ $(grep -c '^Date: ' "$filename") != 1 ]]; then
  echo "File does not have exactly one date line: $filename" >&2
  grep --line-number --context=2 '^Date: ' "$filename" >&2
  exit 1
fi

# Check that the current status is "draft".
if ! grep -q '^Status: draft$' "$filename"; then
  echo "File is not a draft: $filename" >&2
  grep --line-number --context=2 '^Status: ' "$filename" >&2
  exit 1
fi

# Replace the status with "published", and the date with the current date.
sed -i -e 's/^Status: draft$/Status: published/' -e 's/^Date: .*$/Date: '"$(date '+%Y-%m-%d %H:%M')/" "$filename"
