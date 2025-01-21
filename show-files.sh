#!/bin/bash

# Use provided path or current directory if none provided
TARGET_PATH="${1:-.}"

# Print current directory tree
echo "=== Directory Structure for: $TARGET_PATH ==="
tree "$TARGET_PATH"
echo ""

# Find and display all regular files
echo "=== File Contents ==="
find "$TARGET_PATH" -type f ! -path "*/\.*" -print0 | while IFS= read -r -d '' file; do
    echo "=== File: $file ==="
    cat "$file"
    echo "===================="
    echo ""
done
