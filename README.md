# agents-playground

Experimental repository for LangChain / LangGraph agents.

## Setup

```bash
uv sync
cp .env.sample .env  # Set ANTHROPIC_API_KEY
uv run pre-commit install
```

## Usage

```bash
# Jupyter Notebook
uv run jupyter notebook

# Run script
uv run python main.py
```

## Development

```bash
make lint        # ruff check
make format      # ruff format
make typecheck   # mypy
make typecheck-nb # mypy (notebooks)
make check       # lint + typecheck
make check-all   # check + typecheck-nb
```

`make check-all` runs automatically via pre-commit hook.
