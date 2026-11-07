.PHONY: fmt lint test check up down clean

fmt:
	uv run ruff format .

lint:
	uv run ruff check .
	uv run mypy src

test:
	uv run pytest

check:
	uv run ruff format --check .
	$(MAKE) lint
	$(MAKE) test

up:
	docker compose up -d --wait

down:
	docker compose down

clean:
	docker compose down -v
