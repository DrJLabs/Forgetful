#!/bin/bash

# API Contract Test Runner - Step 2.1 Implementation
# ================================================
# 
# This script runs comprehensive API contract tests to ensure:
# - OpenAPI schema compliance
# - Request/response contract validation
# - Error consistency across endpoints
# - Input validation testing
# - API contract stability

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TEST_DIR="$SCRIPT_DIR/tests"
REPORTS_DIR="$PROJECT_ROOT/test-reports"
COVERAGE_DIR="$REPORTS_DIR/coverage"

# Test configuration
export TESTING="true"
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}"
}

print_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] ✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] ⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ✗ $1${NC}"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to ensure directory exists
ensure_directory() {
    if [ ! -d "$1" ]; then
        mkdir -p "$1"
        print_status "Created directory: $1"
    fi
}

# Function to run tests with specific markers
run_test_suite() {
    local test_name="$1"
    local test_markers="$2"
    local test_files="$3"
    local output_suffix="$4"
    
    print_status "Running $test_name..."
    
    local pytest_args=(
        "$test_files"
        "-v"
        "--tb=short"
        "--strict-markers"
        "--disable-warnings"
        "--maxfail=5"
        "--cov=app"
        "--cov-branch"
        "--cov-report=html:$COVERAGE_DIR/contract_tests_$output_suffix"
        "--cov-report=xml:$REPORTS_DIR/coverage_contract_$output_suffix.xml"
        "--cov-report=term-missing"
        "--junit-xml=$REPORTS_DIR/contract_tests_$output_suffix.xml"
        "--html=$REPORTS_DIR/contract_tests_$output_suffix.html"
        "--self-contained-html"
    )
    
    if [ -n "$test_markers" ]; then
        pytest_args+=("-m" "$test_markers")
    fi
    
    if pytest "${pytest_args[@]}"; then
        print_success "$test_name completed successfully"
        return 0
    else
        print_error "$test_name failed"
        return 1
    fi
}

# Function to generate test summary
generate_summary() {
    local total_tests=0
    local passed_tests=0
    local failed_tests=0
    
    print_status "Generating test summary..."
    
    # Count test results from XML reports
    if command_exists xmllint; then
        for xml_file in "$REPORTS_DIR"/contract_tests_*.xml; do
            if [ -f "$xml_file" ]; then
                local tests=$(xmllint --xpath "//testsuite/@tests" "$xml_file" 2>/dev/null | grep -o '[0-9]*' || echo "0")
                local failures=$(xmllint --xpath "//testsuite/@failures" "$xml_file" 2>/dev/null | grep -o '[0-9]*' || echo "0")
                local errors=$(xmllint --xpath "//testsuite/@errors" "$xml_file" 2>/dev/null | grep -o '[0-9]*' || echo "0")
                
                total_tests=$((total_tests + tests))
                failed_tests=$((failed_tests + failures + errors))
                passed_tests=$((passed_tests + tests - failures - errors))
            fi
        done
    fi
    
    echo
    echo "======================================"
    echo "API Contract Test Summary"
    echo "======================================"
    echo "Total Tests: $total_tests"
    echo "Passed: $passed_tests"
    echo "Failed: $failed_tests"
    echo "Reports Directory: $REPORTS_DIR"
    echo "======================================"
    echo
}

# Function to display help
show_help() {
    cat << EOF
API Contract Test Runner

Usage: $0 [OPTIONS] [TEST_CATEGORY]

Test Categories:
  all                 Run all contract tests (default)
  openapi            Run OpenAPI schema validation tests
  contract           Run API contract tests
  validation         Run input validation tests
  endpoints          Run endpoint-specific tests
  consistency        Run error consistency tests

Options:
  -h, --help         Show this help message
  -q, --quiet        Suppress verbose output
  -f, --fast         Skip slow tests
  -c, --coverage     Generate coverage report only
  -r, --report-only  Generate reports without running tests
  --clean            Clean test reports before running

Examples:
  $0                 # Run all contract tests
  $0 openapi         # Run only OpenAPI schema tests
  $0 contract        # Run only API contract tests
  $0 --fast          # Run tests quickly (skip slow ones)
  $0 --clean all     # Clean reports and run all tests

EOF
}

