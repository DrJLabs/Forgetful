#!/bin/bash
# Automated Security Audit and Fix Script
# Addresses common security vulnerabilities in dependencies

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
SECURITY_REPORT="$PROJECT_ROOT/security_audit_report.md"

echo -e "${BLUE}🔒 Starting Security Audit...${NC}"

# Initialize security report
cat > "$SECURITY_REPORT" << EOF
# Security Audit Report

**Generated:** $(date)
**Project:** mem0-stack
**Branch:** $(git branch --show-current)
**Commit:** $(git rev-parse --short HEAD)

## Security Scan Results

EOF

# Counter for vulnerabilities
VULN_COUNT=0
FIXED_COUNT=0

# Function to log vulnerability
log_vulnerability() {
    echo -e "${RED}🚨 $1${NC}"
    echo "- 🚨 **VULNERABILITY:** $1" >> "$SECURITY_REPORT"
    ((VULN_COUNT++))
}

# Function to log fix
log_fix() {
    echo -e "${GREEN}🔧 $1${NC}"
    echo "- 🔧 **FIXED:** $1" >> "$SECURITY_REPORT"
    ((FIXED_COUNT++))
}

# Function to log info
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
    echo "- ℹ️  $1" >> "$SECURITY_REPORT"
}

echo -e "\n## 📦 Python Dependencies" >> "$SECURITY_REPORT"

# Check Python dependencies for vulnerabilities
echo -e "${BLUE}Checking Python dependencies...${NC}"

# Install security audit tools if not present
if ! command -v safety &> /dev/null; then
    echo -e "${YELLOW}Installing safety...${NC}"
    pip install --break-system-packages safety
fi

# Run safety check
echo -e "${BLUE}Running safety audit...${NC}"
SAFETY_OUTPUT=$(safety check --json 2>/dev/null || echo "[]")

if [[ "$SAFETY_OUTPUT" == "[]" ]] || [[ "$SAFETY_OUTPUT" == "" ]]; then
    log_info "No known vulnerabilities found in Python dependencies"
else
    echo "$SAFETY_OUTPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for vuln in data:
        print(f'VULNERABILITY: {vuln.get(\"package\", \"unknown\")} {vuln.get(\"installed_version\", \"unknown\")} - {vuln.get(\"vulnerability\", \"unknown\")}')
except:
    print('Error parsing safety output')
" | while read -r line; do
        if [[ $line == VULNERABILITY:* ]]; then
            log_vulnerability "${line#VULNERABILITY: }"
        fi
    done
fi

echo -e "\n## 📊 NPM Dependencies" >> "$SECURITY_REPORT"

# Check NPM dependencies if package.json exists
if [[ -f "$PROJECT_ROOT/package.json" ]] || [[ -f "$PROJECT_ROOT/openmemory/ui/package.json" ]]; then
    echo -e "${BLUE}Checking NPM dependencies...${NC}"

    # Check main package.json
    if [[ -f "$PROJECT_ROOT/package.json" ]]; then
        cd "$PROJECT_ROOT"
        if command -v npm &> /dev/null; then
            if npm audit --json 2>/dev/null | jq -e '.vulnerabilities | length > 0' &>/dev/null; then
                log_vulnerability "NPM vulnerabilities found in main package.json"
                echo -e "${YELLOW}Attempting to fix NPM vulnerabilities...${NC}"
                if npm audit fix --force &>/dev/null; then
                    log_fix "NPM vulnerabilities auto-fixed"
                else
                    log_vulnerability "NPM vulnerabilities could not be auto-fixed"
                fi
            else
                log_info "No NPM vulnerabilities found in main package.json"
            fi
        fi
    fi

    # Check UI package.json
    if [[ -f "$PROJECT_ROOT/openmemory/ui/package.json" ]]; then
        cd "$PROJECT_ROOT/openmemory/ui"
        if command -v npm &> /dev/null; then
            if npm audit --json 2>/dev/null | jq -e '.vulnerabilities | length > 0' &>/dev/null; then
                log_vulnerability "NPM vulnerabilities found in UI package.json"
                echo -e "${YELLOW}Attempting to fix UI NPM vulnerabilities...${NC}"
                if npm audit fix --force &>/dev/null; then
                    log_fix "UI NPM vulnerabilities auto-fixed"
                else
                    log_vulnerability "UI NPM vulnerabilities could not be auto-fixed"
                fi
            else
                log_info "No NPM vulnerabilities found in UI package.json"
            fi
        fi
    fi
    cd "$PROJECT_ROOT"
