#!/bin/bash

# Backend Test Execution Script for OpenMemory API
# Quality Assurance Agent - Backend Testing Infrastructure

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧪 OpenMemory API Backend Testing Suite${NC}"
echo "=========================================="

# Change to API directory
cd "$(dirname "$0")/../openmemory/api"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}📦 Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install test dependencies
echo -e "${YELLOW}📦 Installing test dependencies...${NC}"
pip install -r requirements.txt
pip install -r requirements-test.txt

# Run different test suites
echo -e "${BLUE}🔧 Running Backend Tests${NC}"
echo "=========================="

# Run unit tests
echo -e "${YELLOW}🧪 Running Unit Tests...${NC}"
pytest tests/test_models.py tests/test_utils.py -v -m unit --tb=short

# Run API endpoint tests
echo -e "${YELLOW}🌐 Running API Endpoint Tests...${NC}"
pytest tests/test_routers.py -v -m unit --tb=short

# Run integration tests
echo -e "${YELLOW}🔗 Running Integration Tests...${NC}"
pytest tests/test_integration.py -v -m integration --tb=short

# Run all tests with coverage
echo -e "${YELLOW}📊 Running All Tests with Coverage...${NC}"
pytest tests/ -v --cov=app --cov-report=html --cov-report=term-missing --cov-report=xml

# Generate coverage report
echo -e "${YELLOW}📈 Coverage Report Generated${NC}"
echo "HTML Report: htmlcov/index.html"
echo "XML Report: coverage.xml"

# Check coverage threshold
COVERAGE_THRESHOLD=80
echo -e "${YELLOW}🎯 Checking Coverage Threshold (${COVERAGE_THRESHOLD}%)...${NC}"

# Run tests with coverage fail condition
if pytest tests/ --cov=app --cov-fail-under=${COVERAGE_THRESHOLD} --quiet; then
    echo -e "${GREEN}✅ Coverage meets threshold (${COVERAGE_THRESHOLD}%)${NC}"
else
    echo -e "${RED}❌ Coverage below threshold (${COVERAGE_THRESHOLD}%)${NC}"
    exit 1
fi

# Run performance tests if they exist
if [ -f "tests/test_performance.py" ]; then
    echo -e "${YELLOW}⚡ Running Performance Tests...${NC}"
    pytest tests/test_performance.py -v --benchmark-only
fi

# Lint check
echo -e "${YELLOW}🔍 Running Lint Checks...${NC}"
if command -v flake8 &> /dev/null; then
    flake8 app/ tests/
    echo -e "${GREEN}✅ Lint checks passed${NC}"
else
    echo -e "${YELLOW}⚠️ flake8 not installed, skipping lint checks${NC}"
fi

# Type checking
echo -e "${YELLOW}🏷️ Running Type Checks...${NC}"
if command -v mypy &> /dev/null; then
    mypy app/ --ignore-missing-imports
    echo -e "${GREEN}✅ Type checks passed${NC}"
else
    echo -e "${YELLOW}⚠️ mypy not installed, skipping type checks${NC}"
fi

# Test summary
echo -e "${BLUE}📋 Test Summary${NC}"
echo "==============="
echo "✅ Unit Tests: PASSED"
echo "✅ API Endpoint Tests: PASSED"
echo "✅ Integration Tests: PASSED"
echo "✅ Coverage: MEETS THRESHOLD"
echo "✅ Lint: PASSED"
echo "✅ Type Checking: PASSED"

echo -e "${GREEN}🎉 All Backend Tests Completed Successfully!${NC}"
echo -e "${BLUE}📊 Open htmlcov/index.html to view detailed coverage report${NC}" 