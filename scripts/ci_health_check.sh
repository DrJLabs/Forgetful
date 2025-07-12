#!/bin/bash
# CI/CD Pipeline Health Check Script
# Automatically detects and reports issues with the testing pipeline

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
HEALTH_REPORT="$PROJECT_ROOT/pipeline_health_report.md"

echo -e "${BLUE}🔍 Starting CI/CD Pipeline Health Check...${NC}"

# Initialize health report
cat > "$HEALTH_REPORT" << EOF
# CI/CD Pipeline Health Report

**Generated:** $(date)
**Project:** mem0-stack
**Branch:** $(git branch --show-current)
**Commit:** $(git rev-parse --short HEAD)

## Health Check Results

EOF

# Counter for issues
ISSUE_COUNT=0
SUCCESS_COUNT=0

# Function to log success
log_success() {
    echo -e "${GREEN}✅ $1${NC}"
    echo "- ✅ $1" >> "$HEALTH_REPORT"
    ((SUCCESS_COUNT++))
}

# Function to log warning
log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
    echo "- ⚠️  $1" >> "$HEALTH_REPORT"
    ((ISSUE_COUNT++))
}

# Function to log error
log_error() {
    echo -e "${RED}❌ $1${NC}"
    echo "- ❌ $1" >> "$HEALTH_REPORT"
    ((ISSUE_COUNT++))
}

# Function to log info
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
    echo "- ℹ️  $1" >> "$HEALTH_REPORT"
}

echo -e "\n## 🔧 Configuration Files" >> "$HEALTH_REPORT"

# Check essential configuration files
echo -e "${BLUE}Checking configuration files...${NC}"

if [[ -f "$PROJECT_ROOT/.editorconfig" ]]; then
    log_success "EditorConfig file exists"
else
    log_error "EditorConfig file missing"
fi

if [[ -f "$PROJECT_ROOT/.gitattributes" ]]; then
    log_success "Git attributes file exists"
else
    log_error "Git attributes file missing"
fi

if [[ -f "$PROJECT_ROOT/.pre-commit-config.yaml" ]]; then
    log_success "Pre-commit configuration exists"
else
    log_error "Pre-commit configuration missing"
fi

if [[ -f "$PROJECT_ROOT/pyproject.toml" ]]; then
    log_success "Python project configuration exists"
else
    log_error "pyproject.toml missing"
fi

echo -e "\n## 🐍 Python Environment" >> "$HEALTH_REPORT"

# Check Python environment
echo -e "${BLUE}Checking Python environment...${NC}"

if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    log_success "Python3 available: $PYTHON_VERSION"
else
    log_error "Python3 not found"
fi

if command -v pip &> /dev/null; then
    log_success "pip available"
else
    log_error "pip not found"
fi

# Check virtual environment
if [[ -n "${VIRTUAL_ENV:-}" ]]; then
    log_success "Virtual environment active: $VIRTUAL_ENV"
elif [[ -d "$PROJECT_ROOT/venv" ]]; then
    log_warning "Virtual environment exists but not activated"
else
    log_warning "No virtual environment found"
fi

echo -e "\n## 📦 Dependencies" >> "$HEALTH_REPORT"

# Check dependencies
echo -e "${BLUE}Checking dependencies...${NC}"

for req_file in "requirements.txt" "requirements-test.txt" "openmemory/api/requirements.txt"; do
    if [[ -f "$PROJECT_ROOT/$req_file" ]]; then
        log_success "Requirements file exists: $req_file"
    else
        log_warning "Requirements file missing: $req_file"
    fi
done

# Check if black is installed
if command -v black &> /dev/null; then
    BLACK_VERSION=$(black --version)
    log_success "Black formatter available: $BLACK_VERSION"
else
    log_error "Black formatter not installed"
fi

# Check if pre-commit is installed
if command -v pre-commit &> /dev/null; then
    log_success "Pre-commit available"
else
    log_error "Pre-commit not installed"
fi

echo -e "\n## 🧪 Testing Tools" >> "$HEALTH_REPORT"

# Check testing tools
echo -e "${BLUE}Checking testing tools...${NC}"

if command -v pytest &> /dev/null; then
    log_success "pytest available"
else
    log_error "pytest not installed"
fi

if python3 -c "import pytest" 2>/dev/null; then
    log_success "pytest importable"
else
    log_error "pytest not importable"
fi

echo -e "\n## 🐳 Docker Environment" >> "$HEALTH_REPORT"

# Check Docker
echo -e "${BLUE}Checking Docker environment...${NC}"

if command -v docker &> /dev/null; then
    if docker --version &> /dev/null; then
        DOCKER_VERSION=$(docker --version)
        log_success "Docker available: $DOCKER_VERSION"
    else
        log_error "Docker not responding"
    fi
else
    log_error "Docker not installed"
fi

if command -v docker-compose &> /dev/null; then
    log_success "Docker Compose available"
