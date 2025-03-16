#!/bin/bash

# Use provided path or current directory if none provided
TARGET_PATH="${1:-.}"

# Print current directory tree
echo "=== Directory Structure for: $TARGET_PATH ==="
tree "$TARGET_PATH"
echo ""

# Function to display file content, with special handling for JSON files
display_file_content() {
    local file="$1"

    # Check if file is a binary or image file
    if file "$file" | grep -qE 'binary|executable|image data|shared object|compiled'; then
        echo "=== File: $file (BINARY/IMAGE - content not displayed) ==="
        echo "[Binary or image file - content skipped]"
    # Check if file is a JSON file (by extension)
    elif [[ "$file" == *.json ]]; then
        # Get character count
        local char_count=$(wc -c < "$file")

        echo "=== File: $file (JSON, $char_count characters) ==="

        if [ "$char_count" -gt 200 ]; then
            # Truncate to first 200 characters and add indication
            head -c 200 "$file"
            echo "... [truncated, total $char_count characters]"
        else
            # Display entire file if less than 200 characters
            cat "$file"
        fi
    else
        # For regular text files, display as normal
        echo "=== File: $file ==="
        cat "$file"
    fi

    echo "===================="
    echo ""
}

# Find and display all regular files
echo "=== File Contents ==="
find "$TARGET_PATH" -type f ! -path "*/\.*" -print0 | while IFS= read -r -d '' file; do
    display_file_content "$file"
done
