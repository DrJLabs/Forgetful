.PHONY: format sort lint

# Variables
ISORT_OPTIONS = --profile black
PROJECT_NAME := mem0ai

# Default target
all: format sort lint

install:
	uv sync

install_all:
	uv sync --all-extras

# Format code with ruff
format:
	uv run ruff format

# Sort imports with isort
sort:
	uv run isort mem0/

# Lint code with ruff
lint:
	uv run ruff check

docs:
	cd docs && mintlify dev

build:
	uv build

publish:
	uv publish

clean:
	rm -rf dist

test:
	uv run pytest tests/

test-py-3.10:
	uv run --python 3.10 pytest tests/

test-py-3.11:
	uv run --python 3.11 pytest tests/

test-py-3.12:
	uv run --python 3.12 pytest tests/