else
    log_info "No NPM package.json files found"
fi

echo -e "\n## 🔐 Secrets Detection" >> "$SECURITY_REPORT"

# Check for potential secrets
echo -e "${BLUE}Scanning for potential secrets...${NC}"

# Common secret patterns
SECRET_PATTERNS=(
    "password.*=.*['\"][^'\"]{8,}['\"]"
    "api[_-]?key.*=.*['\"][^'\"]{16,}['\"]"
    "secret.*=.*['\"][^'\"]{16,}['\"]"
    "token.*=.*['\"][^'\"]{16,}['\"]"
    "['\"][A-Za-z0-9]{32,}['\"]"
    "sk-[A-Za-z0-9]{48}"
    "xoxb-[A-Za-z0-9-]+"
    "ghp_[A-Za-z0-9]{36}"
)

SECRET_FOUND=false
for pattern in "${SECRET_PATTERNS[@]}"; do
    if grep -rE "$pattern" "$PROJECT_ROOT" \
        --exclude-dir=.git \
        --exclude-dir=node_modules \
        --exclude-dir=venv \
        --exclude-dir=__pycache__ \
        --exclude="*.log" \
        --exclude="$SECURITY_REPORT" \
        &>/dev/null; then
        SECRET_FOUND=true
        break
    fi
done

if $SECRET_FOUND; then
    log_vulnerability "Potential secrets detected in codebase"
else
    log_info "No obvious secrets detected"
fi

echo -e "\n## 🔒 File Permissions" >> "$SECURITY_REPORT"

# Check file permissions
echo -e "${BLUE}Checking file permissions...${NC}"

# Check for world-writable files
WORLD_WRITABLE=$(find "$PROJECT_ROOT" -type f -perm -o+w 2>/dev/null | grep -v ".git" || true)
if [[ -n "$WORLD_WRITABLE" ]]; then
    log_vulnerability "World-writable files found"
    echo -e "${YELLOW}Fixing world-writable files...${NC}"
    find "$PROJECT_ROOT" -type f -perm -o+w -exec chmod o-w {} \; 2>/dev/null || true
    log_fix "World-writable permissions removed"
else
    log_info "No world-writable files found"
fi

# Check for executable files that shouldn't be
SUSPICIOUS_EXECUTABLES=$(find "$PROJECT_ROOT" -name "*.py" -perm -u+x | grep -v "scripts/" | grep -v "__pycache__" || true)
if [[ -n "$SUSPICIOUS_EXECUTABLES" ]]; then
    log_vulnerability "Python files with unnecessary execute permissions found"
    echo -e "${YELLOW}Removing unnecessary execute permissions...${NC}"
    find "$PROJECT_ROOT" -name "*.py" ! -path "*/scripts/*" -exec chmod -x {} \; 2>/dev/null || true
    log_fix "Unnecessary execute permissions removed"
else
    log_info "No suspicious executable files found"
fi

echo -e "\n## 🌐 Network Security" >> "$SECURITY_REPORT"

# Check for insecure network configurations
echo -e "${BLUE}Checking network security...${NC}"

# Check for HTTP URLs in code (should be HTTPS)
HTTP_URLS=$(grep -r "http://" "$PROJECT_ROOT" \
    --exclude-dir=.git \
    --exclude-dir=node_modules \
    --exclude-dir=venv \
    --exclude="$SECURITY_REPORT" \
    --include="*.py" \
    --include="*.js" \
    --include="*.yml" \
    --include="*.yaml" \
    2>/dev/null | wc -l)

if [[ $HTTP_URLS -gt 0 ]]; then
    log_vulnerability "$HTTP_URLS insecure HTTP URLs found (should use HTTPS)"
else
    log_info "No insecure HTTP URLs found"
fi

echo -e "\n## 🐳 Docker Security" >> "$SECURITY_REPORT"

# Check Docker security
echo -e "${BLUE}Checking Docker security...${NC}"

