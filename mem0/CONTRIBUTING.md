# Contributing to mem0

Let us make contribution easy, collaborative and fun.

## Submit your Contribution through PR

To make a contribution, follow these steps:

1. Fork and clone this repository
2. Do the changes on your fork with dedicated feature branch `feature/f1`
3. If you modified the code (new feature or bug-fix), please add tests for it
4. Include proper documentation / docstring and examples to run the feature
5. Ensure that all tests pass
6. Submit a pull request

For more details about pull requests, please read [GitHub's guides](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request).

## Development Setup

We use `uv` for managing development environments. To set up:

```bash
# Install uv (if not already installed)
pipx install uv

# Install all dependencies including dev dependencies
uv sync

# Install with specific optional dependencies
uv sync --extra graph  # For graph memory features
uv sync --extra llms   # For LLM integrations
uv sync --all-extras   # Install all optional dependencies

# Run commands in the virtual environment
uv run python your_script.py
uv run pytest tests/
```

### 📌 Pre-commit

To ensure our standards, make sure to install pre-commit before starting to contribute.

```bash
pre-commit install
```

## Running Tests

```bash
# Run all tests
make test

# Run tests with specific Python version
make test-py-3.10  # Python 3.10
make test-py-3.11  # Python 3.11
make test-py-3.12  # Python 3.12

# Or directly with uv
uv run pytest tests/
uv run --python 3.11 pytest tests/
```

Make sure that all tests pass across all supported Python versions before submitting a pull request.

We look forward to your pull requests and can't wait to see your contributions!
