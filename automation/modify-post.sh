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

# Check that the current status is "published".
if ! grep -q '^Status: published$' "$filename"; then
  echo "File is not published: $filename" >&2
  grep --line-number --context=2 '^Status: ' "$filename" >&2
  exit 1
fi

# If the file does not have a modified line, then create one after the date line.
# Otherwise, replace the date on the modified line.
if ! grep -q '^Modified: ' "$filename"; then
  sed -i -e '/^Date: /a\Modified: '"$(date '+%Y-%m-%d %H:%M')" "$filename"
else
  sed -i -e 's/^Modified: .*$/Modified: '"$(date '+%Y-%m-%d %H:%M')/" "$filename"
fi
