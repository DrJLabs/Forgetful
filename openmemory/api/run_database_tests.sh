#!/bin/bash

# Database Testing Framework Runner - Step 1.2
# Comprehensive test runner for database testing framework

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Default values
ENVIRONMENT="test"
VERBOSE=false
PARALLEL=false
COVERAGE=true
MARKERS=""
PATTERN=""
TIMEOUT=300
DOCKER_CLEANUP=true
REPORT_DIR="test-reports"

# Function to display usage
usage() {
    echo "Database Testing Framework Runner"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "OPTIONS:"
    echo "  -h, --help                Show this help message"
    echo "  -e, --environment ENV     Test environment (test, docker, ci) [default: test]"
    echo "  -v, --verbose             Verbose output"
    echo "  -p, --parallel            Run tests in parallel"
    echo "  -c, --no-coverage         Skip coverage reporting"
    echo "  -m, --markers MARKERS     Run tests with specific markers"
    echo "  -k, --pattern PATTERN     Run tests matching pattern"
    echo "  -t, --timeout TIMEOUT     Test timeout in seconds [default: 300]"
    echo "  --no-cleanup              Don't cleanup Docker containers"
    echo "  --report-dir DIR          Report directory [default: test-reports]"
    echo ""
    echo "EXAMPLES:"
    echo "  $0                        Run all tests"
    echo "  $0 -m unit                Run only unit tests"
    echo "  $0 -m \"database and postgres\" Run PostgreSQL database tests"
    echo "  $0 -k transaction         Run transaction tests"
    echo "  $0 -e docker -p           Run tests with Docker in parallel"
    echo "  $0 -m migration           Run migration tests"
    echo ""
    echo "AVAILABLE MARKERS:"
    echo "  unit                      Fast, isolated unit tests"
    echo "  integration               Integration tests with dependencies"
    echo "  database                  Database tests with containers"
    echo "  migration                 Database migration tests"
    echo "  performance               Performance and benchmark tests"
    echo "  transaction               Transaction rollback tests"
    echo "  concurrent                Concurrent access tests"
    echo "  postgres                  PostgreSQL specific tests"
    echo "  sqlite                    SQLite specific tests"
    echo "  slow                      Slow running tests"
    echo ""
}

# Function to log messages
log() {
    local level=$1
    shift
    local message="$@"

    case $level in
        "INFO")
            echo -e "${GREEN}[INFO]${NC} $message"
            ;;
        "WARN")
            echo -e "${YELLOW}[WARN]${NC} $message"
            ;;
        "ERROR")
            echo -e "${RED}[ERROR]${NC} $message"
            ;;
        "DEBUG")
            if [ "$VERBOSE" = true ]; then
                echo -e "${BLUE}[DEBUG]${NC} $message"
            fi
            ;;
    esac
}

# Function to check prerequisites
check_prerequisites() {
    log "INFO" "Checking prerequisites..."

    # Check if we're in the correct directory
    if [ ! -f "pytest.ini" ]; then
        log "ERROR" "pytest.ini not found. Please run from the API directory."
        exit 1
    fi

    # Check if Python is available
    if ! command -v python3 &> /dev/null; then
        log "ERROR" "Python 3 is required but not found."
        exit 1
    fi

    # Check if pip is available
    if ! command -v pip &> /dev/null; then
        log "ERROR" "pip is required but not found."
        exit 1
    fi

    # Check if Docker is available for Docker tests
    if [ "$ENVIRONMENT" = "docker" ] && ! command -v docker &> /dev/null; then
        log "ERROR" "Docker is required for Docker environment tests."
        exit 1
    fi

    log "INFO" "Prerequisites check passed."
}

# Function to setup test environment
setup_environment() {
    log "INFO" "Setting up test environment..."

    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        log "INFO" "Creating virtual environment..."
        python3 -m venv venv
    fi

    # Activate virtual environment
    source venv/bin/activate

    # Install/upgrade pip
    pip install --upgrade pip

    # Install test dependencies
    log "INFO" "Installing test dependencies..."
    pip install -r requirements-test.txt

    # Install main dependencies
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
    fi

    # Create report directory
    mkdir -p "$REPORT_DIR"

    log "INFO" "Test environment setup completed."
}

# Function to cleanup Docker containers
cleanup_docker() {
    if [ "$DOCKER_CLEANUP" = true ]; then
        log "INFO" "Cleaning up Docker containers..."

        # Stop and remove test containers
        docker container prune -f --filter "label=testcontainer=true" 2>/dev/null || true

        # Remove test networks
        docker network prune -f 2>/dev/null || true

        # Remove test volumes
        docker volume prune -f 2>/dev/null || true

        log "INFO" "Docker cleanup completed."
    fi
}