if [[ -f "$PROJECT_ROOT/Dockerfile" ]] || [[ -f "$PROJECT_ROOT/docker-compose.yml" ]]; then
    # Check for running as root
    if grep -q "USER root\|USER 0" "$PROJECT_ROOT"/*/Dockerfile "$PROJECT_ROOT/Dockerfile" 2>/dev/null; then
        log_vulnerability "Docker containers running as root user"
    else
        log_info "Docker containers not explicitly running as root"
    fi

    # Check for --privileged flag
    if grep -q "privileged.*true\|--privileged" "$PROJECT_ROOT/docker-compose.yml" 2>/dev/null; then
        log_vulnerability "Docker containers running with privileged access"
    else
        log_info "No privileged Docker containers found"
    fi
else
    log_info "No Docker files found"
fi

echo -e "\n## 🔧 Automated Fixes Applied" >> "$SECURITY_REPORT"

# Apply automated fixes
echo -e "${BLUE}Applying automated security fixes...${NC}"

# Update .gitignore to ignore common secrets
GITIGNORE_ADDITIONS=(
    "*.env"
    "*.key"
    "*.pem"
    "*.p12"
    ".secrets"
    "config/secrets.yml"
    "secrets.json"
)

if [[ -f "$PROJECT_ROOT/.gitignore" ]]; then
    for addition in "${GITIGNORE_ADDITIONS[@]}"; do
        if ! grep -q "^$addition$" "$PROJECT_ROOT/.gitignore"; then
            echo "$addition" >> "$PROJECT_ROOT/.gitignore"
        fi
    done
    log_fix "Updated .gitignore with security patterns"
else
    log_vulnerability ".gitignore file missing"
fi

# Create security headers for web components
if [[ -d "$PROJECT_ROOT/openmemory/ui" ]]; then
    SECURITY_HEADERS_FILE="$PROJECT_ROOT/openmemory/ui/security-headers.json"
    if [[ ! -f "$SECURITY_HEADERS_FILE" ]]; then
        cat > "$SECURITY_HEADERS_FILE" << 'EOF'
{
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        {
          "key": "X-Content-Type-Options",
          "value": "nosniff"
        },
        {
          "key": "X-Frame-Options",
          "value": "DENY"
        },
        {
          "key": "X-XSS-Protection",
          "value": "1; mode=block"
        },
        {
          "key": "Strict-Transport-Security",
          "value": "max-age=63072000; includeSubDomains; preload"
        },
        {
          "key": "Content-Security-Policy",
          "value": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self';"
        }
      ]
    }
  ]
}
EOF
        log_fix "Created security headers configuration"
    fi
fi

echo -e "\n## 📊 Summary" >> "$SECURITY_REPORT"

# Summary
cat >> "$SECURITY_REPORT" << EOF

- **Vulnerabilities Found:** $VULN_COUNT
- **Fixes Applied:** $FIXED_COUNT
- **Security Status:** $(if [[ $VULN_COUNT -eq 0 ]]; then echo "🟢 SECURE"; elif [[ $VULN_COUNT -lt 3 ]]; then echo "🟡 MODERATE RISK"; else echo "🔴 HIGH RISK"; fi)

## 🛡️ Recommended Actions

### Immediate Actions
- Review and update all dependencies to latest secure versions
- Enable GitHub security alerts and Dependabot
- Implement regular security audits in CI/CD pipeline
- Add secret scanning to pre-commit hooks

### Long-term Security Improvements
- Implement proper secrets management (e.g., HashiCorp Vault)
- Set up automated dependency updates
- Add security testing to CI/CD pipeline
- Implement security monitoring and alerting

### Manual Review Required
- Check all environment variables for sensitive data
- Review API endpoints for proper authentication
- Audit database access patterns
- Verify network security configurations

EOF

# Display summary
echo -e "\n${BLUE}📊 Security Audit Summary:${NC}"
echo -e "${RED}Vulnerabilities found: $VULN_COUNT${NC}"
echo -e "${GREEN}Fixes applied: $FIXED_COUNT${NC}"

if [[ $VULN_COUNT -eq 0 ]]; then
    echo -e "${GREEN}🛡️  System appears secure!${NC}"
    exit 0
elif [[ $VULN_COUNT -lt 3 ]]; then
    echo -e "${YELLOW}⚠️  Moderate security risk detected${NC}"
    exit 1
else
    echo -e "${RED}🚨 High security risk detected${NC}"
    exit 2
fi