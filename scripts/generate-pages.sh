#!/bin/bash
# Generate markdown pages from Jupyter notebooks
# Usage: ./scripts/generate-pages.sh [--output DIR]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
NOTEBOOKS_DIR="$PROJECT_ROOT/notebooks"
OUTPUT_DIR="$PROJECT_ROOT/pages"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --output|-o)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [--output DIR]"
            echo ""
            echo "Convert Jupyter notebooks to markdown and generate llms.txt"
            echo ""
            echo "Options:"
            echo "  --output, -o DIR  Output directory (default: ./pages)"
            echo "  --help, -h        Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
    esac
done

# Create output directory
mkdir -p "$OUTPUT_DIR"

echo "Converting notebooks to markdown..."
echo "  Source: $NOTEBOOKS_DIR"
echo "  Output: $OUTPUT_DIR"
echo ""

# Track converted files for llms.txt
declare -a PAGES=()

# Convert each notebook (including subdirectories)
while IFS= read -r -d '' notebook; do
    # Get relative path from notebooks dir
    rel_path="${notebook#$NOTEBOOKS_DIR/}"
    rel_dir=$(dirname "$rel_path")
    basename=$(basename "$notebook" .ipynb)

    # Determine output path (preserve directory structure under notebooks/)
    if [[ "$rel_dir" == "." ]]; then
        output_subdir="$OUTPUT_DIR/notebooks"
        page_path="notebooks/$basename"
    else
        output_subdir="$OUTPUT_DIR/notebooks/$rel_dir"
        page_path="notebooks/$rel_dir/$basename"
    fi

    mkdir -p "$output_subdir"

    echo "  Converting: $rel_path -> ${page_path}.md"

    uv run jupyter nbconvert \
        --to markdown \
        --output-dir "$output_subdir" \
        --config "$PROJECT_ROOT/nbconvert_templates/config.py" \
        --template plaintext \
        "$notebook"

    PAGES+=("$page_path")
done < <(find "$NOTEBOOKS_DIR" -name "*.ipynb" -type f -print0 | sort -z)

echo ""
echo "Generating llms.txt and index.html..."

# Generate llms.txt
cat > "$OUTPUT_DIR/llms.txt" << EOF
# agents-playground

LangChain / LangGraph agent development notebooks.

## Pages

EOF

# Generate index.html
cat > "$OUTPUT_DIR/index.html" << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>agents-playground</title>
  <style>
    body {
      font-family: system-ui, -apple-system, sans-serif;
      max-width: 800px;
      margin: 2rem auto;
      padding: 0 1rem;
      line-height: 1.6;
    }
    h1 { border-bottom: 1px solid #ddd; padding-bottom: 0.5rem; }
    ul { list-style: none; padding: 0; }
    li { margin: 0.5rem 0; }
    a { color: #0066cc; text-decoration: none; }
    a:hover { text-decoration: underline; }
    .meta { color: #666; font-size: 0.9rem; margin-top: 2rem; }
  </style>
</head>
<body>
  <h1>agents-playground</h1>
  <p>LangChain / LangGraph agent development notebooks.</p>
  <h2>Notebooks</h2>
  <ul>
EOF

for page in "${PAGES[@]}"; do
    # Create a title from the filename (replace hyphens with spaces, capitalize)
    # Use only the basename for title
    name=$(basename "$page")
    title=$(echo "$name" | sed 's/-/ /g' | awk '{for(i=1;i<=NF;i++) $i=toupper(substr($i,1,1)) substr($i,2)}1')
    echo "- [$title](${page}.md)" >> "$OUTPUT_DIR/llms.txt"
    echo "    <li><a href=\"${page}.md\">$title</a></li>" >> "$OUTPUT_DIR/index.html"
done

cat >> "$OUTPUT_DIR/index.html" << 'EOF'
  </ul>
  <p class="meta"><a href="llms.txt">llms.txt</a></p>
</body>
</html>
EOF

echo ""
echo "Done! Generated ${#PAGES[@]} pages, llms.txt, and index.html"
