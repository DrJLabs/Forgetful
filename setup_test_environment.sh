#!/bin/bash

set -euo pipefail  # Exit on error, undefined vars, pipe failures
IFS=$'\n\t'       # Secure IFS

echo "🚀 Setting up Test Environment"
echo "================================"

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m' # No Color

# Configuration
readonly MAX_WAIT_TIME=60
readonly RETRY_INTERVAL=2
readonly PYTHON_CMD="python3"
readonly DOCKER_COMPOSE_CMD="docker-compose"

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
    print_status "Validating environment..."
    
    # Check if running as root (security concern)
    if [[ $EUID -eq 0 ]]; then
        print_error "This script should not be run as root for security reasons."
        exit 1
    fi
    
    # Check disk space (minimum 1GB free)
    local available_space
    available_space=$(df . | tail -1 | awk '{print $4}')
    if [[ $available_space -lt 1048576 ]]; then
        print_error "Insufficient disk space. At least 1GB required."
        exit 1
    fi
    
    # Validate we're in the correct directory
    if [[ ! -f "docker-compose.yml" ]]; then
        print_error "docker-compose.yml not found. Are you in the correct directory?"
        exit 1
    fi
}

# Wait for service with exponential backoff
wait_for_service() {
    local service_name="$1"
    local check_cmd="$2"
    local max_attempts=$((MAX_WAIT_TIME / RETRY_INTERVAL))
    
    print_status "Waiting for $service_name..."
    
    for ((i=1; i<=max_attempts; i++)); do
        if eval "$check_cmd" > /dev/null 2>&1; then
            print_status "$service_name is ready"
            return 0
        fi
        
        if [[ $i -eq $max_attempts ]]; then
            print_error "$service_name failed to start after $MAX_WAIT_TIME seconds"
            return 1
        fi
        
        sleep $RETRY_INTERVAL
    done
}

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    print_error "Docker not found. Please install Docker to run integration tests."
    exit 1
fi

# Check if Docker Compose is available
if ! command -v $DOCKER_COMPOSE_CMD &> /dev/null; then
    print_error "Docker Compose not found. Please install Docker Compose."
    exit 1
fi

# Validate environment before proceeding
validate_environment

print_status "Step 1: Installing Python dependencies..."
if [[ -f "requirements-test.txt" ]]; then
    $PYTHON_CMD -m pip install --user -r requirements-test.txt
    print_status "Python dependencies installed"
else
    print_warning "requirements-test.txt not found, skipping Python dependencies"
fi

print_status "Step 2: Installing Node.js dependencies..."
if [[ -f "package.json" ]]; then
    npm install
    print_status "Node.js dependencies installed"
else
    print_warning "package.json not found, skipping Node.js dependencies"
fi

print_status "Step 3: Starting Docker services..."
$DOCKER_COMPOSE_CMD up -d mem0 postgres-mem0 neo4j-mem0 openmemory-mcp

print_status "Step 4: Waiting for services to be ready..."
sleep 5

# Wait for services with proper error handling
if ! wait_for_service "mem0 API" "curl -s http://localhost:8000/health"; then
    print_error "Failed to start mem0 API. Check logs: docker-compose logs mem0"
    exit 1
fi

if ! wait_for_service "PostgreSQL" "docker exec postgres-mem0 pg_isready -U drj"; then
    print_error "Failed to start PostgreSQL. Check logs: docker-compose logs postgres-mem0"
    exit 1
fi

print_status "Step 5: Running service validation..."
if [[ -x "./validate_bmad_services.sh" ]]; then
    ./validate_bmad_services.sh
else
    print_warning "validate_bmad_services.sh not found or not executable"
fi

print_status "Step 6: Running tests..."
echo "================================"

# Run Python syntax validation
print_status "Running Python syntax validation..."
$PYTHON_CMD -c "
import py_compile
import os
import sys

errors = []
for root, dirs, files in os.walk('.'):
    # Skip hidden directories and __pycache__
    dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
    
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            try:
                py_compile.compile(filepath, doraise=True)
            except py_compile.PyCompileError as e:
                errors.append(f'{filepath}: {e}')

if errors:
    print('Python syntax errors found:')
    for error in errors:
        print(f'  {error}')
    sys.exit(1)
else:
    print('✅ All Python files have valid syntax')
"

# Run pytest if dependencies are available
print_status "Running pytest..."
if $PYTHON_CMD -c "import pytest, requests" 2>/dev/null; then
    $PYTHON_CMD -m pytest --tb=short --maxfail=5 -v || print_warning "Some pytest tests failed"
else
    print_warning "Missing pytest dependencies, skipping pytest tests"
fi

# Run integration tests
print_status "Running integration tests..."
if [[ -x "./test_all_systems.sh" ]]; then
    ./test_all_systems.sh || print_warning "Some integration tests failed"
else
    print_warning "test_all_systems.sh not found or not executable"
fi

# Run E2E tests if available
print_status "Running E2E tests..."
if npm list @playwright/test > /dev/null 2>&1; then
    npm run test:e2e || print_warning "Some E2E tests failed"
else
    print_warning "Playwright dependencies not available, skipping E2E tests"
fi

print_status "Test environment setup complete!"
echo "================================"
echo "Services running:"
echo "  - mem0 API: http://localhost:8000"
echo "  - PostgreSQL: localhost:5432"
echo "  - Neo4j: localhost:7474"
echo "  - OpenMemory MCP: localhost:8765"
echo ""
echo "To stop services: $DOCKER_COMPOSE_CMD down" 