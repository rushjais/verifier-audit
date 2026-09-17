check:
	uv run ruff format --check .
	uv run ruff check .
	uv run pytest -q

fmt:
	uv run ruff format .
	uv run ruff check --fix .

.PHONY: check fmt
