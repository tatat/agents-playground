# AGENTS.md

This file provides guidance to AI coding agents when working with code in this repository.

## Commands

```bash
make check-all   # Run before commit (lint + typecheck including notebooks)
make format      # Auto-format with ruff
make nb2md NB=notebooks/example.ipynb  # Convert notebook to LLM-friendly markdown
```

Note: If `make` doesn't work, try `command make` or use full path.

## Workspace

Use `tmp/` (project root) for temporary files and debugging. This directory is gitignored.

## Stack

- Python 3.13, uv
- LangChain / LangGraph for agent development
- Jupyter notebooks in `notebooks/`
- mypy strict mode with pydantic plugin
- ruff for linting/formatting

## Style

- Comments and documentation in English
- File naming: `snake_case` for Python files, `kebab-case` for others

## Type Annotations

See `docs/types.md`

## Documentation

Reference links below are HTML (for humans). When reading docs, append `.md` for LLM-optimized markdown.

- LangChain: https://docs.langchain.com
  - Index: https://docs.langchain.com/llms.txt
  - Example: `/persistence` → read `/persistence.md`
- Anthropic Claude: https://platform.claude.com/docs
  - Index: https://platform.claude.com/llms.txt
  - Example: `/en/docs/agents-and-tools/tool-use` → read `/en/docs/agents-and-tools/tool-use.md`
