#!/bin/bash

# Initialize variables
TARGET_PATH="."
EXCLUDE_PATTERNS=()

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--exclude)
            EXCLUDE_PATTERNS+=("$2")
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [TARGET_PATH] [-e|--exclude PATTERN]..."
            echo ""
            echo "Options:"
            echo "  TARGET_PATH              Directory to scan (default: current directory)"
            echo "  -e, --exclude PATTERN    Exclude files/folders matching PATTERN (can be used multiple times)"
            echo "  -h, --help               Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 /path/to/dir"
            echo "  $0 /path/to/dir -e node_modules -e '*.log'"
            echo "  $0 . -e soyspray-venv -e kubespray"
            exit 0
            ;;
        *)
            TARGET_PATH="$1"
            shift
            ;;
    esac
done

# Extract basename from path and generate timestamp
BASENAME=$(basename "$TARGET_PATH")
TIMESTAMP=$(date +%Y-%m-%d-%H-%M-%S)
OUTPUT_FILE="${BASENAME}-${TIMESTAMP}.txt"

# Print message to stderr before redirecting stdout
echo "Saving output to: $OUTPUT_FILE" >&2
if [ ${#EXCLUDE_PATTERNS[@]} -gt 0 ]; then
    echo "Excluding patterns: ${EXCLUDE_PATTERNS[*]}" >&2
fi

# Redirect all output to the file
exec > "$OUTPUT_FILE"

# Build tree exclude options
TREE_EXCLUDE=""
for pattern in "${EXCLUDE_PATTERNS[@]}"; do
    TREE_EXCLUDE="$TREE_EXCLUDE -I '$pattern'"
done

# Print current directory tree
echo "=== Directory Structure for: $TARGET_PATH ==="
if [ -n "$TREE_EXCLUDE" ]; then
    eval "tree $TREE_EXCLUDE '$TARGET_PATH'"
else
    tree "$TARGET_PATH"
fi
echo ""

# Function to display file content, with special handling for JSON files
display_file_content() {
    local file="$1"
    local char_count
    local line_count

    # Check file extension first (more reliable than file command)
    # Check if file is a JSON file (by extension)
    if [[ "$file" == *.json ]]; then
        line_count=$(wc -l < "$file")
        echo "=== File: $file (JSON, $line_count lines) ==="
        if [ "$line_count" -gt 1000 ]; then
            head -n 1000 "$file"
            echo "... [truncated, total $line_count lines]"
        else
            cat "$file"
        fi
    # Check if file is a Markdown file (by extension)
    elif [[ "$file" == *.md ]]; then
        line_count=$(wc -l < "$file")
        echo "=== File: $file (Markdown, $line_count lines) ==="
        if [ "$line_count" -gt 1000 ]; then
            head -n 1000 "$file"
            echo "... [truncated, total $line_count lines]"
        else
            cat "$file"
        fi
    # Check if file is a YAML file (by extension)
    elif [[ "$file" == *.yaml || "$file" == *.yml ]]; then
        line_count=$(wc -l < "$file")
        echo "=== File: $file (YAML, $line_count lines, comments stripped) ==="
        # Remove full-line comments and trailing comments
        sed -e '/^[[:space:]]*#/d' -e 's/[[:space:]]*#.*$//' "$file"
    # Check if file is a binary or image file (after extension checks)
    elif file "$file" | grep -qE 'binary|executable|image data|shared object|compiled'; then
        echo "=== File: $file (BINARY/IMAGE - content not displayed) ==="
        echo "[Binary or image file - content skipped]"
    else
        # For other regular text files, display as normal
        line_count=$(wc -l < "$file")
        echo "=== File: $file (Text, $line_count lines) ==="
        cat "$file"
    fi

    echo "===================="
    echo ""
}

# Build find exclude options
FIND_EXCLUDE_ARGS=()
for pattern in "${EXCLUDE_PATTERNS[@]}"; do
    # Handle both directory names and file patterns
    FIND_EXCLUDE_ARGS+=(-not -path "*/$pattern/*" -not -path "*/$pattern" -not -name "$pattern")
done

# Find and display all regular files
echo "=== File Contents ==="
find "$TARGET_PATH" -type f ! -path "*/\.*" "${FIND_EXCLUDE_ARGS[@]}" -print0 | while IFS= read -r -d '' file; do
    display_file_content "$file"
done
