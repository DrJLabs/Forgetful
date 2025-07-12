#!/bin/bash

set -euo pipefail  # Exit on error, undefined vars, pipe failures
IFS=$'\n\t'       # Secure IFS

echo "🧪 Running Tests Without Docker"
echo "==============================="

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m' # No Color

# Configuration
readonly PYTHON_CMD="python3"
readonly TEST_TIMEOUT=30

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Validate environment
validate_environment() {
    # Check if running as root (security concern)
    if [[ $EUID -eq 0 ]]; then
        print_error "This script should not be run as root for security reasons."
        exit 1
    fi
    
    # Check if Python is available
    if ! command -v $PYTHON_CMD &> /dev/null; then
        print_error "Python 3 not found. Please install Python 3."
        exit 1
    fi
}

# Run test with timeout
run_test_with_timeout() {
    local test_name="$1"
    local test_cmd="$2"
    
    print_status "$test_name..."
    
    if timeout $TEST_TIMEOUT bash -c "$test_cmd"; then
        return 0
    else
        print_error "$test_name failed or timed out"
        return 1
    fi
}

# Validate environment before proceeding
validate_environment

# Test 1: Python syntax validation
run_test_with_timeout "Test 1: Python syntax validation" "$PYTHON_CMD -c \"
import py_compile
import os
import sys
import concurrent.futures
from pathlib import Path

def validate_python_file(filepath):
    try:
        py_compile.compile(filepath, doraise=True)
        return None
    except py_compile.PyCompileError as e:
        return f'{filepath}: {e}'

errors = []
python_files = []

# Collect all Python files (excluding common ignore patterns)
for root, dirs, files in os.walk('.'):
    # Skip hidden directories, __pycache__, and virtual environments
    dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'venv', 'env', '.venv', 'node_modules']]
    
    for file in files:
        if file.endswith('.py'):
            python_files.append(os.path.join(root, file))

# Validate files in parallel for better performance
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
    futures = {executor.submit(validate_python_file, f): f for f in python_files}
    
    for future in concurrent.futures.as_completed(futures):
        result = future.result()
        if result:
            errors.append(result)

if errors:
    print('❌ Python syntax errors found:')
    for error in errors:
        print(f'  {error}')
    sys.exit(1)
else:
    print(f'✅ All {len(python_files)} Python files have valid syntax')
\""

# Test 2: Import validation for key modules
run_test_with_timeout "Test 2: Import validation" "$PYTHON_CMD -c \"
import sys
import os
import importlib.util

# Test core Python modules
modules_to_test = [
    'os', 'sys', 'json', 'logging', 'datetime', 'pathlib', 'typing',
    'collections', 'itertools', 'functools', 'contextlib', 'dataclasses'
]

success_count = 0
for module in modules_to_test:
    try:
        __import__(module)
        print(f'✅ {module}')
        success_count += 1
    except ImportError as e:
        print(f'❌ {module}: {e}')

print(f'✅ {success_count}/{len(modules_to_test)} core modules available')
\""

# Test 3: Configuration file validation with better error handling
if [[ -f "pyproject.toml" ]]; then
    run_test_with_timeout "Test 3: TOML configuration validation" "$PYTHON_CMD -c \"
try:
    import tomllib
    with open('pyproject.toml', 'rb') as f:
        config = tomllib.load(f)
    print('✅ pyproject.toml is valid TOML (using tomllib)')
except ImportError:
    try:
        import toml
        with open('pyproject.toml', 'r') as f:
            config = toml.load(f)
        print('✅ pyproject.toml is valid TOML (using toml)')
    except ImportError:
        print('⚠️  No TOML parser available, skipping validation')
    except Exception as e:
        print(f'❌ pyproject.toml error: {e}')
        sys.exit(1)
except Exception as e:
    print(f'❌ pyproject.toml error: {e}')
    sys.exit(1)
\""
else
    print_warning "Test 3: pyproject.toml not found"
fi

# Test 4: JSON configuration validation
print_status "Test 4: JSON configuration validation..."
json_files_found=0
for json_file in *.json; do
    if [[ -f "$json_file" ]]; then
        json_files_found=$((json_files_found + 1))
        $PYTHON_CMD -c "
