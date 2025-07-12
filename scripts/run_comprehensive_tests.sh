#!/bin/bash

# Comprehensive Test Execution Script for mem0-stack
# Enhanced pytest infrastructure with coverage, reporting, and quality gates

set -euo pipefail

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly PURPLE='\033[0;35m'
readonly CYAN='\033[0;36m'
readonly NC='\033[0m' # No Color

# Configuration
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
readonly COVERAGE_THRESHOLD=80
readonly MAX_DURATION=300
readonly TEST_RESULTS_DIR="${PROJECT_ROOT}/test-results"
readonly REPORTS_DIR="${PROJECT_ROOT}/test-reports"

# Default values
TEST_SUITE="all"
COVERAGE_REPORT="html"
PARALLEL_JOBS=4
VERBOSE=false
BENCHMARK=false
PROFILE=false
FAILFAST=false
RERUN_FAILED=false
CLEAN_CACHE=false
GENERATE_REPORT=true

# Function to print colored output
print_colored() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to print header
print_header() {
    echo ""
    print_colored "${CYAN}" "=========================================="
    print_colored "${CYAN}" "$1"
    print_colored "${CYAN}" "=========================================="
    echo ""
}

# Function to print usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS] [TEST_SUITE]

Comprehensive test execution script for mem0-stack pytest infrastructure.

TEST_SUITE:
    all          Run all tests (default)
    unit         Run only unit tests
    integration  Run only integration tests
    performance  Run only performance tests
    api          Run only API tests
    ui           Run only UI tests
    smoke        Run only smoke tests
    regression   Run only regression tests
    security     Run only security tests
    slow         Run only slow tests
    e2e          Run only end-to-end tests

OPTIONS:
    -h, --help              Show this help message
    -v, --verbose           Verbose output
    -j, --jobs N            Number of parallel jobs (default: 4)
    -c, --coverage FORMAT   Coverage report format: html,xml,json,term (default: html)
    -f, --failfast          Stop on first failure
    -r, --rerun-failed      Rerun only failed tests from last run
    -b, --benchmark         Run with benchmarking
    -p, --profile           Run with profiling
    --clean-cache           Clean pytest cache before running
    --no-report             Skip generating test report
    --threshold N           Coverage threshold (default: 80)
    --max-duration N        Maximum test duration in seconds (default: 300)

Examples:
    $0                      # Run all tests
    $0 unit                 # Run unit tests only
    $0 -v -j 8 integration  # Run integration tests with 8 parallel jobs
    $0 -f -c xml unit       # Run unit tests with failfast and XML coverage
    $0 --benchmark performance  # Run performance tests with benchmarking
    $0 --profile --verbose slow # Run slow tests with profiling

Environment Variables:
    TESTING=true            # Set automatically
    COVERAGE_THRESHOLD      # Override coverage threshold
    MAX_TEST_DURATION       # Override max duration
    PYTEST_ARGS            # Additional pytest arguments

EOF
}

