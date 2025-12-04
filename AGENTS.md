# AGENTS.md

This file provides guidance to AI coding agents when working with code in this repository.

## Commands

```bash
make check-all   # Run before commit (lint + typecheck including notebooks)
make format      # Auto-format with ruff
```

Note: If `make` doesn't work, try `command make` or use full path.

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

- LangChain docs index: https://docs.langchain.com/llms.txt
- For HTML version, remove `.md` from URL (e.g., `/persistence.md` → `/persistence`)