else
    log_warning "Docker Compose not found"
fi

# Check if Docker daemon is running
if docker info &> /dev/null; then
    log_success "Docker daemon running"
else
    log_warning "Docker daemon not running"
fi

echo -e "\n## 📁 Project Structure" >> "$HEALTH_REPORT"

# Check project structure
echo -e "${BLUE}Checking project structure...${NC}"

ESSENTIAL_DIRS=("tests" "openmemory/api" "shared" "scripts")
for dir in "${ESSENTIAL_DIRS[@]}"; do
    if [[ -d "$PROJECT_ROOT/$dir" ]]; then
        log_success "Directory exists: $dir"
    else
        log_error "Directory missing: $dir"
    fi
done

# Check for test files
TEST_FILES=$(find "$PROJECT_ROOT/tests" -name "test_*.py" 2>/dev/null | wc -l)
if [[ $TEST_FILES -gt 0 ]]; then
    log_success "Test files found: $TEST_FILES files"
else
    log_error "No test files found"
fi

echo -e "\n## 🔒 Security" >> "$HEALTH_REPORT"

# Security checks
echo -e "${BLUE}Checking security configuration...${NC}"

# Check for secrets in environment
if [[ -f "$PROJECT_ROOT/.env" ]]; then
    log_warning ".env file exists - ensure it's in .gitignore"
else
    log_info "No .env file found (recommended for production)"
fi

# Check .gitignore
if [[ -f "$PROJECT_ROOT/.gitignore" ]]; then
    if grep -q "\.env" "$PROJECT_ROOT/.gitignore"; then
        log_success ".env files ignored in git"
    else
        log_warning ".env files not ignored in git"
    fi
    log_success ".gitignore exists"
else
    log_error ".gitignore missing"
fi

echo -e "\n## 🚀 CI/CD Configuration" >> "$HEALTH_REPORT"

# Check CI/CD configuration
echo -e "${BLUE}Checking CI/CD configuration...${NC}"

if [[ -f "$PROJECT_ROOT/.github/workflows/test.yml" ]]; then
    log_success "GitHub Actions workflow exists"
else
    log_error "GitHub Actions workflow missing"
fi

# Check if GitHub Actions syntax is valid
if command -v yamllint &> /dev/null; then
    if yamllint "$PROJECT_ROOT/.github/workflows/test.yml" &> /dev/null; then
        log_success "GitHub Actions workflow syntax valid"
    else
        log_warning "GitHub Actions workflow syntax issues"
    fi
fi

echo -e "\n## 🔧 Automated Fixes" >> "$HEALTH_REPORT"

# Provide automated fixes
echo -e "${BLUE}Generating automated fixes...${NC}"

cat >> "$HEALTH_REPORT" << 'EOF'

## 🛠️ Recommended Actions

### High Priority Issues
EOF

if [[ $ISSUE_COUNT -gt 0 ]]; then
    cat >> "$HEALTH_REPORT" << 'EOF'

**Install missing dependencies:**
```bash
# Install pre-commit if missing
pipx install pre-commit
pre-commit install

# Install Python dependencies
pip install -r requirements-test.txt

# Install Black formatter
pip install black

# Install pytest
pip install pytest
```

**Fix formatting issues:**
```bash
# Run Black formatter
black openmemory/ shared/ tests/

# Run import sorting
python3 -m isort openmemory/ shared/ tests/ --profile black

# Check pre-commit hooks
pre-commit run --all-files
```

**Docker setup:**
```bash
# Start Docker daemon (if not running)
sudo systemctl start docker

# Build containers
docker-compose build

# Run services
docker-compose up -d
```
EOF
fi

# Summary
echo -e "\n## 📊 Summary" >> "$HEALTH_REPORT"

cat >> "$HEALTH_REPORT" << EOF

- **Successful Checks:** $SUCCESS_COUNT
- **Issues Found:** $ISSUE_COUNT
- **Overall Status:** $(if [[ $ISSUE_COUNT -eq 0 ]]; then echo "✅ HEALTHY"; elif [[ $ISSUE_COUNT -lt 5 ]]; then echo "⚠️ NEEDS ATTENTION"; else echo "❌ CRITICAL ISSUES"; fi)

EOF

# Display summary
echo -e "\n${BLUE}📊 Health Check Summary:${NC}"
echo -e "${GREEN}Successful checks: $SUCCESS_COUNT${NC}"
echo -e "${RED}Issues found: $ISSUE_COUNT${NC}"

if [[ $ISSUE_COUNT -eq 0 ]]; then
    echo -e "${GREEN}🎉 Pipeline is healthy!${NC}"
    exit 0
elif [[ $ISSUE_COUNT -lt 5 ]]; then
    echo -e "${YELLOW}⚠️  Pipeline needs attention${NC}"
    exit 1
else
    echo -e "${RED}🚨 Pipeline has critical issues${NC}"
    exit 2
fi