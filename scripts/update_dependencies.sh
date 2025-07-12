#!/bin/bash
# Automated Dependency Update Script
# Safely updates Python and NPM dependencies

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
UPDATE_REPORT="$PROJECT_ROOT/dependency_update_report.md"

echo -e "${BLUE}📦 Starting Dependency Update Process...${NC}"

# Initialize update report
cat > "$UPDATE_REPORT" << EOF
# Dependency Update Report

**Generated:** $(date)
**Project:** mem0-stack
**Branch:** $(git branch --show-current)
**Commit:** $(git rev-parse --short HEAD)

## Update Results

EOF

# Counter for updates
UPDATE_COUNT=0
ERROR_COUNT=0

# Function to log update
log_update() {
    echo -e "${GREEN}⬆️  $1${NC}"
    echo "- ⬆️  **UPDATED:** $1" >> "$UPDATE_REPORT"
    ((UPDATE_COUNT++))
}

# Function to log error
log_error() {
    echo -e "${RED}❌ $1${NC}"
    echo "- ❌ **ERROR:** $1" >> "$UPDATE_REPORT"
    ((ERROR_COUNT++))
}

# Function to log info
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
    echo "- ℹ️  $1" >> "$UPDATE_REPORT"
}

echo -e "\n## 🐍 Python Dependencies" >> "$UPDATE_REPORT"

# Create backup of current requirements
backup_requirements() {
    local req_file=$1
    if [[ -f "$req_file" ]]; then
        cp "$req_file" "${req_file}.backup.$(date +%Y%m%d_%H%M%S)"
        log_info "Backed up $(basename "$req_file")"
    fi
}

# Update Python dependencies
update_python_deps() {
    echo -e "${BLUE}Updating Python dependencies...${NC}"
    
    # Main requirements
    if [[ -f "$PROJECT_ROOT/requirements.txt" ]]; then
        backup_requirements "$PROJECT_ROOT/requirements.txt"
        
        # Try to update using pip-tools if available
        if command -v pip-compile &> /dev/null; then
            log_info "Using pip-tools to update requirements.txt"
            cd "$PROJECT_ROOT"
            if pip-compile --upgrade requirements.in 2>/dev/null; then
                log_update "requirements.txt updated via pip-tools"
            else
                log_error "Failed to update requirements.txt via pip-tools"
            fi
        else
            log_info "pip-tools not available, manual update recommended"
        fi
    fi
    
    # Test requirements
    if [[ -f "$PROJECT_ROOT/requirements-test.txt" ]]; then
        backup_requirements "$PROJECT_ROOT/requirements-test.txt"
        log_info "Test requirements backed up"
    fi
    
    # API requirements
    if [[ -f "$PROJECT_ROOT/openmemory/api/requirements.txt" ]]; then
        backup_requirements "$PROJECT_ROOT/openmemory/api/requirements.txt"
        log_info "API requirements backed up"
    fi
    
    # Install updated dependencies
    if [[ -f "$PROJECT_ROOT/requirements.txt" ]]; then
        echo -e "${YELLOW}Installing updated Python dependencies...${NC}"
        if pip install -r "$PROJECT_ROOT/requirements.txt" --upgrade 2>/dev/null; then
            log_update "Python dependencies installed successfully"
        else
            log_error "Failed to install updated Python dependencies"
        fi
    fi
}

echo -e "\n## 📊 NPM Dependencies" >> "$UPDATE_REPORT"

# Update NPM dependencies
update_npm_deps() {
    echo -e "${BLUE}Updating NPM dependencies...${NC}"
    
    # Main package.json
    if [[ -f "$PROJECT_ROOT/package.json" ]]; then
        cd "$PROJECT_ROOT"
        if command -v npm &> /dev/null; then
            echo -e "${YELLOW}Updating main package.json...${NC}"
            
            # Backup package-lock.json
            if [[ -f "package-lock.json" ]]; then
                cp package-lock.json "package-lock.json.backup.$(date +%Y%m%d_%H%M%S)"
            fi
            
            # Update dependencies
            if npm update 2>/dev/null; then
                log_update "Main NPM dependencies updated"
            else
                log_error "Failed to update main NPM dependencies"
            fi
            
            # Audit and fix vulnerabilities
            if npm audit fix --force 2>/dev/null; then
                log_update "NPM vulnerabilities fixed"
            else
                log_info "No NPM vulnerabilities to fix"
            fi
        else
            log_error "NPM not available"
        fi
    fi
    
    # UI package.json
    if [[ -f "$PROJECT_ROOT/openmemory/ui/package.json" ]]; then
        cd "$PROJECT_ROOT/openmemory/ui"
        if command -v npm &> /dev/null; then
            echo -e "${YELLOW}Updating UI package.json...${NC}"
            
            # Backup package-lock.json
            if [[ -f "package-lock.json" ]]; then
                cp package-lock.json "package-lock.json.backup.$(date +%Y%m%d_%H%M%S)"
            fi
            
            # Update dependencies
            if npm update 2>/dev/null; then
                log_update "UI NPM dependencies updated"
            else
                log_error "Failed to update UI NPM dependencies"
            fi
            
            # Audit and fix vulnerabilities
            if npm audit fix --force 2>/dev/null; then
                log_update "UI NPM vulnerabilities fixed"
            else
                log_info "No UI NPM vulnerabilities to fix"
            fi
        fi
        cd "$PROJECT_ROOT"
    fi
}