# Function to check dependencies
check_dependencies() {
    print_header "🔍 Checking Dependencies"

    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_colored "${RED}" "❌ Python 3 not found"
        exit 1
    fi

    # Check pip
    if ! command -v pip &> /dev/null; then
        print_colored "${RED}" "❌ pip not found"
        exit 1
    fi

    # Check if we're in a virtual environment
    if [[ -z "${VIRTUAL_ENV:-}" ]]; then
        print_colored "${YELLOW}" "⚠️  Not in a virtual environment"
        print_colored "${YELLOW}" "   Consider activating a virtual environment first"
    else
        print_colored "${GREEN}" "✅ Virtual environment: ${VIRTUAL_ENV}"
    fi

    # Check if required packages are installed
    local missing_packages=()

    if ! python3 -c "import pytest" 2>/dev/null; then
        missing_packages+=("pytest")
    fi

    if ! python3 -c "import pytest_cov" 2>/dev/null; then
        missing_packages+=("pytest-cov")
    fi

    if [[ ${#missing_packages[@]} -gt 0 ]]; then
        print_colored "${YELLOW}" "⚠️  Missing packages: ${missing_packages[*]}"
        print_colored "${YELLOW}" "   Installing test dependencies..."
        pip install -r "${PROJECT_ROOT}/requirements-test.txt"
    fi

    print_colored "${GREEN}" "✅ Dependencies check complete"
}

# Function to setup test environment
setup_test_environment() {
    print_header "🔧 Setting up Test Environment"

    # Create directories
    mkdir -p "${TEST_RESULTS_DIR}" "${REPORTS_DIR}"

    # Set environment variables
    export TESTING=true
    export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH:-}"
    export COVERAGE_THRESHOLD="${COVERAGE_THRESHOLD}"
    export MAX_TEST_DURATION="${MAX_DURATION}"

    # Clean cache if requested
    if [[ "${CLEAN_CACHE}" == "true" ]]; then
        print_colored "${YELLOW}" "🧹 Cleaning pytest cache..."
        find "${PROJECT_ROOT}" -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null || true
        find "${PROJECT_ROOT}" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    fi

    # Check if services are running (for integration tests)
    if [[ "${TEST_SUITE}" == "integration" || "${TEST_SUITE}" == "all" ]]; then
        check_services
    fi

    print_colored "${GREEN}" "✅ Test environment setup complete"
}

# Function to check if required services are running
check_services() {
    print_colored "${BLUE}" "🔍 Checking required services..."

    # Check PostgreSQL
    if ! nc -z localhost 5432 2>/dev/null; then
        print_colored "${YELLOW}" "⚠️  PostgreSQL not running on localhost:5432"
        print_colored "${YELLOW}" "   Integration tests may fail"
    else
        print_colored "${GREEN}" "✅ PostgreSQL running"
    fi

    # Check Neo4j
    if ! nc -z localhost 7687 2>/dev/null; then
        print_colored "${YELLOW}" "⚠️  Neo4j not running on localhost:7687"
        print_colored "${YELLOW}" "   Integration tests may fail"
    else
        print_colored "${GREEN}" "✅ Neo4j running"
    fi

    # Check mem0 API
    if ! nc -z localhost 8000 2>/dev/null; then
        print_colored "${YELLOW}" "⚠️  mem0 API not running on localhost:8000"
        print_colored "${YELLOW}" "   Some integration tests may fail"
    else
        print_colored "${GREEN}" "✅ mem0 API running"
    fi
}

# Function to build pytest command
build_pytest_command() {
    local cmd="python3 -m pytest"

    # Add test paths based on suite
    case "${TEST_SUITE}" in
        "unit")
            cmd+=" -m 'unit or (not integration and not performance and not slow and not e2e)'"
            ;;
        "integration")
            cmd+=" -m 'integration'"
            ;;
        "performance")
            cmd+=" -m 'performance'"
            ;;
        "api")
            cmd+=" -m 'api'"
            ;;
        "ui")
            cmd+=" -m 'ui'"
            ;;
        "smoke")
            cmd+=" -m 'smoke'"
            ;;
        "regression")
            cmd+=" -m 'regression'"
            ;;
        "security")
            cmd+=" -m 'security'"
            ;;
        "slow")
            cmd+=" -m 'slow'"
            ;;
        "e2e")
            cmd+=" -m 'e2e'"
            ;;
        "all")
            # Use default testpaths from pytest.ini
            ;;
        *)
            print_colored "${RED}" "❌ Unknown test suite: ${TEST_SUITE}"
            exit 1
            ;;
    esac

    # Add parallel execution
    if [[ "${PARALLEL_JOBS}" -gt 1 ]]; then
        cmd+=" -n ${PARALLEL_JOBS}"
    fi

    # Add coverage options
    cmd+=" --cov-report=${COVERAGE_REPORT}"
    cmd+=" --cov-fail-under=${COVERAGE_THRESHOLD}"

    # Add verbosity
    if [[ "${VERBOSE}" == "true" ]]; then
        cmd+=" -vv"
    fi

    # Add failfast
    if [[ "${FAILFAST}" == "true" ]]; then
        cmd+=" -x"
    fi

    # Add rerun failed
    if [[ "${RERUN_FAILED}" == "true" ]]; then
        cmd+=" --lf"
    fi

    # Add benchmarking
    if [[ "${BENCHMARK}" == "true" ]]; then
        cmd+=" --benchmark-only"
        cmd+=" --benchmark-json=${REPORTS_DIR}/benchmark-results.json"
    fi

    # Add profiling
    if [[ "${PROFILE}" == "true" ]]; then
        cmd+=" --profile"
        cmd+=" --profile-svg"
    fi

    # Add custom pytest args
    if [[ -n "${PYTEST_ARGS:-}" ]]; then
        cmd+=" ${PYTEST_ARGS}"
    fi

    echo "${cmd}"
}

