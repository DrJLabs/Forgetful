#!/bin/bash

# Security Test Runner for OpenMemory API
# Author: Quinn (QA Agent) - Step 2.2 Security Testing Suite
#
# This script runs comprehensive security tests covering:
# - Authentication security
# - Input validation security
# - Rate limiting security
# - Security headers
# - API security
# - Security integration tests

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test configuration
TEST_DIR="tests"
SECURITY_TESTS=(
    "test_security_authentication.py"
    "test_security_input_validation.py"
    "test_security_rate_limiting.py"
    "test_security_headers.py"
    "test_security_api.py"
    "test_security_integration.py"
)

# Output directories
REPORTS_DIR="security_test_reports"
COVERAGE_DIR="security_coverage"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Function to print colored output
print_status() {
    echo -e "${2}$1${NC}"
}

print_header() {
    echo -e "\n${BLUE}================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================================${NC}\n"
}

print_success() {
    print_status "$1" $GREEN
}

print_error() {
    print_status "$1" $RED
}

print_warning() {
    print_status "$1" $YELLOW
}

print_info() {
    print_status "$1" $BLUE
}

# Function to check prerequisites
check_prerequisites() {
    print_header "CHECKING PREREQUISITES"

    # Check if we're in the right directory
    if [ ! -f "main.py" ]; then
        print_error "Error: main.py not found. Please run from the OpenMemory API directory."
        exit 1
    fi

    # Check if pytest is installed
    if ! command -v pytest &> /dev/null; then
        print_error "Error: pytest not found. Please install pytest."
        exit 1
    fi

    # Check if test files exist
    missing_tests=()
    for test_file in "${SECURITY_TESTS[@]}"; do
        if [ ! -f "$TEST_DIR/$test_file" ]; then
            missing_tests+=("$test_file")
        fi
    done

    if [ ${#missing_tests[@]} -gt 0 ]; then
        print_error "Error: Missing test files:"
        for test in "${missing_tests[@]}"; do
            print_error "  - $test"
        done
        exit 1
    fi

    print_success "✓ All prerequisites met"
}

# Function to setup test environment
setup_environment() {
    print_header "SETTING UP TEST ENVIRONMENT"

    # Create reports directory
    mkdir -p "$REPORTS_DIR"
    mkdir -p "$COVERAGE_DIR"

    # Set test environment variables
    export TESTING=true
    export PYTHONPATH="${PYTHONPATH}:$(pwd)"

    # Create test database if needed
    if [ ! -f "test_openmemory.db" ]; then
        print_info "Creating test database..."
        python3 -c "
import os
os.environ['TESTING'] = 'true'
os.environ['DATABASE_URL'] = 'sqlite:///test_openmemory.db'
from app.database import engine, Base
Base.metadata.create_all(bind=engine)
print('Test database created')
"
    fi

    print_success "✓ Test environment ready"
}

# Function to run individual security test
run_security_test() {
    local test_file=$1
    local test_name=$(basename "$test_file" .py)

    print_info "Running $test_name..."

    # Run the test with detailed output
    if pytest "$TEST_DIR/$test_file" \
        -v \
        --tb=short \
        --markers security \
        --junit-xml="$REPORTS_DIR/${test_name}_${TIMESTAMP}.xml" \
        --html="$REPORTS_DIR/${test_name}_${TIMESTAMP}.html" \
        --self-contained-html \
        --cov=app \
        --cov-report=html:"$COVERAGE_DIR/${test_name}_${TIMESTAMP}" \
        --cov-report=term-missing \
        --disable-warnings \
        -x; then

        print_success "✓ $test_name PASSED"
        return 0
    else
        print_error "✗ $test_name FAILED"
        return 1
    fi
}

# Function to run all security tests
run_all_tests() {
    print_header "RUNNING SECURITY TESTS"

    local passed_tests=0
    local total_tests=${#SECURITY_TESTS[@]}
    local failed_tests=()

    for test_file in "${SECURITY_TESTS[@]}"; do
        if run_security_test "$test_file"; then
            ((passed_tests++))
        else
            failed_tests+=("$test_file")
        fi
        echo ""
    done

    # Summary
    print_header "SECURITY TEST SUMMARY"
    print_info "Total tests: $total_tests"
    print_success "Passed: $passed_tests"
    print_error "Failed: $((total_tests - passed_tests))"

    if [ ${#failed_tests[@]} -gt 0 ]; then
        print_error "Failed tests:"
        for test in "${failed_tests[@]}"; do
            print_error "  - $test"
        done
    fi

    # Calculate success rate
    local success_rate=$((passed_tests * 100 / total_tests))
    print_info "Success rate: $success_rate%"

    return $((total_tests - passed_tests))
}

# Function to run quick security check
run_quick_check() {
    print_header "QUICK SECURITY CHECK"

    # Run only critical security tests
    critical_tests=(
        "test_security_authentication.py::TestAuthenticationSecurity::test_unauthorized_memory_access_prevention"
        "test_security_input_validation.py::TestSQLInjectionPrevention::test_memory_list_sql_injection"
        "test_security_input_validation.py::TestXSSPrevention::test_memory_content_xss_prevention"
        "test_security_headers.py::TestCORSValidation::test_cors_credentials_handling"
        "test_security_api.py::TestEndpointAuthorization::test_cross_user_data_access_prevention"
    )

    local passed=0
    local total=${#critical_tests[@]}

    for test in "${critical_tests[@]}"; do
        print_info "Running critical test: $test"
        if pytest "$TEST_DIR/$test" -v --tb=short --disable-warnings; then
            print_success "✓ PASSED"
            ((passed++))
        else
            print_error "✗ FAILED"
        fi
    done

    print_info "Critical security tests: $passed/$total passed"
    return $((total - passed))
}

# Function to generate security report
generate_report() {
    print_header "GENERATING SECURITY REPORT"

    local report_file="$REPORTS_DIR/security_report_${TIMESTAMP}.md"

    cat > "$report_file" << EOF
# OpenMemory API Security Test Report

**Generated:** $(date)
**Test Suite:** Comprehensive Security Testing
**Author:** Quinn (QA Agent)

## Test Overview

This report covers comprehensive security testing across multiple layers:

### Test Categories

1. **Authentication Security** - User authentication and authorization
2. **Input Validation Security** - SQL injection, XSS, and input sanitization
3. **Rate Limiting Security** - API rate limiting and abuse protection
4. **Security Headers** - CORS, CSP, and HTTP security headers
5. **API Security** - Endpoint authorization and data protection
6. **Security Integration** - Multi-layer security validation

### Test Files Executed

EOF

    for test_file in "${SECURITY_TESTS[@]}"; do
        echo "- $test_file" >> "$report_file"
    done

    cat >> "$report_file" << EOF

## Test Results

### Summary
- **Total Test Files:** ${#SECURITY_TESTS[@]}
- **Execution Time:** $(date)
- **Environment:** Testing
- **Coverage Reports:** Available in $COVERAGE_DIR

### Detailed Results

Results are available in the following formats:
- **XML Reports:** $REPORTS_DIR/*_${TIMESTAMP}.xml
- **HTML Reports:** $REPORTS_DIR/*_${TIMESTAMP}.html
- **Coverage Reports:** $COVERAGE_DIR/

### Security Recommendations

1. **Authentication**: Ensure proper user authentication and authorization
2. **Input Validation**: Implement comprehensive input sanitization
3. **Rate Limiting**: Configure appropriate rate limits
4. **Security Headers**: Implement all recommended security headers
5. **API Security**: Enforce proper endpoint authorization
6. **Monitoring**: Implement security event monitoring

### Next Steps

1. Review failed tests and implement fixes
2. Add security tests to CI/CD pipeline
3. Regular security test execution
4. Security policy updates as needed

---
*This report was generated automatically by the OpenMemory Security Testing Suite*
EOF

    print_success "✓ Security report generated: $report_file"
}

# Function to cleanup test environment
cleanup() {
    print_header "CLEANING UP"

    # Remove test database
    if [ -f "test_openmemory.db" ]; then
        rm -f "test_openmemory.db"
        print_info "Test database removed"
    fi

    # Unset environment variables
    unset TESTING

    print_success "✓ Cleanup completed"
}

# Function to show help
show_help() {
    echo "OpenMemory API Security Test Runner"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help         Show this help message"
    echo "  -q, --quick        Run only critical security tests"
    echo "  -a, --all          Run all security tests (default)"
    echo "  -r, --report-only  Generate report only (no tests)"
    echo "  -c, --clean        Clean up test environment"
    echo "  -v, --verbose      Verbose output"
    echo ""
    echo "Examples:"
    echo "  $0                 # Run all security tests"
    echo "  $0 --quick         # Run critical tests only"
    echo "  $0 --clean         # Clean up test environment"
    echo ""
}

# Main execution
main() {
    local run_mode="all"
    local verbose=false

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -q|--quick)
                run_mode="quick"
                shift
                ;;
            -a|--all)
                run_mode="all"
                shift
                ;;
            -r|--report-only)
                run_mode="report"
                shift
                ;;
            -c|--clean)
                cleanup
                exit 0
                ;;
            -v|--verbose)
                verbose=true
                shift
                ;;
            *)
                print_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done

    # Set verbose mode
    if [ "$verbose" = true ]; then
        set -x
    fi

    # Print header
    print_header "OPENMEMORY API SECURITY TEST RUNNER"
    print_info "Mode: $run_mode"
    print_info "Timestamp: $TIMESTAMP"

    # Check prerequisites
    check_prerequisites

    # Setup environment
    setup_environment

    # Run tests based on mode
    local exit_code=0

    case $run_mode in
        "all")
            run_all_tests
            exit_code=$?
            ;;
        "quick")
            run_quick_check
            exit_code=$?
            ;;
        "report")
            print_info "Generating report only..."
            ;;
    esac

    # Generate report
    generate_report

    # Cleanup
    cleanup

    # Final status
    if [ $exit_code -eq 0 ]; then
        print_success "✓ All security tests completed successfully!"
    else
        print_error "✗ Some security tests failed. Please review the results."
    fi

    exit $exit_code
}

# Error handling
trap 'print_error "An error occurred. Cleaning up..."; cleanup; exit 1' ERR

# Run main function
main "$@"