# Parse command line arguments
QUIET=false
FAST=false
COVERAGE_ONLY=false
REPORT_ONLY=false
CLEAN=false
TEST_CATEGORY="all"

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -q|--quiet)
            QUIET=true
            shift
            ;;
        -f|--fast)
            FAST=true
            shift
            ;;
        -c|--coverage)
            COVERAGE_ONLY=true
            shift
            ;;
        -r|--report-only)
            REPORT_ONLY=true
            shift
            ;;
        --clean)
            CLEAN=true
            shift
            ;;
        openapi|contract|validation|endpoints|consistency|all)
            TEST_CATEGORY="$1"
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Main execution
main() {
    print_status "Starting API Contract Test Runner"
    print_status "Test Category: $TEST_CATEGORY"
    print_status "Project Root: $PROJECT_ROOT"
    print_status "Test Directory: $TEST_DIR"
    
    # Ensure directories exist
    ensure_directory "$REPORTS_DIR"
    ensure_directory "$COVERAGE_DIR"
    
    # Clean reports if requested
    if [ "$CLEAN" = true ]; then
        print_status "Cleaning test reports..."
        rm -rf "$REPORTS_DIR"/*
        ensure_directory "$REPORTS_DIR"
        ensure_directory "$COVERAGE_DIR"
    fi
    
    # Check if pytest is available
    if ! command_exists pytest; then
        print_error "pytest is not installed. Please install test dependencies:"
        print_error "pip install -r requirements-test.txt"
        exit 1
    fi
    
    # Change to script directory
    cd "$SCRIPT_DIR"
    
    # Skip tests if report-only mode
    if [ "$REPORT_ONLY" = true ]; then
        print_status "Report-only mode - skipping test execution"
        generate_summary
        exit 0
    fi
    
    # Coverage-only mode
    if [ "$COVERAGE_ONLY" = true ]; then
        print_status "Generating coverage report..."
        pytest --cov=app --cov-report=html:"$COVERAGE_DIR"/contract_tests_coverage tests/
        print_success "Coverage report generated: $COVERAGE_DIR/contract_tests_coverage/index.html"
        exit 0
    fi
    
    # Test execution
    local exit_code=0
    local fast_markers=""
    
    if [ "$FAST" = true ]; then
        fast_markers="not slow"
    fi
    
    case "$TEST_CATEGORY" in
        "openapi")
            run_test_suite "OpenAPI Schema Validation Tests" "$fast_markers and openapi" "tests/test_openapi_schema_validation.py" "openapi" || exit_code=$?
            ;;
        "contract")
            run_test_suite "API Contract Tests" "$fast_markers and contract" "tests/test_api_contract_validation.py" "contract" || exit_code=$?
            ;;
        "validation")
            run_test_suite "Input Validation Tests" "$fast_markers and validation" "tests/test_api_contract_validation.py::TestInputValidationComprehensive" "validation" || exit_code=$?
            ;;
        "endpoints")
            run_test_suite "Endpoint Contract Tests" "$fast_markers" "tests/test_api_contract_validation.py::TestMemoryEndpointContracts tests/test_api_contract_validation.py::TestAppsEndpointContracts tests/test_api_contract_validation.py::TestStatsEndpointContracts tests/test_api_contract_validation.py::TestConfigEndpointContracts" "endpoints" || exit_code=$?
            ;;
        "consistency")
            run_test_suite "Error Consistency Tests" "$fast_markers" "tests/test_api_contract_validation.py::TestErrorConsistencyValidation" "consistency" || exit_code=$?
            ;;
        "all")
            print_status "Running comprehensive API contract test suite..."
            
            # Run OpenAPI schema validation tests
            run_test_suite "OpenAPI Schema Validation" "$fast_markers and openapi" "tests/test_openapi_schema_validation.py" "openapi" || exit_code=$?
            
            # Run API contract tests
            run_test_suite "API Contract Validation" "$fast_markers and contract" "tests/test_api_contract_validation.py" "contract" || exit_code=$?
            
            # Run all contract tests together for comprehensive coverage
            run_test_suite "Complete Contract Test Suite" "$fast_markers" "tests/test_api_contract_validation.py tests/test_openapi_schema_validation.py" "complete" || exit_code=$?
            ;;
        *)
            print_error "Invalid test category: $TEST_CATEGORY"
            show_help
            exit 1
            ;;
    esac
    
    # Generate summary
    generate_summary
    
    # Final status
    if [ $exit_code -eq 0 ]; then
        print_success "All API contract tests completed successfully!"
        print_status "View detailed reports in: $REPORTS_DIR"
        print_status "View coverage reports in: $COVERAGE_DIR"
    else
        print_error "Some API contract tests failed (exit code: $exit_code)"
        print_status "Check reports in: $REPORTS_DIR for details"
    fi
    
    exit $exit_code
}

# Run main function
main "$@" 