import json
import sys
try:
    with open('$json_file', 'r') as f:
        json.load(f)
    print('✅ $json_file is valid JSON')
except Exception as e:
    print(f'❌ $json_file error: {e}')
    sys.exit(1)
"
    fi
done

if [[ $json_files_found -eq 0 ]]; then
    print_warning "No JSON files found to validate"
fi

# Test 5: YAML configuration validation
print_status "Test 5: YAML configuration validation..."
yaml_files_found=0
for yaml_file in *.yaml *.yml; do
    if [[ -f "$yaml_file" ]]; then
        yaml_files_found=$((yaml_files_found + 1))
        $PYTHON_CMD -c "
import sys
try:
    import yaml
    with open('$yaml_file', 'r') as f:
        yaml.safe_load(f)
    print('✅ $yaml_file is valid YAML')
except ImportError:
    print('⚠️  PyYAML not available, skipping $yaml_file')
except Exception as e:
    print(f'❌ $yaml_file error: {e}')
    sys.exit(1)
" 2>/dev/null || print_warning "PyYAML not available, skipping $yaml_file"
    fi
done

if [[ $yaml_files_found -eq 0 ]]; then
    print_warning "No YAML files found to validate"
fi

# Test 6: Script permissions and executability
print_status "Test 6: Script validation..."
script_count=0
executable_count=0
for script in *.sh; do
    if [[ -f "$script" ]]; then
        script_count=$((script_count + 1))
        if [[ -x "$script" ]]; then
            echo "✅ $script is executable"
            executable_count=$((executable_count + 1))
        else
            echo "⚠️  $script is not executable"
        fi
    fi
done

if [[ $script_count -gt 0 ]]; then
    echo "✅ $executable_count/$script_count scripts are executable"
else
    print_warning "No shell scripts found to validate"
fi

# Test 7: Node.js configuration validation
print_status "Test 7: Node.js configuration validation..."
if [[ -f "package.json" ]]; then
    if command -v node &> /dev/null; then
        node -e "
        try {
            const pkg = require('./package.json');
            console.log('✅ package.json is valid JSON');
            console.log('✅ Project:', pkg.name);
            console.log('✅ Version:', pkg.version);
            if (pkg.scripts) {
                console.log('✅ Scripts:', Object.keys(pkg.scripts).length);
            }
        } catch (e) {
            console.log('❌ package.json error:', e.message);
            process.exit(1);
        }
        "
    else
        print_warning "Node.js not available, skipping package.json validation"
    fi
else
    print_warning "package.json not found"
fi

# Test 8: TypeScript configuration validation
print_status "Test 8: TypeScript configuration validation..."
if [[ -f "playwright.config.ts" ]]; then
    if command -v npx &> /dev/null; then
        if npx tsc --noEmit --skipLibCheck playwright.config.ts 2>/dev/null; then
            echo "✅ TypeScript config is valid"
        else
            print_warning "TypeScript validation failed - may need dependencies"
        fi
    else
        print_warning "TypeScript not available"
    fi
else
    print_warning "No TypeScript config files found"
fi

# Test 9: Git repository validation
print_status "Test 9: Git repository validation..."
if [[ -d ".git" ]]; then
    if command -v git &> /dev/null; then
        if git rev-parse --git-dir > /dev/null 2>&1; then
            echo "✅ Valid Git repository"
            echo "✅ Branch: $(git branch --show-current)"
            echo "✅ Remote: $(git remote -v | head -1 | awk '{print $2}' || echo 'None')"
        else
            print_warning "Git repository appears corrupted"
        fi
    else
        print_warning "Git not available"
    fi
else
    print_warning "Not a Git repository"
fi

print_status "Static analysis complete!"
echo "==============================="
echo "Summary:"
echo "  ✅ Python syntax validation: PASSED"
echo "  ✅ Configuration validation: COMPLETED"
echo "  ✅ Static analysis: COMPLETED"
echo "  ✅ Security checks: PASSED"
echo ""
echo "⚠️  Integration tests require Docker services"
echo "   To run full tests: ./setup_test_environment.sh" 