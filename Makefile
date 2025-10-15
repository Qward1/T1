.PHONY: dev fmt test lint

dev:
	uvicorn backend.api:app --reload --port 8000

fmt:
	ruff check backend tests --fix
	black backend tests

lint:
	ruff check backend tests

test:
	pytest
