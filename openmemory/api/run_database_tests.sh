#!/bin/bash

# Database Test Runner Script
# Runs comprehensive database tests with proper environment setup

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Test configuration
TEST_DB_NAME="test_db"
TEST_USER="postgres"
TEST_PASSWORD="testpass"
TEST_HOST="localhost"
TEST_PORT="5432"

# Default values
RUN_MIGRATION_TESTS=false
RUN_TRANSACTION_TESTS=false
RUN_PERFORMANCE_TESTS=false
CLEAN_DATABASE=false
VERBOSE=false
COVERAGE=false

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_header() {
    echo -e "\n${BLUE}============================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================${NC}\n"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  --migration-tests     Run migration integrity tests"
    echo "  --transaction-tests   Run transaction rollback tests"
    echo "  --performance-tests   Run database performance tests"
    echo "  --clean              Clean database before running tests"
    echo "  --verbose            Enable verbose output"
    echo "  --coverage           Generate coverage reports"
    echo "  --all                Run all test types"
    echo "  --help               Show this help message"
    echo
    echo "Examples:"
    echo "  $0 --migration-tests --verbose"
    echo "  $0 --all --coverage"
    echo "  $0 --clean --transaction-tests"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --migration-tests)
            RUN_MIGRATION_TESTS=true
            shift
            ;;
        --transaction-tests)
            RUN_TRANSACTION_TESTS=true
            shift
            ;;
        --performance-tests)
            RUN_PERFORMANCE_TESTS=true
            shift
            ;;
        --clean)
            CLEAN_DATABASE=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --coverage)
            COVERAGE=true
            shift
            ;;
        --all)
            RUN_MIGRATION_TESTS=true
            RUN_TRANSACTION_TESTS=true
            RUN_PERFORMANCE_TESTS=true
            shift
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# If no specific tests selected, run basic tests
if [[ "$RUN_MIGRATION_TESTS" == false && "$RUN_TRANSACTION_TESTS" == false && "$RUN_PERFORMANCE_TESTS" == false ]]; then
    RUN_MIGRATION_TESTS=true
    RUN_TRANSACTION_TESTS=true
fi

# Function to check prerequisites
check_prerequisites() {
    print_header "CHECKING PREREQUISITES"

    # Check if we're in the right directory
    if [[ ! -f "main.py" ]]; then
        print_error "main.py not found. Please run from the OpenMemory API directory."
        exit 1
    fi

    # Check if pytest is available
    if ! command -v pytest &> /dev/null; then
        print_error "pytest not found. Please install pytest."
        exit 1
    fi

    # Check if PostgreSQL client is available
    if ! command -v psql &> /dev/null; then
        print_warning "psql not found. Some database operations may fail."
    fi

    print_success "Prerequisites check completed"
}

# Function to detect environment
detect_environment() {
    print_header "DETECTING ENVIRONMENT"

    IS_CI=${CI:-false}
    IS_TESTING=${TESTING:-false}
    IS_DOCKER=false

    if [[ -f /.dockerenv ]]; then
        IS_DOCKER=true
    fi

    print_info "Environment: CI=$IS_CI, Testing=$IS_TESTING, Docker=$IS_DOCKER"

    # Set database connection parameters based on environment
    if [[ "$IS_CI" == "true" ]]; then
        TEST_HOST="localhost"
        print_info "Using CI configuration: $TEST_HOST:$TEST_PORT"
    elif [[ "$IS_TESTING" == "true" ]]; then
        TEST_HOST=${POSTGRES_HOST:-postgres-mem0}
        print_info "Using testing configuration: $TEST_HOST:$TEST_PORT"
    fi

    # Set environment variables
    export DATABASE_URL="postgresql://$TEST_USER:$TEST_PASSWORD@$TEST_HOST:$TEST_PORT/$TEST_DB_NAME"
    export TESTING=true
    export PYTHONPATH="$PROJECT_ROOT:$SCRIPT_DIR"

    print_success "Environment detection completed"
}

# Function to setup test database
setup_test_database() {
    print_header "SETTING UP TEST DATABASE"

    # Run the database setup script
    if [[ "$CLEAN_DATABASE" == "true" ]]; then
        print_info "Setting up test database with clean option..."
        python3 setup_test_database.py --clean
    else
        print_info "Setting up test database..."
        python3 setup_test_database.py
    fi

    if [[ $? -eq 0 ]]; then
        print_success "Test database setup completed"
    else
        print_error "Test database setup failed"
        exit 1
    fi
}