# Function to run tests
run_tests() {
    log "INFO" "Running database tests..."

    # Build pytest command
    local pytest_cmd="python -m pytest"

    # Add verbosity
    if [ "$VERBOSE" = true ]; then
        pytest_cmd="$pytest_cmd -vv"
    fi

    # Add parallel execution
    if [ "$PARALLEL" = true ]; then
        pytest_cmd="$pytest_cmd -n auto"
    fi

    # Add coverage
    if [ "$COVERAGE" = true ]; then
        pytest_cmd="$pytest_cmd --cov=app --cov-report=html:$REPORT_DIR/htmlcov --cov-report=term-missing --cov-report=xml:$REPORT_DIR/coverage.xml"
    fi

    # Add markers
    if [ -n "$MARKERS" ]; then
        pytest_cmd="$pytest_cmd -m \"$MARKERS\""
    fi

    # Add pattern
    if [ -n "$PATTERN" ]; then
        pytest_cmd="$pytest_cmd -k \"$PATTERN\""
    fi

    # Add timeout
    pytest_cmd="$pytest_cmd --timeout=$TIMEOUT"

    # Add report outputs
    pytest_cmd="$pytest_cmd --junit-xml=$REPORT_DIR/test-results.xml --html=$REPORT_DIR/test-report.html --self-contained-html"

    # Set environment variables based on test environment
    case $ENVIRONMENT in
        "test")
            export TESTING=true
            export DATABASE_URL="sqlite:///:memory:"
            ;;
        "docker")
            export TESTING=true
            export USE_DOCKER_CONTAINERS=true
            ;;
        "ci")
            export TESTING=true
            export CI=true
            export DATABASE_URL="sqlite:///:memory:"
            ;;
    esac

    # Run the tests
    log "INFO" "Executing: $pytest_cmd"
    log "INFO" "Test environment: $ENVIRONMENT"
    log "INFO" "Timeout: ${TIMEOUT}s"

    if eval "$pytest_cmd"; then
        log "INFO" "Tests completed successfully!"

        # Display coverage summary if available
        if [ "$COVERAGE" = true ] && [ -f "$REPORT_DIR/coverage.xml" ]; then
            log "INFO" "Coverage report generated: $REPORT_DIR/htmlcov/index.html"
        fi

        # Display test report
        if [ -f "$REPORT_DIR/test-report.html" ]; then
            log "INFO" "Test report generated: $REPORT_DIR/test-report.html"
        fi

        return 0
    else
        log "ERROR" "Tests failed!"
        return 1
    fi
}

# Function to run specific test suites
run_test_suite() {
    local suite=$1

    case $suite in
        "unit")
            log "INFO" "Running unit tests..."
            MARKERS="unit"
            ;;
        "integration")
            log "INFO" "Running integration tests..."
            MARKERS="integration"
            ;;
        "database")
            log "INFO" "Running database tests..."
            MARKERS="database"
            ENVIRONMENT="docker"
            ;;
        "migration")
            log "INFO" "Running migration tests..."
            MARKERS="migration"
            ENVIRONMENT="docker"
            ;;
        "performance")
            log "INFO" "Running performance tests..."
            MARKERS="performance"
            TIMEOUT=600
            ;;
        "transaction")
            log "INFO" "Running transaction tests..."
            MARKERS="transaction"
            ENVIRONMENT="docker"
            ;;
        "all")
            log "INFO" "Running all tests..."
            MARKERS=""
            ENVIRONMENT="docker"
            ;;
    esac
}

# Function to display test results summary
display_summary() {
    log "INFO" "=== Test Results Summary ==="

    if [ -f "$REPORT_DIR/test-results.xml" ]; then
        # Parse JUnit XML for summary (simplified)
        if command -v xmllint &> /dev/null; then
            local tests=$(xmllint --xpath "string(//testsuite/@tests)" "$REPORT_DIR/test-results.xml" 2>/dev/null || echo "N/A")
            local failures=$(xmllint --xpath "string(//testsuite/@failures)" "$REPORT_DIR/test-results.xml" 2>/dev/null || echo "N/A")
            local errors=$(xmllint --xpath "string(//testsuite/@errors)" "$REPORT_DIR/test-results.xml" 2>/dev/null || echo "N/A")
            local time=$(xmllint --xpath "string(//testsuite/@time)" "$REPORT_DIR/test-results.xml" 2>/dev/null || echo "N/A")

            log "INFO" "Total Tests: $tests"
            log "INFO" "Failures: $failures"
            log "INFO" "Errors: $errors"
            log "INFO" "Execution Time: ${time}s"
        fi
    fi

    # Report locations
    log "INFO" "Reports generated in: $REPORT_DIR/"
    log "INFO" "- HTML Report: $REPORT_DIR/test-report.html"
    log "INFO" "- Coverage Report: $REPORT_DIR/htmlcov/index.html"
    log "INFO" "- JUnit XML: $REPORT_DIR/test-results.xml"
    log "INFO" "- Coverage XML: $REPORT_DIR/coverage.xml"
}

# Trap to cleanup on exit
cleanup() {
    log "INFO" "Performing cleanup..."
    cleanup_docker
}

trap cleanup EXIT

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            exit 0
            ;;
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -p|--parallel)
            PARALLEL=true
            shift
            ;;
        -c|--no-coverage)
            COVERAGE=false
            shift
            ;;
        -m|--markers)
            MARKERS="$2"
            shift 2
            ;;
        -k|--pattern)
            PATTERN="$2"
            shift 2
            ;;
        -t|--timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --no-cleanup)
            DOCKER_CLEANUP=false
            shift
            ;;
        --report-dir)
            REPORT_DIR="$2"
            shift 2
            ;;
        --suite)
            run_test_suite "$2"
            shift 2
            ;;
        *)
            log "ERROR" "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Main execution
main() {
    log "INFO" "Starting Database Testing Framework..."
    log "INFO" "Environment: $ENVIRONMENT"
    log "INFO" "Verbose: $VERBOSE"
    log "INFO" "Parallel: $PARALLEL"
    log "INFO" "Coverage: $COVERAGE"
    log "INFO" "Markers: ${MARKERS:-'all'}"
    log "INFO" "Pattern: ${PATTERN:-'all'}"
    log "INFO" "Timeout: ${TIMEOUT}s"
    log "INFO" "Report Directory: $REPORT_DIR"

    # Check prerequisites
    check_prerequisites

    # Setup environment
    setup_environment

    # Run tests
    if run_tests; then
        display_summary
        log "INFO" "Database testing completed successfully!"
        exit 0
    else
        log "ERROR" "Database testing failed!"
        exit 1
    fi
}

# Run main function
main "$@"