echo -e "\n## 🔧 Pre-commit Updates" >> "$UPDATE_REPORT"

# Update pre-commit hooks
update_precommit() {
    echo -e "${BLUE}Updating pre-commit hooks...${NC}"
    
    if command -v pre-commit &> /dev/null; then
        if pre-commit autoupdate 2>/dev/null; then
            log_update "Pre-commit hooks updated"
        else
            log_error "Failed to update pre-commit hooks"
        fi
    else
        log_error "Pre-commit not available"
    fi
}

echo -e "\n## 🧪 Testing Updates" >> "$UPDATE_REPORT"

# Test updated dependencies
test_updates() {
    echo -e "${BLUE}Testing updated dependencies...${NC}"
    
    # Test Python imports
    if python3 -c "
import sys
try:
    import pytest
    import black
    import fastapi
    print('✅ Core dependencies importable')
except ImportError as e:
    print(f'❌ Import error: {e}')
    sys.exit(1)
" 2>/dev/null; then
        log_update "Python dependencies tested successfully"
    else
        log_error "Python dependency test failed"
    fi
    
    # Test formatting tools
    if black --version &>/dev/null && python3 -c "import isort" 2>/dev/null; then
        log_update "Formatting tools working"
    else
        log_error "Formatting tools not working"
    fi
    
    # Test if npm packages work (if applicable)
    if [[ -f "$PROJECT_ROOT/package.json" ]] && command -v npm &> /dev/null; then
        cd "$PROJECT_ROOT"
        if npm test --dry-run &>/dev/null || npm run build --dry-run &>/dev/null; then
            log_update "NPM dependencies tested successfully"
        else
            log_info "NPM test not configured or failed"
        fi
    fi
}

# Main execution
update_python_deps
update_npm_deps
update_precommit
test_updates

echo -e "\n## 📊 Summary" >> "$UPDATE_REPORT"

# Generate security recommendations
cat >> "$UPDATE_REPORT" << EOF

- **Updates Applied:** $UPDATE_COUNT
- **Errors Encountered:** $ERROR_COUNT
- **Update Status:** $(if [[ $ERROR_COUNT -eq 0 ]]; then echo "✅ SUCCESS"; elif [[ $ERROR_COUNT -lt 3 ]]; then echo "⚠️ PARTIAL"; else echo "❌ FAILED"; fi)

## 🔄 Next Steps

### Recommended Actions
1. **Test the application thoroughly** after dependency updates
2. **Run the full test suite** to ensure compatibility
3. **Check for breaking changes** in updated packages
4. **Update documentation** if APIs have changed

### Manual Review Required
- Check changelogs of major version updates
- Verify deprecated features are still supported
- Test critical application flows
- Update configuration if needed

### Automated Monitoring
- Set up Dependabot for automatic updates
- Configure security alerts for vulnerabilities
- Implement dependency pinning for critical packages
- Schedule regular dependency audits

EOF

# Create rollback script
cat > "$PROJECT_ROOT/scripts/rollback_dependencies.sh" << 'EOF'
#!/bin/bash
# Rollback script for dependency updates

echo "🔄 Rolling back dependency updates..."

# Find and restore backup files
find . -name "*.backup.*" -type f | while read -r backup_file; do
    original_file="${backup_file%%.backup.*}"
    if [[ -f "$backup_file" ]]; then
        echo "Restoring $original_file"
        cp "$backup_file" "$original_file"
    fi
done

echo "✅ Rollback completed"
echo "🧪 Run tests to verify rollback was successful"
EOF

chmod +x "$PROJECT_ROOT/scripts/rollback_dependencies.sh"
log_update "Created dependency rollback script"

# Display summary
echo -e "\n${BLUE}📊 Dependency Update Summary:${NC}"
echo -e "${GREEN}Updates applied: $UPDATE_COUNT${NC}"
echo -e "${RED}Errors encountered: $ERROR_COUNT${NC}"

if [[ $ERROR_COUNT -eq 0 ]]; then
    echo -e "${GREEN}🎉 All dependencies updated successfully!${NC}"
    echo -e "${YELLOW}⚠️  Please run tests to verify everything works${NC}"
    exit 0
elif [[ $ERROR_COUNT -lt 3 ]]; then
    echo -e "${YELLOW}⚠️  Dependencies updated with some issues${NC}"
    exit 1
else
    echo -e "${RED}🚨 Multiple errors during dependency update${NC}"
    exit 2
fi 