# Migration Guide: Poetry/Hatch to uv

This guide helps you migrate from the previous dependency management setup (Poetry/Hatch) to the new uv-based workflow.

## What Changed?

- **Dependency Manager**: Switched from Poetry/Hatch to uv
- **Lock File**: `poetry.lock` → `uv.lock`
- **Virtual Environment**: Automatically managed by uv in `.venv`
- **Python Version**: Minimum Python version updated from 3.9 to 3.10
- **Commands**: All `hatch run` and `poetry` commands replaced with `uv run`

## Migration Steps

### 1. Install uv

```bash
# Using pipx (recommended)
pipx install uv

# Or using pip
pip install uv
```

### 2. Clean Up Old Environment

```bash
# Remove old virtual environments
rm -rf .venv
rm -rf poetry.lock
rm -rf .hatch/

# If you have a backup of pyproject.toml
rm pyproject.toml.backup
```

### 3. Set Up New Environment

```bash
# Clone the latest version of the repository
git pull

# Install dependencies
uv sync

# Install with optional dependencies
uv sync --extra graph      # Graph memory features
uv sync --extra llms       # LLM integrations
uv sync --extra vector-stores  # Vector store integrations
uv sync --all-extras       # All optional dependencies
```

## Command Mapping

| Old Command | New Command |
|-------------|-------------|
| `poetry install` | `uv sync` |
| `poetry add <package>` | `uv add <package>` |
| `poetry remove <package>` | `uv remove <package>` |
| `poetry run python` | `uv run python` |
| `hatch shell` | `source .venv/bin/activate` or use `uv run` |
| `hatch run format` | `uv run ruff format` |
| `hatch run lint` | `uv run ruff check` |
| `hatch run test` | `uv run pytest tests/` |
| `hatch build` | `uv build` |
| `hatch publish` | `uv publish` |

## Development Workflow

### Running Code
```bash
# Instead of activating virtual environment
uv run python your_script.py
uv run jupyter notebook
uv run pytest tests/
```

### Adding Dependencies
```bash
# Add a regular dependency
uv add requests

# Add a development dependency
uv add --dev pytest

# Add to optional dependencies
uv add --optional graph neo4j
```

### Building and Publishing
```bash
# Build package
uv build

# Publish to PyPI
uv publish
```

## Benefits of uv

1. **Speed**: 10-100x faster than pip for dependency resolution
2. **Simplicity**: No manual virtual environment activation needed
3. **Reproducibility**: Lock file ensures consistent environments
4. **Compatibility**: Works with standard pyproject.toml
5. **Modern**: Actively developed with excellent performance

## Troubleshooting

### Issue: Dependencies not installing
```bash
# Clear uv cache and reinstall
uv cache clean
uv sync --refresh
```

### Issue: Python version conflicts
Make sure you have Python 3.10 or newer:
```bash
python --version
# Should show Python 3.10.x or newer
```

### Issue: Import errors
Ensure you're using `uv run`:
```bash
# Wrong
python script.py

# Correct
uv run python script.py
```

## Need Help?

If you encounter any issues during migration, please:
1. Check the [uv documentation](https://github.com/astral-sh/uv)
2. Open an issue in the repository
3. Reach out to the maintainers 