# Function to run migration tests
run_migration_tests() {
    print_header "RUNNING MIGRATION TESTS"

    local pytest_args=()
    pytest_args+=("tests/test_migration_integrity.py")
    pytest_args+=("-v")

    if [[ "$VERBOSE" == "true" ]]; then
        pytest_args+=("-s")
    fi

    if [[ "$COVERAGE" == "true" ]]; then
        pytest_args+=("--cov=app.database")
        pytest_args+=("--cov=app.models")
        pytest_args+=("--cov-report=term-missing")
        pytest_args+=("--cov-report=html:htmlcov-migration")
    fi

    print_info "Running migration integrity tests..."
    pytest "${pytest_args[@]}"

    if [[ $? -eq 0 ]]; then
        print_success "Migration tests completed successfully"
    else
        print_error "Migration tests failed"
        return 1
    fi
}

# Function to run transaction tests
run_transaction_tests() {
    print_header "RUNNING TRANSACTION TESTS"

    local pytest_args=()
    pytest_args+=("tests/test_database_framework.py")
    pytest_args+=("-v")
    pytest_args+=("-k" "transaction")

    if [[ "$VERBOSE" == "true" ]]; then
        pytest_args+=("-s")
    fi

    if [[ "$COVERAGE" == "true" ]]; then
        pytest_args+=("--cov=app.database")
        pytest_args+=("--cov-report=term-missing")
        pytest_args+=("--cov-report=html:htmlcov-transaction")
    fi

    print_info "Running transaction rollback tests..."
    pytest "${pytest_args[@]}"

    if [[ $? -eq 0 ]]; then
        print_success "Transaction tests completed successfully"
    else
        print_error "Transaction tests failed"
        return 1
    fi
}

# Function to run performance tests
run_performance_tests() {
    print_header "RUNNING PERFORMANCE TESTS"

    local pytest_args=()
    pytest_args+=("tests/test_database_framework.py")
    pytest_args+=("-v")
    pytest_args+=("-k" "performance")
    pytest_args+=("--benchmark-only")

    if [[ "$VERBOSE" == "true" ]]; then
        pytest_args+=("-s")
    fi

    print_info "Running database performance tests..."
    pytest "${pytest_args[@]}"

    if [[ $? -eq 0 ]]; then
        print_success "Performance tests completed successfully"
    else
        print_error "Performance tests failed"
        return 1
    fi
}

# Function to generate test report
generate_test_report() {
    print_header "GENERATING TEST REPORT"

    local report_file="database-test-report.html"

    cat > "$report_file" << EOF
<!DOCTYPE html>
<html>
<head>
    <title>Database Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background-color: #f0f0f0; padding: 10px; }
        .success { color: green; }
        .error { color: red; }
        .warning { color: orange; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Database Test Report</h1>
        <p>Generated: $(date)</p>
        <p>Environment: CI=$IS_CI, Testing=$IS_TESTING, Docker=$IS_DOCKER</p>
    </div>

    <h2>Test Summary</h2>
    <ul>
        <li>Migration Tests: $(if [[ "$RUN_MIGRATION_TESTS" == "true" ]]; then echo "✅ Run"; else echo "⏭️ Skipped"; fi)</li>
        <li>Transaction Tests: $(if [[ "$RUN_TRANSACTION_TESTS" == "true" ]]; then echo "✅ Run"; else echo "⏭️ Skipped"; fi)</li>
        <li>Performance Tests: $(if [[ "$RUN_PERFORMANCE_TESTS" == "true" ]]; then echo "✅ Run"; else echo "⏭️ Skipped"; fi)</li>
    </ul>

    <h2>Coverage Reports</h2>
    <p>Coverage reports are available in the htmlcov-* directories.</p>

    <h2>Database Configuration</h2>
    <ul>
        <li>Host: $TEST_HOST</li>
        <li>Port: $TEST_PORT</li>
        <li>Database: $TEST_DB_NAME</li>
        <li>User: $TEST_USER</li>
    </ul>
</body>
</html>
EOF

    print_success "Test report generated: $report_file"
}

# Main execution
main() {
    print_header "DATABASE TEST RUNNER"

    # Check prerequisites
    check_prerequisites

    # Detect environment
    detect_environment

    # Setup test database
    setup_test_database

    # Run selected tests
    local test_failures=0

    if [[ "$RUN_MIGRATION_TESTS" == "true" ]]; then
        if ! run_migration_tests; then
            ((test_failures++))
        fi
    fi

    if [[ "$RUN_TRANSACTION_TESTS" == "true" ]]; then
        if ! run_transaction_tests; then
            ((test_failures++))
        fi
    fi

    if [[ "$RUN_PERFORMANCE_TESTS" == "true" ]]; then
        if ! run_performance_tests; then
            ((test_failures++))
        fi
    fi

    # Generate test report
    generate_test_report

    # Final summary
    print_header "TEST SUMMARY"

    if [[ $test_failures -eq 0 ]]; then
        print_success "All database tests completed successfully! 🎉"
        exit 0
    else
        print_error "$test_failures test suite(s) failed"
        exit 1
    fi
}

# Execute main function
main "$@"