# Function to run tests
run_tests() {
    print_header "🧪 Running Tests: ${TEST_SUITE}"

    local start_time=$(date +%s)
    local cmd=$(build_pytest_command)

    print_colored "${BLUE}" "Command: ${cmd}"
    print_colored "${BLUE}" "Working directory: ${PROJECT_ROOT}"
    print_colored "${BLUE}" "Test suite: ${TEST_SUITE}"
    print_colored "${BLUE}" "Parallel jobs: ${PARALLEL_JOBS}"
    print_colored "${BLUE}" "Coverage threshold: ${COVERAGE_THRESHOLD}%"
    echo ""

    # Change to project root
    cd "${PROJECT_ROOT}"

    # Run the tests
    local exit_code=0
    eval "${cmd}" || exit_code=$?

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    # Print results
    echo ""
    print_colored "${BLUE}" "Test execution completed in ${duration} seconds"

    if [[ ${exit_code} -eq 0 ]]; then
        print_colored "${GREEN}" "✅ All tests passed!"
    else
        print_colored "${RED}" "❌ Some tests failed (exit code: ${exit_code})"
    fi

    return ${exit_code}
}

# Function to generate comprehensive report
generate_report() {
    if [[ "${GENERATE_REPORT}" != "true" ]]; then
        return 0
    fi

    print_header "📊 Generating Test Report"

    local report_file="${REPORTS_DIR}/test-summary-$(date +%Y%m%d_%H%M%S).md"

    cat > "${report_file}" << EOF
# Test Execution Report

**Generated:** $(date)
**Test Suite:** ${TEST_SUITE}
**Coverage Threshold:** ${COVERAGE_THRESHOLD}%
**Parallel Jobs:** ${PARALLEL_JOBS}

## Configuration

- **Project Root:** ${PROJECT_ROOT}
- **Python:** $(python3 --version)
- **pytest:** $(python3 -m pytest --version)
- **Coverage:** ${COVERAGE_REPORT}
- **Benchmarking:** ${BENCHMARK}
- **Profiling:** ${PROFILE}

## Test Results

EOF

    # Add coverage information if available
    if [[ -f "${PROJECT_ROOT}/coverage.xml" ]]; then
        echo "## Coverage Report" >> "${report_file}"
        echo "" >> "${report_file}"
        echo "Coverage report generated: coverage.xml" >> "${report_file}"
        echo "" >> "${report_file}"
    fi

    # Add HTML report link if available
    if [[ -d "${PROJECT_ROOT}/htmlcov" ]]; then
        echo "## HTML Coverage Report" >> "${report_file}"
        echo "" >> "${report_file}"
        echo "Open: htmlcov/index.html" >> "${report_file}"
        echo "" >> "${report_file}"
    fi

    # Add benchmark results if available
    if [[ -f "${REPORTS_DIR}/benchmark-results.json" ]]; then
        echo "## Benchmark Results" >> "${report_file}"
        echo "" >> "${report_file}"
        echo "Benchmark results: test-reports/benchmark-results.json" >> "${report_file}"
        echo "" >> "${report_file}"
    fi

    print_colored "${GREEN}" "✅ Test report generated: ${report_file}"
}

