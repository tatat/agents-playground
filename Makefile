.PHONY: lint format check typecheck typecheck-nb check-all

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
