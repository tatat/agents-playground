.PHONY: lint format check typecheck typecheck-nb check-all nb2md pages

lint:
	uv run ruff check .

format:
	uv run ruff format .

typecheck:
	uv run mypy --sqlite-cache .

typecheck-nb:
	uv run nbqa mypy --sqlite-cache notebooks/

check: lint typecheck

check-all: check typecheck-nb

# Convert notebook to LLM-friendly markdown (no HTML, no ANSI)
# Usage: make nb2md NB=notebooks/example.ipynb
nb2md:
	@uv run jupyter nbconvert --to markdown --stdout --config nbconvert_templates/config.py --template plaintext $(NB)

# Generate pages from notebooks with llms.txt
# Usage: make pages [OUTPUT=./pages]
pages:
	@./scripts/generate-pages.sh $(if $(OUTPUT),--output $(OUTPUT),)