# Function to cleanup
cleanup() {
    print_header "🧹 Cleanup"

    # Move reports to timestamped directory
    if [[ -d "${REPORTS_DIR}" ]]; then
        local timestamp=$(date +%Y%m%d_%H%M%S)
        local archived_dir="${REPORTS_DIR}/archived/${timestamp}"
        mkdir -p "${archived_dir}"

        # Move generated files
        [[ -f "${PROJECT_ROOT}/coverage.xml" ]] && mv "${PROJECT_ROOT}/coverage.xml" "${archived_dir}/"
        [[ -f "${PROJECT_ROOT}/test-results.xml" ]] && mv "${PROJECT_ROOT}/test-results.xml" "${archived_dir}/"
        [[ -f "${PROJECT_ROOT}/test-report.html" ]] && mv "${PROJECT_ROOT}/test-report.html" "${archived_dir}/"
        [[ -f "${PROJECT_ROOT}/tests.log" ]] && mv "${PROJECT_ROOT}/tests.log" "${archived_dir}/"

        # Create symlink to latest
        rm -f "${REPORTS_DIR}/latest"
        ln -sf "archived/${timestamp}" "${REPORTS_DIR}/latest"

        print_colored "${GREEN}" "✅ Reports archived to: ${archived_dir}"
        print_colored "${GREEN}" "✅ Latest symlink: ${REPORTS_DIR}/latest"
    fi
}

# Main function
main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                usage
                exit 0
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -j|--jobs)
                PARALLEL_JOBS="$2"
                shift 2
                ;;
            -c|--coverage)
                COVERAGE_REPORT="$2"
                shift 2
                ;;
            -f|--failfast)
                FAILFAST=true
                shift
                ;;
            -r|--rerun-failed)
                RERUN_FAILED=true
                shift
                ;;
            -b|--benchmark)
                BENCHMARK=true
                shift
                ;;
            -p|--profile)
                PROFILE=true
                shift
                ;;
            --clean-cache)
                CLEAN_CACHE=true
                shift
                ;;
            --no-report)
                GENERATE_REPORT=false
                shift
                ;;
            --threshold)
                COVERAGE_THRESHOLD="$2"
                shift 2
                ;;
            --max-duration)
                MAX_DURATION="$2"
                shift 2
                ;;
            -*)
                print_colored "${RED}" "Unknown option: $1"
                usage
                exit 1
                ;;
            *)
                TEST_SUITE="$1"
                shift
                ;;
        esac
    done

    # Validate coverage format
    case "${COVERAGE_REPORT}" in
        html|xml|json|term)
            ;;
        *)
            print_colored "${RED}" "Invalid coverage format: ${COVERAGE_REPORT}"
            exit 1
            ;;
    esac

    # Print startup banner
    print_header "🚀 mem0-stack Comprehensive Test Suite"
    print_colored "${BLUE}" "Test Suite: ${TEST_SUITE}"
    print_colored "${BLUE}" "Coverage: ${COVERAGE_REPORT}"
    print_colored "${BLUE}" "Parallel Jobs: ${PARALLEL_JOBS}"
    print_colored "${BLUE}" "Threshold: ${COVERAGE_THRESHOLD}%"

    # Execute test pipeline
    local exit_code=0

    check_dependencies
    setup_test_environment
    run_tests || exit_code=$?
    generate_report
    cleanup

    # Final status
    echo ""
    if [[ ${exit_code} -eq 0 ]]; then
        print_header "🎉 Test Suite Completed Successfully"
        print_colored "${GREEN}" "✅ All tests passed!"
        print_colored "${GREEN}" "✅ Coverage threshold met!"
        print_colored "${GREEN}" "✅ Reports generated!"
    else
        print_header "❌ Test Suite Failed"
        print_colored "${RED}" "❌ Some tests failed"
        print_colored "${RED}" "❌ Check the reports for details"
    fi

    exit ${exit_code}
}

# Run main function
main "$@"