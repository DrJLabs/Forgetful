#!/bin/bash
# ================================================================
# mem0-stack Environment Setup Script
# ================================================================
# 
# This script automates the setup of environment configuration
# for the mem0-stack project, ensuring consistent deployments
# and reducing configuration errors.
#
# Features:
# - Interactive and non-interactive modes
# - Environment file generation from template
# - Validation and testing
# - Docker service preparation
# - Comprehensive error checking
#
# Usage:
#   ./scripts/setup_environment.sh
#   ./scripts/setup_environment.sh --interactive
#   ./scripts/setup_environment.sh --production
#   ./scripts/setup_environment.sh --validate-only

set -euo pipefail

# ================================================================
# Configuration and Constants
# ================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${PROJECT_ROOT}/.env"
ENV_TEMPLATE="${PROJECT_ROOT}/env.template"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Default values
INTERACTIVE_MODE=false
PRODUCTION_MODE=false
VALIDATE_ONLY=false
SKIP_DOCKER=false
FORCE_OVERWRITE=false

# ================================================================
# Utility Functions
# ================================================================

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_section() {
    echo -e "\n${PURPLE}🔧 $1${NC}"
    echo "$(printf '%.0s─' {1..50})"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Prompt for user input with default value
prompt_with_default() {
    local prompt="$1"
    local default="$2"
    local var_name="$3"
    local is_secret="${4:-false}"
    
    if [[ "$INTERACTIVE_MODE" == "true" ]]; then
        if [[ "$is_secret" == "true" ]]; then
            echo -n "$prompt [$default]: "
            read -s user_input
            echo
        else
            echo -n "$prompt [$default]: "
            read user_input
        fi
        
        if [[ -n "$user_input" ]]; then
            eval "$var_name='$user_input'"
        else
            eval "$var_name='$default'"
        fi
    else
        eval "$var_name='$default'"
    fi
}

# Generate secure random password
generate_password() {
    local length="${1:-16}"
    if command_exists openssl; then
        openssl rand -base64 "$length" | tr -d "=+/" | cut -c1-"$length"
    elif command_exists python3; then
        python3 -c "import secrets, string; print(''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range($length)))"
    else
        # Fallback to date-based generation
        date +%s | sha256sum | base64 | head -c "$length"
    fi
}

# ================================================================
# Validation Functions
# ================================================================

validate_prerequisites() {
    log_section "Checking Prerequisites"
    
    local errors=0
    
    # Check Docker
    if ! command_exists docker; then
        log_error "Docker is not installed. Please install Docker first."
        ((errors++))
    else
        log_success "Docker is installed"
    fi
    
    # Check Docker Compose
    if ! docker compose version >/dev/null 2>&1; then
        log_error "Docker Compose is not available. Please install Docker Compose V2."
        ((errors++))
    else
        log_success "Docker Compose is available"
    fi
    
    # Check Python
    if ! command_exists python3; then
        log_warning "Python 3 is not installed. Some validation features will be limited."
    else
        log_success "Python 3 is available"
    fi
    
    # Check required directories
    if [[ ! -f "$ENV_TEMPLATE" ]]; then
        log_error "Environment template file not found: $ENV_TEMPLATE"
        ((errors++))
    else
        log_success "Environment template found"
    fi
    
    return $errors
}

validate_environment_file() {
    log_section "Validating Environment Configuration"
    
    if [[ ! -f "$ENV_FILE" ]]; then
        log_error "Environment file not found: $ENV_FILE"
        return 1
    fi
    
    # Check for required variables
    local required_vars=(
        "DATABASE_USER"
        "DATABASE_PASSWORD"
        "NEO4J_PASSWORD"
        "OPENAI_API_KEY"
        "APP_USER_ID"
    )
    
    local missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if ! grep -q "^${var}=" "$ENV_FILE" || grep -q "^${var}=.*your_.*here" "$ENV_FILE"; then
            missing_vars+=("$var")
        fi
    done
    
    if [[ ${#missing_vars[@]} -eq 0 ]]; then
        log_success "All required variables are configured"
        return 0
    else
        log_error "Missing or unconfigured variables: ${missing_vars[*]}"
        return 1
    fi
}

# ================================================================
# Setup Functions
# ================================================================

create_data_directories() {
    log_section "Creating Data Directories"
    
    local directories=(
        "data"
        "data/postgres"
        "data/neo4j"
        "data/mem0"
        "data/mem0/history"
    )
    
    for dir in "${directories[@]}"; do
        local full_path="${PROJECT_ROOT}/${dir}"
        if [[ ! -d "$full_path" ]]; then
            mkdir -p "$full_path"
            log_success "Created directory: $dir"
        else
            log_info "Directory already exists: $dir"
        fi
        
        # Set appropriate permissions
        chmod 755 "$full_path"
    done
}

setup_environment_file() {
    log_section "Setting Up Environment File"
    
    # Check if .env already exists
    if [[ -f "$ENV_FILE" && "$FORCE_OVERWRITE" != "true" ]]; then
        if [[ "$INTERACTIVE_MODE" == "true" ]]; then
            echo -n "Environment file already exists. Overwrite? (y/N): "
            read -r response
            if [[ ! "$response" =~ ^[Yy]$ ]]; then
                log_info "Skipping environment file creation"
                return 0
            fi
        else
            log_warning "Environment file already exists. Use --force to overwrite."
            return 0
        fi
    fi
    
    # Copy template to .env
    cp "$ENV_TEMPLATE" "$ENV_FILE"
    log_success "Created environment file from template"
    
    # Collect configuration values
    collect_configuration_values
    
    # Apply configuration to .env file
    apply_configuration_values
    
    log_success "Environment file configured successfully"
}

collect_configuration_values() {
    log_section "Collecting Configuration Values"
    
    # Database configuration
    if [[ "$PRODUCTION_MODE" == "true" ]]; then
        DATABASE_USER="prod_user"
        DATABASE_PASSWORD=$(generate_password 20)
        NEO4J_PASSWORD=$(generate_password 16)
        APP_USER_ID="production_user"
        APP_ENVIRONMENT="production"
        APP_DEBUG="false"
        APP_LOG_LEVEL="WARNING"
    else
        DATABASE_USER="drj"
        DATABASE_PASSWORD=$(generate_password 16)
        NEO4J_PASSWORD=$(generate_password 12)
        APP_USER_ID="drj"
        APP_ENVIRONMENT="development"
        APP_DEBUG="true"
        APP_LOG_LEVEL="INFO"
    fi
    
    # Interactive prompts
    if [[ "$INTERACTIVE_MODE" == "true" ]]; then
        echo -e "\n${CYAN}📝 Configuration Setup${NC}"
        echo "Please provide the following configuration values:"
        echo "(Press Enter to use default values shown in brackets)"
        echo
        
        prompt_with_default "Database username" "$DATABASE_USER" "DATABASE_USER"
        prompt_with_default "Database password" "$DATABASE_PASSWORD" "DATABASE_PASSWORD" "true"
        prompt_with_default "Neo4j password" "$NEO4J_PASSWORD" "NEO4J_PASSWORD" "true"
        prompt_with_default "OpenAI API key" "sk-proj-your-key-here" "OPENAI_API_KEY" "true"
        prompt_with_default "Application user ID" "$APP_USER_ID" "APP_USER_ID"
        prompt_with_default "Environment" "$APP_ENVIRONMENT" "APP_ENVIRONMENT"
        prompt_with_default "Debug mode" "$APP_DEBUG" "APP_DEBUG"
        prompt_with_default "Log level" "$APP_LOG_LEVEL" "APP_LOG_LEVEL"
    else
        # Non-interactive mode - need OpenAI API key from environment or prompt
        if [[ -z "${OPENAI_API_KEY:-}" ]]; then
            if [[ "$PRODUCTION_MODE" != "true" ]]; then
                log_warning "OPENAI_API_KEY not set. Please set it manually in .env file."
                OPENAI_API_KEY="sk-proj-your-openai-api-key-here"
            else
                log_error "OPENAI_API_KEY is required for production setup"
                exit 1
            fi
        fi
    fi
    
    log_info "Configuration values collected"
}

apply_configuration_values() {
    log_section "Applying Configuration Values"
    
    # Replace template values in .env file
    local replacements=(
        "s/DATABASE_USER=your_username_here/DATABASE_USER=$DATABASE_USER/g"
        "s/DATABASE_PASSWORD=your_secure_password_here/DATABASE_PASSWORD=$DATABASE_PASSWORD/g"
        "s/NEO4J_PASSWORD=your_neo4j_password_here/NEO4J_PASSWORD=$NEO4J_PASSWORD/g"
        "s/OPENAI_API_KEY=sk-proj-your-openai-api-key-here/OPENAI_API_KEY=$OPENAI_API_KEY/g"
        "s/APP_USER_ID=your_username_here/APP_USER_ID=$APP_USER_ID/g"
        "s/APP_ENVIRONMENT=development/APP_ENVIRONMENT=$APP_ENVIRONMENT/g"
        "s/APP_DEBUG=false/APP_DEBUG=$APP_DEBUG/g"
        "s/APP_LOG_LEVEL=INFO/APP_LOG_LEVEL=$APP_LOG_LEVEL/g"
    )
    
    for replacement in "${replacements[@]}"; do
        sed -i.bak "$replacement" "$ENV_FILE"
    done
    
    # Remove backup file
    rm -f "${ENV_FILE}.bak"
    
    log_success "Configuration applied to environment file"
}

setup_service_environments() {
    log_section "Setting Up Service-Specific Environment Files"
    
    # OpenMemory API environment
    local api_env="${PROJECT_ROOT}/openmemory/api/.env"
    if [[ ! -f "$api_env" ]]; then
        cat > "$api_env" << EOF
# OpenMemory API Environment Variables
# Generated by setup script

# Copy from main .env file
DATABASE_HOST=postgres-mem0
DATABASE_PORT=5432
DATABASE_NAME=mem0
DATABASE_USER=$DATABASE_USER
DATABASE_PASSWORD=$DATABASE_PASSWORD

NEO4J_HOST=neo4j-mem0
NEO4J_PORT=7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=$NEO4J_PASSWORD

OPENAI_API_KEY=$OPENAI_API_KEY
OPENAI_MODEL=gpt-4o-mini

USER=$APP_USER_ID
APP_ENVIRONMENT=$APP_ENVIRONMENT

# API specific settings
API_PORT=8765
API_WORKERS=4
EOF
        log_success "Created OpenMemory API environment file"
    else
        log_info "OpenMemory API environment file already exists"
    fi
    
    # OpenMemory UI environment
    local ui_env="${PROJECT_ROOT}/openmemory/ui/.env"
    if [[ ! -f "$ui_env" ]]; then
        cat > "$ui_env" << EOF
# OpenMemory UI Environment Variables
# Generated by setup script

NEXT_PUBLIC_API_URL=http://localhost:8765
NEXT_PUBLIC_USER_ID=$APP_USER_ID
NEXT_PUBLIC_ENVIRONMENT=$APP_ENVIRONMENT

# Build settings
NEXT_PUBLIC_BUILD_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
NEXT_PUBLIC_VERSION=1.0.0
EOF
        log_success "Created OpenMemory UI environment file"
    else
        log_info "OpenMemory UI environment file already exists"
    fi
}

validate_docker_configuration() {
    log_section "Validating Docker Configuration"
    
    cd "$PROJECT_ROOT"
    
    # Test docker-compose configuration
    if docker compose config >/dev/null 2>&1; then
        log_success "Docker Compose configuration is valid"
    else
        log_error "Docker Compose configuration has errors"
        return 1
    fi
    
    # Check if required images can be built/pulled
    local services=("postgres" "neo4j" "mem0" "openmemory-mcp" "openmemory-ui")
    
    for service in "${services[@]}"; do
        if docker compose config --services | grep -q "^${service}$"; then
            log_success "Service '$service' is configured"
        else
            log_warning "Service '$service' not found in configuration"
        fi
    done
}

run_configuration_validation() {
    log_section "Running Configuration Validation"
    
    if command_exists python3 && [[ -f "${PROJECT_ROOT}/scripts/validate_config.py" ]]; then
        if python3 "${PROJECT_ROOT}/scripts/validate_config.py" --skip-connections; then
            log_success "Configuration validation passed"
            return 0
        else
            log_error "Configuration validation failed"
            return 1
        fi
    else
        log_warning "Python configuration validation not available"
        return 0
    fi
}

# ================================================================
# Main Functions
# ================================================================

show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Setup environment configuration for mem0-stack.

OPTIONS:
    -i, --interactive       Interactive mode with prompts
    -p, --production        Production mode setup
    -v, --validate-only     Only validate existing configuration
    -f, --force             Force overwrite existing files
    --skip-docker          Skip Docker-related setup and validation
    -h, --help             Show this help message

EXAMPLES:
    $0                      # Basic setup with defaults
    $0 --interactive        # Interactive setup with prompts
    $0 --production         # Production setup with secure defaults
    $0 --validate-only      # Only validate current configuration
    $0 --force --production # Force production setup, overwrite files

ENVIRONMENT VARIABLES:
    OPENAI_API_KEY         OpenAI API key (required for non-interactive mode)
    DATABASE_USER          Database username (optional)
    DATABASE_PASSWORD      Database password (optional)
    NEO4J_PASSWORD         Neo4j password (optional)

EOF
}

main() {
    echo -e "${PURPLE}🚀 mem0-stack Environment Setup${NC}"
    echo "================================================================"
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -i|--interactive)
                INTERACTIVE_MODE=true
                shift
                ;;
            -p|--production)
                PRODUCTION_MODE=true
                shift
                ;;
            -v|--validate-only)
                VALIDATE_ONLY=true
                shift
                ;;
            -f|--force)
                FORCE_OVERWRITE=true
                shift
                ;;
            --skip-docker)
                SKIP_DOCKER=true
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Validate prerequisites
    if ! validate_prerequisites; then
        log_error "Prerequisites not met. Please fix the issues above."
        exit 1
    fi
    
    # Validate-only mode
    if [[ "$VALIDATE_ONLY" == "true" ]]; then
        if validate_environment_file && run_configuration_validation; then
            log_success "Environment validation completed successfully"
            exit 0
        else
            log_error "Environment validation failed"
            exit 1
        fi
    fi
    
    # Create necessary directories
    create_data_directories
    
    # Setup environment files
    setup_environment_file
    setup_service_environments
    
    # Docker validation
    if [[ "$SKIP_DOCKER" != "true" ]]; then
        validate_docker_configuration
    fi
    
    # Final validation
    if validate_environment_file && run_configuration_validation; then
        log_success "Environment setup completed successfully!"
    else
        log_warning "Setup completed but validation found issues"
    fi
    
    # Show next steps
    echo -e "\n${CYAN}🎯 Next Steps:${NC}"
    echo "1. Review the generated .env file and update values as needed"
    echo "2. Run: docker-compose up -d"
    echo "3. Test: python test_memory_system.py"
    echo "4. Monitor: docker-compose logs -f"
    
    if [[ "$PRODUCTION_MODE" == "true" ]]; then
        echo -e "\n${YELLOW}⚠️  Production Notes:${NC}"
        echo "• Secure the generated passwords in a safe location"
        echo "• Configure SSL/TLS for production deployment"
        echo "• Set up proper backup procedures"
        echo "• Review security settings in docker-compose.yml"
    fi
    
    echo -e "\n${GREEN}✨ Environment setup complete!${NC}"
}

# ================================================================
# Script Execution
# ================================================================

# Ensure we're in the project root
cd "$PROJECT_ROOT"

# Run main function
main "$@"