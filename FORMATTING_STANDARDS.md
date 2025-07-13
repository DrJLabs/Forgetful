# Code Formatting Standards & Setup Guide

## Overview

This document describes the code formatting standards and automated setup for the mem0-stack project. These standards ensure consistent code formatting across all environments and prevent the recurring formatting issues that were identified in CI/CD pipelines.

## 🔧 **Root Cause Analysis**

The formatting issues were caused by:
1. **Line ending inconsistencies** between local (Windows) and CI (Linux) environments
2. **Missing configuration files** for consistent formatting
3. **Lack of automated enforcement** via pre-commit hooks
4. **Environment-specific tool behavior** differences

## 📋 **Implemented Solutions**

### 1. **EditorConfig Configuration** (`.editorconfig`)
- Enforces consistent line endings (`lf`) across all file types
- Standardizes indentation, character encoding, and whitespace handling
- Supports Python, JavaScript, YAML, SQL, and other file types

### 2. **Git Attributes** (`.gitattributes`)
- Forces line ending normalization to LF in git repository
- Prevents line ending inconsistencies during checkout/commit
- Handles binary files appropriately

### 3. **Python Formatting** (`pyproject.toml`)
- **Black**: Code formatting with 88 character line length
- **isort**: Import sorting with black-compatible profile
- **flake8**: Linting with consistent rules
- **mypy**: Type checking configuration

### 4. **Pre-commit Hooks** (`.pre-commit-config.yaml`)
- Automated formatting checks before each commit
- Comprehensive validation including:
  - Code formatting (black, isort)
  - Linting (flake8)
  - Security scanning (bandit)
  - YAML/JSON validation
  - Shell script checking

### 5. **CI/CD Integration** (`.github/workflows/test.yml`)
- Updated GitHub Actions workflow with:
  - Consistent git configuration
  - Pre-commit hook validation
  - Environment-specific line ending handling

## 🛠️ **Setup Instructions**

### For New Developers

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd mem0-stack
   ```

2. **Install pre-commit** (if not already installed):
   ```bash
   pipx install pre-commit
   # or
   pip install pre-commit --user
   ```

3. **Install pre-commit hooks**:
   ```bash
   pre-commit install
   ```

4. **Configure git** (to ensure consistent behavior):
   ```bash
   git config core.autocrlf false
   git config core.eol lf
   git config core.filemode false
   ```

### For Existing Developers

1. **Update your local repository**:
   ```bash
   git pull origin main
   ```

2. **Install/update pre-commit hooks**:
   ```bash
   pre-commit install
   pre-commit autoupdate
   ```

3. **Run formatting on all files** (one-time):
   ```bash
   black openmemory/ shared/ tests/
   python3 -m isort openmemory/ shared/ tests/ --profile black
   ```

## 📏 **Formatting Rules**

### Python Code
- **Line length**: 88 characters (Black default)
- **Indentation**: 4 spaces
- **Line endings**: LF (Unix style)
- **Import sorting**: isort with black profile
- **String quotes**: Double quotes preferred
- **Trailing commas**: Enforced in multiline structures

### Other File Types
- **JavaScript/TypeScript**: 2 spaces indentation
- **YAML**: 2 spaces indentation
- **JSON**: 2 spaces indentation
- **SQL**: 2 spaces indentation
- **Shell scripts**: 2 spaces indentation

## 🚀 **Automated Enforcement**

### Pre-commit Hooks
The following checks run automatically before each commit:
- **Formatting**: Black, isort
- **Linting**: flake8
- **Security**: bandit
- **Type checking**: mypy
- **File validation**: YAML, JSON, line endings
- **Shell scripts**: shellcheck

### CI/CD Pipeline
The GitHub Actions workflow includes:
- **Quality Gate 7**: Comprehensive code quality checks
- **Environment consistency**: Standardized git configuration
- **Multi-environment validation**: Both local and CI environments

## 🐛 **Troubleshooting**

### Common Issues

1. **Line ending errors in CI**:
   ```bash
   git config --global core.autocrlf false
   git config --global core.eol lf
   git add -A
   git commit -m "Fix line endings"
   ```

2. **Pre-commit hook failures**:
   ```bash
   pre-commit run --all-files
   # Fix any issues reported, then:
   git add -A
   git commit -m "Fix formatting issues"
   ```

3. **Import sorting issues**:
   ```bash
   python3 -m isort openmemory/ shared/ tests/ --profile black
   ```

4. **Black formatting issues**:
   ```bash
   black openmemory/ shared/ tests/
   ```

### Validation Commands

Test your setup with these commands:

```bash
# Test formatting
black --check openmemory/ shared/ tests/

# Test import sorting
python3 -m isort openmemory/ shared/ tests/ --profile black --check-only

# Test pre-commit hooks
pre-commit run --all-files

# Test specific file
pre-commit run --files path/to/file.py
```

## 📊 **Benefits**

1. **Consistency**: All code follows the same formatting standards
2. **Reduced conflicts**: Fewer merge conflicts due to formatting differences
3. **Faster reviews**: Reviewers can focus on logic, not formatting
4. **Automated enforcement**: Catches issues before they reach CI
5. **Cross-platform compatibility**: Works on Windows, macOS, and Linux

## 🔄 **Maintenance**

### Regular Updates
- Update pre-commit hooks monthly: `pre-commit autoupdate`
- Review and update formatting rules as needed
- Monitor CI/CD pipeline for new formatting issues

### Adding New File Types
1. Update `.editorconfig` with new file patterns
2. Add appropriate entries to `.gitattributes`
3. Update pre-commit hooks if needed
4. Test with sample files

## 📚 **References**

- [EditorConfig](https://editorconfig.org/)
- [Black Code Formatter](https://black.readthedocs.io/)
- [isort Import Sorter](https://pycqa.github.io/isort/)
- [Pre-commit Framework](https://pre-commit.com/)
- [Git Attributes](https://git-scm.com/docs/gitattributes)

## 🆘 **Support**

If you encounter formatting issues:
1. Check this documentation first
2. Run the validation commands
3. Review CI/CD logs for specific error messages
4. Contact the development team if issues persist

---

**Last Updated**: $(date)
**Version**: 1.0
**Status**: ✅ Active
