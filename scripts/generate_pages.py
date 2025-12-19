#!/usr/bin/env python3
"""Generate GitHub Pages from notebooks and source code.

Converts Jupyter notebooks to markdown and copies Python source files,
preserving directory structure.

Usage:
    python scripts/generate_pages.py [--output DIR]
"""

import argparse
import shutil
import subprocess
from pathlib import Path


def convert_notebooks(notebooks_dir: Path, output_dir: Path, config_path: Path) -> list[str]:
    """Convert Jupyter notebooks to markdown.

    Args:
        notebooks_dir: Directory containing notebooks.
        output_dir: Output directory for markdown files.
        config_path: Path to nbconvert config.

    Returns:
        List of relative page paths (without extension).
    """
    pages: list[str] = []
    output_notebooks = output_dir / "notebooks"

    for notebook in sorted(notebooks_dir.rglob("*.ipynb")):
        # Get relative path from notebooks dir
        rel_path = notebook.relative_to(notebooks_dir)
        rel_dir = rel_path.parent

        # Determine output path
        if rel_dir == Path("."):
            output_subdir = output_notebooks
            page_path = f"notebooks/{notebook.stem}"
        else:
            output_subdir = output_notebooks / rel_dir
            page_path = f"notebooks/{rel_dir}/{notebook.stem}"

        output_subdir.mkdir(parents=True, exist_ok=True)

        print(f"  Converting: {rel_path}")

        subprocess.run(
            [
                "uv", "run", "jupyter", "nbconvert",
                "--to", "markdown",
                "--output-dir", str(output_subdir),
                "--config", str(config_path),
                "--template", "plaintext",
                str(notebook),
            ],
            check=True,
            capture_output=True,
        )

        pages.append(page_path)

    return pages


def copy_source_files(source_dir: Path, output_dir: Path, package_name: str) -> list[str]:
    """Copy Python source files preserving directory structure.

    Args:
        source_dir: Source directory (e.g., agentchat/).
        output_dir: Output directory.
        package_name: Name of the package (e.g., "agentchat").

    Returns:
        List of relative file paths.
    """
    files: list[str] = []
    output_package = output_dir / package_name

    for py_file in sorted(source_dir.rglob("*.py")):
        # Get relative path from source dir
        rel_path = py_file.relative_to(source_dir)

        # Determine output path
        output_path = output_package / rel_path
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Copy file
        shutil.copy2(py_file, output_path)
        files.append(f"{package_name}/{rel_path}")

    return files


def generate_index_html(output_dir: Path, notebook_pages: list[str], source_files: list[str]) -> None:
    """Generate index.html with navigation.

    Args:
        output_dir: Output directory.
        notebook_pages: List of notebook page paths.
        source_files: List of source file paths.
    """
    # Group source files by directory
    source_tree: dict[str, list[str]] = {}
    for path in source_files:
        parts = path.split("/")
        if len(parts) >= 2:
            # Group by first subdirectory or root
            if len(parts) == 2:
                key = parts[0]  # agentchat/__init__.py -> agentchat
            else:
                key = f"{parts[0]}/{parts[1]}"  # agentchat/middleware/foo.py -> agentchat/middleware
            source_tree.setdefault(key, []).append(path)

    html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>agents-playground</title>
  <style>
    body {
      font-family: system-ui, -apple-system, sans-serif;
      max-width: 900px;
      margin: 2rem auto;
      padding: 0 1rem;
      line-height: 1.6;
    }
    h1 { border-bottom: 1px solid #ddd; padding-bottom: 0.5rem; }
    h2 { margin-top: 2rem; color: #333; }
    h3 { margin-top: 1.5rem; color: #555; font-size: 1rem; }
    ul { list-style: none; padding: 0; }
    li { margin: 0.3rem 0; }
    a { color: #0066cc; text-decoration: none; }
    a:hover { text-decoration: underline; }
    .meta { color: #666; font-size: 0.9rem; margin-top: 2rem; }
    .columns { display: flex; gap: 3rem; }
    .column { flex: 1; }
    code { background: #f5f5f5; padding: 0.1rem 0.3rem; border-radius: 3px; }
  </style>
</head>
<body>
  <h1>agents-playground</h1>
  <p>LangChain / LangGraph agent development notebooks and source code.</p>

  <div class="columns">
    <div class="column">
      <h2>Notebooks</h2>
      <ul>
"""

    for page in notebook_pages:
        name = Path(page).stem
        title = name.replace("-", " ").title()
        html += f'        <li><a href="{page}.md">{title}</a></li>\n'

    html += """      </ul>
    </div>

    <div class="column">
      <h2>Source Code</h2>
"""

    for group, files in sorted(source_tree.items()):
        group_name = group.split("/")[-1]
        html += f"      <h3><code>{group_name}/</code></h3>\n"
        html += "      <ul>\n"
        for file_path in files:
            name = Path(file_path).name
            html += f'        <li><a href="{file_path}">{name}</a></li>\n'
        html += "      </ul>\n"

    html += """    </div>
  </div>

  <p class="meta"><a href="llms.txt">llms.txt</a></p>
</body>
</html>
"""

    (output_dir / "index.html").write_text(html)


def generate_llms_txt(output_dir: Path, notebook_pages: list[str], source_files: list[str]) -> None:
    """Generate llms.txt index file.

    Args:
        output_dir: Output directory.
        notebook_pages: List of notebook page paths.
        source_files: List of source file paths.
    """
    lines = [
        "# agents-playground",
        "",
        "LangChain / LangGraph agent development notebooks and source code.",
        "",
        "## Notebooks",
        "",
    ]

    for page in notebook_pages:
        name = Path(page).stem
        title = name.replace("-", " ").title()
        lines.append(f"- [{title}]({page}.md)")

    lines.extend([
        "",
        "## Source Code",
        "",
    ])

    for file_path in source_files:
        lines.append(f"- [{file_path}]({file_path})")

    (output_dir / "llms.txt").write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate GitHub Pages from notebooks and source code."
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path("pages"),
        help="Output directory (default: ./pages)",
    )
    args = parser.parse_args()

    # Paths
    project_root = Path(__file__).parent.parent
    notebooks_dir = project_root / "notebooks"
    source_dir = project_root / "agentchat"
    config_path = project_root / "nbconvert_templates" / "config.py"
    output_dir = args.output.resolve()

    # Clean and create output directory
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    print("Generating pages...")
    print(f"  Output: {output_dir}")
    print()

    # Convert notebooks
    print("Converting notebooks...")
    notebook_pages = convert_notebooks(notebooks_dir, output_dir, config_path)
    print(f"  Converted {len(notebook_pages)} notebooks")
    print()

    # Copy source files
    print("Copying source files...")
    source_files = copy_source_files(source_dir, output_dir, "agentchat")
    print(f"  Copied {len(source_files)} files")
    print()

    # Generate index files
    print("Generating index files...")
    generate_index_html(output_dir, notebook_pages, source_files)
    generate_llms_txt(output_dir, notebook_pages, source_files)
    print()

    print(f"Done! Generated {len(notebook_pages)} notebook pages and {len(source_files)} source files")


if __name__ == "__main__":
    main()
