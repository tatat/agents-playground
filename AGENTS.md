# AGENTS.md

This file provides guidance to AI coding agents when working with code in this repository.

## Commands

```bash
make check-all   # Run before commit (lint + typecheck including notebooks)
make format      # Auto-format with ruff
```

## Stack

- Python 3.13, uv
- LangChain / LangGraph for agent development
- Jupyter notebooks in `notebooks/`
- mypy strict mode with pydantic plugin
- ruff for linting/formatting

## Style

- Comments and documentation in English

## Type Annotations

See `docs/types.md`
