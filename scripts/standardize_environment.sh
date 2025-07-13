#!/bin/bash
# ================================================================
# mem0-stack Environment Configuration Standardization Script
# ================================================================
#
# This script helps standardize environment configuration across
# all mem0-stack services including development, testing, and production.
#
# Features:
# - Environment detection and validation
# - Service-specific configuration generation
# - Docker compose configuration validation
# - CI/CD environment setup
# - Configuration migration assistance
#
# Usage:
#   ./scripts/standardize_environment.sh [options]
#
# Options:
#   --setup           Set up standardized environment
#   --validate        Validate current configuration
#   --migrate         Migrate from old configuration
#   --generate-ci     Generate CI environment variables
#   --test            Test configuration with services
#   --help            Show this help message

set -euo pipefail

# ================================================================
# Configuration and Constants
# ================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_TEMPLATE="${PROJECT_ROOT}/.env.template"
ENV_FILE="${PROJECT_ROOT}/.env"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Default values
SETUP_MODE=false
VALIDATE_MODE=false
MIGRATE_MODE=false
GENERATE_CI_MODE=false
TEST_MODE=false
FORCE_MODE=false

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
    echo "$(printf '%.0s─' {1..60})"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Generate secure password
generate_password() {
    local length=${1:-16}
    openssl rand -base64 $((length * 3 / 4)) | tr -d "=+/" | cut -c1-${length}
}

# Parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --setup)
                SETUP_MODE=true
                shift
                ;;
            --validate)
                VALIDATE_MODE=true
                shift
                ;;
            --migrate)
                MIGRATE_MODE=true
                shift
                ;;
            --generate-ci)
                GENERATE_CI_MODE=true
                shift
                ;;
            --test)
                TEST_MODE=true
                shift
                ;;
            --force)
                FORCE_MODE=true
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown argument: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# Show help message
show_help() {
    cat << EOF
${CYAN}mem0-stack Environment Configuration Standardization Script${NC}

${YELLOW}Usage:${NC}
  $0 [options]

${YELLOW}Options:${NC}
  --setup           Set up standardized environment configuration
  --validate        Validate current configuration against standards
  --migrate         Migrate from old configuration format
  --generate-ci     Generate CI environment variables
  --test            Test configuration with services
  --force           Force operations (skip confirmations)
  --help, -h        Show this help message

${YELLOW}Examples:${NC}
  $0 --setup                    # Set up new standardized environment
  $0 --validate                 # Validate current configuration
  $0 --migrate --force          # Migrate from old format
  $0 --generate-ci              # Generate CI environment variables
  $0 --test                     # Test configuration with services
  $0 --setup --validate --test  # Full setup and validation

${YELLOW}Environment Variables:${NC}
  ENVIRONMENT_TYPE              # Override environment type (dev/test/prod)
  SKIP_DOCKER_VALIDATION        # Skip Docker configuration validation
  SKIP_SERVICE_VALIDATION       # Skip service-specific validation

${YELLOW}Configuration Files:${NC}
  .env.template                 # Main environment template
  .env                          # Main environment file
  openmemory/api/.env.example   # API service template
  openmemory/ui/.env.example    # UI service template
  docker-compose.yml            # Docker configuration

EOF
}

# ================================================================
# Configuration Setup Functions
# ================================================================

setup_standardized_environment() {
    log_section "Setting Up Standardized Environment Configuration"

    # Check if .env already exists
    if [[ -f "$ENV_FILE" ]] && [[ "$FORCE_MODE" != "true" ]]; then
        log_warning "Environment file already exists: $ENV_FILE"
        read -p "Do you want to overwrite it? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Skipping environment setup"
            return 0
        fi
    fi

    # Copy template to .env
    if [[ -f "$ENV_TEMPLATE" ]]; then
        cp "$ENV_TEMPLATE" "$ENV_FILE"
        log_success "Created .env file from template"
    else
        log_error "Template file not found: $ENV_TEMPLATE"
        return 1
    fi

    # Collect configuration values
    collect_configuration_values

    # Generate service-specific configurations
    generate_service_configurations

    # Validate the setup
    validate_environment_configuration

    log_success "Standardized environment setup completed"
}

collect_configuration_values() {
    log_section "Collecting Configuration Values"

    # Environment type
    local env_type="${ENVIRONMENT_TYPE:-development}"
    
    # Generate secure defaults
    local db_user="drj"
    local db_password=$(generate_password 16)
    local neo4j_password=$(generate_password 16)
    local app_user_id="drj"
    local openai_key="sk-proj-your-openai-api-key-here"

    # Interactive collection if not in force mode
    if [[ "$FORCE_MODE" != "true" ]]; then
        echo -e "\n${CYAN}📝 Configuration Setup${NC}"
        echo "Please provide the following configuration values:"
        echo "(Press Enter to use generated defaults)"
        echo

        read -p "Environment type (development/test/production) [$env_type]: " input_env_type
        env_type="${input_env_type:-$env_type}"

        read -p "Database username [$db_user]: " input_db_user
        db_user="${input_db_user:-$db_user}"

        read -p "Database password [$db_password]: " input_db_password
        db_password="${input_db_password:-$db_password}"

        read -p "Neo4j password [$neo4j_password]: " input_neo4j_password
        neo4j_password="${input_neo4j_password:-$neo4j_password}"

        read -p "OpenAI API key [$openai_key]: " input_openai_key
        openai_key="${input_openai_key:-$openai_key}"

        read -p "Application user ID [$app_user_id]: " input_app_user_id
        app_user_id="${input_app_user_id:-$app_user_id}"
    fi

    # Apply values to .env file
    apply_configuration_values "$env_type" "$db_user" "$db_password" "$neo4j_password" "$openai_key" "$app_user_id"

    log_success "Configuration values collected and applied"
}

apply_configuration_values() {
    local env_type="$1"
    local db_user="$2"
    local db_password="$3"
    local neo4j_password="$4"
    local openai_key="$5"
    local app_user_id="$6"

    log_info "Applying configuration values to .env file"

    # Environment-specific settings
    local debug_mode="true"
    local log_level="INFO"
    
    case "$env_type" in
        "production")
            debug_mode="false"
            log_level="WARNING"
            ;;
        "test")
            debug_mode="false"
            log_level="INFO"
            ;;
        *)
            debug_mode="true"
            log_level="DEBUG"
            ;;
    esac

    # Apply replacements
    sed -i.bak \
        -e "s/APP_ENVIRONMENT=development/APP_ENVIRONMENT=$env_type/g" \
        -e "s/APP_DEBUG=true/APP_DEBUG=$debug_mode/g" \
        -e "s/APP_LOG_LEVEL=INFO/APP_LOG_LEVEL=$log_level/g" \
        -e "s/APP_USER_ID=drj/APP_USER_ID=$app_user_id/g" \
        -e "s/DATABASE_USER=your_username_here/DATABASE_USER=$db_user/g" \
        -e "s/DATABASE_PASSWORD=your_secure_password_here/DATABASE_PASSWORD=$db_password/g" \
        -e "s/NEO4J_PASSWORD=your_neo4j_password_here/NEO4J_PASSWORD=$neo4j_password/g" \
        -e "s/OPENAI_API_KEY=sk-proj-your-openai-api-key-here/OPENAI_API_KEY=$openai_key/g" \
        "$ENV_FILE"

    # Remove backup file
    rm -f "${ENV_FILE}.bak"

    log_success "Configuration values applied successfully"
}

generate_service_configurations() {
    log_section "Generating Service-Specific Configurations"

    # Create OpenMemory API .env file
    generate_api_env_file

    # Create OpenMemory UI .env file
    generate_ui_env_file

    log_success "Service-specific configurations generated"
}

generate_api_env_file() {
    local api_env_file="${PROJECT_ROOT}/openmemory/api/.env"
    local api_env_example="${PROJECT_ROOT}/openmemory/api/.env.example"

    if [[ -f "$api_env_example" ]]; then
        cp "$api_env_example" "$api_env_file"
        
        # Source main .env file to get variables
        if [[ -f "$ENV_FILE" ]]; then
            source "$ENV_FILE"
            
            # Apply values from main .env
            sed -i.bak \
                -e "s/DATABASE_USER=your_username_here/DATABASE_USER=$DATABASE_USER/g" \
                -e "s/DATABASE_PASSWORD=your_secure_password_here/DATABASE_PASSWORD=$DATABASE_PASSWORD/g" \
                -e "s/NEO4J_PASSWORD=your_neo4j_password_here/NEO4J_PASSWORD=$NEO4J_PASSWORD/g" \
                -e "s/OPENAI_API_KEY=sk-proj-your-openai-api-key-here/OPENAI_API_KEY=$OPENAI_API_KEY/g" \
                -e "s/APP_USER_ID=your_username_here/APP_USER_ID=$APP_USER_ID/g" \
                -e "s/APP_ENVIRONMENT=development/APP_ENVIRONMENT=$APP_ENVIRONMENT/g" \
                -e "s/APP_DEBUG=true/APP_DEBUG=$APP_DEBUG/g" \
                -e "s/APP_LOG_LEVEL=INFO/APP_LOG_LEVEL=$APP_LOG_LEVEL/g" \
                "$api_env_file"
                
            rm -f "${api_env_file}.bak"
        fi
        
        log_success "Generated OpenMemory API .env file"
    else
        log_warning "OpenMemory API .env.example not found"
    fi
}

generate_ui_env_file() {
    local ui_env_file="${PROJECT_ROOT}/openmemory/ui/.env"
    local ui_env_example="${PROJECT_ROOT}/openmemory/ui/.env.example"

    if [[ -f "$ui_env_example" ]]; then
        cp "$ui_env_example" "$ui_env_file"
        
        # Source main .env file to get variables
        if [[ -f "$ENV_FILE" ]]; then
            source "$ENV_FILE"
            
            # Apply values from main .env
            sed -i.bak \
                -e "s/NEXT_PUBLIC_USER_ID=your_username_here/NEXT_PUBLIC_USER_ID=$APP_USER_ID/g" \
                -e "s/APP_USER_ID=your_username_here/APP_USER_ID=$APP_USER_ID/g" \
                -e "s/APP_ENVIRONMENT=development/APP_ENVIRONMENT=$APP_ENVIRONMENT/g" \
                -e "s/APP_DEBUG=true/APP_DEBUG=$APP_DEBUG/g" \
                -e "s/APP_LOG_LEVEL=INFO/APP_LOG_LEVEL=$APP_LOG_LEVEL/g" \
                "$ui_env_file"
                
            rm -f "${ui_env_file}.bak"
        fi
        
        log_success "Generated OpenMemory UI .env file"
    else
        log_warning "OpenMemory UI .env.example not found"
    fi
}

# ================================================================
# Validation Functions
# ================================================================

validate_environment_configuration() {
    log_section "Validating Environment Configuration"

    local validation_passed=true

    # Validate main .env file
    if ! validate_main_env_file; then
        validation_passed=false
    fi

    # Validate service configurations
    if ! validate_service_configurations; then
        validation_passed=false
    fi

    # Validate Docker compose configuration
    if [[ "${SKIP_DOCKER_VALIDATION:-false}" != "true" ]]; then
        if ! validate_docker_configuration; then
            validation_passed=false
        fi
    fi

    # Validate variable consistency
    if ! validate_variable_consistency; then
        validation_passed=false
    fi

    if [[ "$validation_passed" == "true" ]]; then
        log_success "Environment configuration validation passed"
        return 0
    else
        log_error "Environment configuration validation failed"
        return 1
    fi
}

validate_main_env_file() {
    log_info "Validating main .env file"

    if [[ ! -f "$ENV_FILE" ]]; then
        log_error "Main .env file not found: $ENV_FILE"
        return 1
    fi

    # Check required variables
    local required_vars=(
        "APP_ENVIRONMENT"
        "APP_USER_ID"
        "DATABASE_USER"
        "DATABASE_PASSWORD"
        "NEO4J_PASSWORD"
        "OPENAI_API_KEY"
    )

    local missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if ! grep -q "^${var}=" "$ENV_FILE"; then
            missing_vars+=("$var")
        fi
    done

    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        log_error "Missing required variables: ${missing_vars[*]}"
        return 1
    fi

    # Check for placeholder values
    local placeholder_vars=()
    
    if grep -q "your_username_here" "$ENV_FILE"; then
        placeholder_vars+=("DATABASE_USER or APP_USER_ID")
    fi
    
    if grep -q "your_secure_password_here" "$ENV_FILE"; then
        placeholder_vars+=("DATABASE_PASSWORD")
    fi
    
    if grep -q "your_neo4j_password_here" "$ENV_FILE"; then
        placeholder_vars+=("NEO4J_PASSWORD")
    fi
    
    if grep -q "sk-proj-your-openai-api-key-here" "$ENV_FILE"; then
        placeholder_vars+=("OPENAI_API_KEY")
    fi

    if [[ ${#placeholder_vars[@]} -gt 0 ]]; then
        log_warning "Placeholder values found: ${placeholder_vars[*]}"
        log_warning "Please update these values before using in production"
    fi

    log_success "Main .env file validation passed"
    return 0
}

validate_service_configurations() {
    log_info "Validating service configurations"

    # Check API configuration
    local api_env_file="${PROJECT_ROOT}/openmemory/api/.env"
    if [[ -f "$api_env_file" ]]; then
        if grep -q "your_username_here\|your_secure_password_here\|your_neo4j_password_here" "$api_env_file"; then
            log_warning "OpenMemory API .env file contains placeholder values"
        else
            log_success "OpenMemory API .env file validated"
        fi
    else
        log_warning "OpenMemory API .env file not found"
    fi

    # Check UI configuration
    local ui_env_file="${PROJECT_ROOT}/openmemory/ui/.env"
    if [[ -f "$ui_env_file" ]]; then
        if grep -q "your_username_here" "$ui_env_file"; then
            log_warning "OpenMemory UI .env file contains placeholder values"
        else
            log_success "OpenMemory UI .env file validated"
        fi
    else
        log_warning "OpenMemory UI .env file not found"
    fi

    return 0
}

validate_docker_configuration() {
    log_info "Validating Docker configuration"

    if ! command_exists docker; then
        log_warning "Docker not found, skipping Docker validation"
        return 0
    fi

    # Test docker-compose config
    cd "$PROJECT_ROOT"
    if docker compose config >/dev/null 2>&1; then
        log_success "Docker Compose configuration is valid"
    else
        log_error "Docker Compose configuration has errors"
        return 1
    fi

    return 0
}

validate_variable_consistency() {
    log_info "Validating variable consistency across services"

    # Check if main .env file exists
    if [[ ! -f "$ENV_FILE" ]]; then
        log_error "Main .env file not found"
        return 1
    fi

    # Source main .env file
    source "$ENV_FILE"

    # Check API .env file consistency
    local api_env_file="${PROJECT_ROOT}/openmemory/api/.env"
    if [[ -f "$api_env_file" ]]; then
        if ! grep -q "APP_USER_ID=$APP_USER_ID" "$api_env_file"; then
            log_warning "APP_USER_ID mismatch in API .env file"
        fi
    fi

    # Check UI .env file consistency
    local ui_env_file="${PROJECT_ROOT}/openmemory/ui/.env"
    if [[ -f "$ui_env_file" ]]; then
        if ! grep -q "APP_USER_ID=$APP_USER_ID" "$ui_env_file"; then
            log_warning "APP_USER_ID mismatch in UI .env file"
        fi
    fi

    log_success "Variable consistency validation completed"
    return 0
}

# ================================================================
# Migration Functions
# ================================================================

migrate_from_old_configuration() {
    log_section "Migrating from Old Configuration Format"

    # Backup existing configuration
    backup_existing_configuration

    # Migrate main .env file
    migrate_main_env_file

    # Migrate service configurations
    migrate_service_configurations

    # Validate migrated configuration
    validate_environment_configuration

    log_success "Configuration migration completed"
}

backup_existing_configuration() {
    log_info "Creating backup of existing configuration"

    local backup_dir="${PROJECT_ROOT}/config_backup_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"

    # Backup main .env file
    if [[ -f "$ENV_FILE" ]]; then
        cp "$ENV_FILE" "$backup_dir/.env"
    fi

    # Backup service .env files
    if [[ -f "${PROJECT_ROOT}/openmemory/api/.env" ]]; then
        cp "${PROJECT_ROOT}/openmemory/api/.env" "$backup_dir/api.env"
    fi

    if [[ -f "${PROJECT_ROOT}/openmemory/ui/.env" ]]; then
        cp "${PROJECT_ROOT}/openmemory/ui/.env" "$backup_dir/ui.env"
    fi

    log_success "Configuration backup created: $backup_dir"
}

migrate_main_env_file() {
    log_info "Migrating main .env file"

    if [[ ! -f "$ENV_FILE" ]]; then
        log_info "No existing .env file found, creating new one"
        setup_standardized_environment
        return 0
    fi

    # Create temporary file for migration
    local temp_file=$(mktemp)
    
    # Copy template as base
    cp "$ENV_TEMPLATE" "$temp_file"

    # Migrate existing values
    source "$ENV_FILE"

    # Apply existing values to new template
    sed -i.bak \
        -e "s/APP_USER_ID=drj/APP_USER_ID=${USER:-${APP_USER_ID:-drj}}/g" \
        -e "s/DATABASE_USER=your_username_here/DATABASE_USER=${POSTGRES_USER:-${DATABASE_USER:-drj}}/g" \
        -e "s/DATABASE_PASSWORD=your_secure_password_here/DATABASE_PASSWORD=${POSTGRES_PASSWORD:-${DATABASE_PASSWORD:-}}/g" \
        -e "s/NEO4J_PASSWORD=your_neo4j_password_here/NEO4J_PASSWORD=${NEO4J_PASSWORD:-}/g" \
        -e "s/OPENAI_API_KEY=sk-proj-your-openai-api-key-here/OPENAI_API_KEY=${OPENAI_API_KEY:-${API_KEY:-}}/g" \
        "$temp_file"

    # Replace original with migrated version
    mv "$temp_file" "$ENV_FILE"
    rm -f "${temp_file}.bak"

    log_success "Main .env file migrated successfully"
}

migrate_service_configurations() {
    log_info "Migrating service configurations"

    # Regenerate service configurations based on migrated main .env
    generate_service_configurations

    log_success "Service configurations migrated successfully"
}

# ================================================================
# CI/CD Functions
# ================================================================

generate_ci_environment_variables() {
    log_section "Generating CI/CD Environment Variables"

    local ci_env_file="${PROJECT_ROOT}/ci_environment.env"

    cat > "$ci_env_file" << EOF
# CI/CD Environment Variables
# Generated by standardize_environment.sh

# Environment Configuration
APP_ENVIRONMENT=test
APP_DEBUG=false
APP_LOG_LEVEL=INFO
APP_USER_ID=test_user

# Database Configuration
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=test_db
DATABASE_USER=postgres
DATABASE_PASSWORD=testpass
DATABASE_URL=postgresql://postgres:testpass@localhost:5432/test_db

# Neo4j Configuration
NEO4J_HOST=localhost
NEO4J_PORT=7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=testpass
NEO4J_URI=bolt://localhost:7687
NEO4J_AUTH=neo4j/testpass

# OpenAI Configuration
OPENAI_API_KEY=sk-test-key-for-mocking-only
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Testing Configuration
TESTING=true
CI=true
GITHUB_ACTIONS=true
COVERAGE_THRESHOLD=80

# Legacy Variables (for backward compatibility)
POSTGRES_HOST=localhost
POSTGRES_DB=test_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=testpass
USER=test_user
API_KEY=sk-test-key-for-mocking-only

# CI-specific Configuration
PYTHONPATH=\${PWD}:\${PWD}/openmemory/api
CI_DATABASE_URL=postgresql://postgres:testpass@localhost:5432/test_db
CI_NEO4J_URI=bolt://localhost:7687
CI_COVERAGE_THRESHOLD=80
EOF

    log_success "CI environment variables generated: $ci_env_file"

    # Generate GitHub Actions environment section
    generate_github_actions_env_section

    log_success "CI/CD environment variables generation completed"
}

generate_github_actions_env_section() {
    local github_env_file="${PROJECT_ROOT}/github_actions_env.yml"

    cat > "$github_env_file" << EOF
# GitHub Actions Environment Section
# Copy this to your workflow files

env:
  # Environment Configuration
  APP_ENVIRONMENT: test
  APP_DEBUG: false
  APP_LOG_LEVEL: INFO
  APP_USER_ID: test_user
  
  # Database Configuration
  DATABASE_HOST: localhost
  DATABASE_PORT: 5432
  DATABASE_NAME: test_db
  DATABASE_USER: postgres
  DATABASE_PASSWORD: testpass
  DATABASE_URL: postgresql://postgres:testpass@localhost:5432/test_db
  
  # Neo4j Configuration
  NEO4J_HOST: localhost
  NEO4J_PORT: 7687
  NEO4J_USERNAME: neo4j
  NEO4J_PASSWORD: testpass
  NEO4J_URI: bolt://localhost:7687
  NEO4J_AUTH: neo4j/testpass
  
  # OpenAI Configuration
  OPENAI_API_KEY: sk-test-key-for-mocking-only
  OPENAI_MODEL: gpt-4o-mini
  OPENAI_EMBEDDING_MODEL: text-embedding-3-small
  
  # Testing Configuration
  TESTING: true
  CI: true
  GITHUB_ACTIONS: true
  COVERAGE_THRESHOLD: 80
  
  # Legacy Variables (for backward compatibility)
  POSTGRES_HOST: localhost
  POSTGRES_DB: test_db
  POSTGRES_USER: postgres
  POSTGRES_PASSWORD: testpass
  USER: test_user
  API_KEY: sk-test-key-for-mocking-only
  
  # CI-specific Configuration
  PYTHONPATH: \${PWD}:\${PWD}/openmemory/api
  CI_DATABASE_URL: postgresql://postgres:testpass@localhost:5432/test_db
  CI_NEO4J_URI: bolt://localhost:7687
  CI_COVERAGE_THRESHOLD: 80
EOF

    log_success "GitHub Actions environment section generated: $github_env_file"
}

# ================================================================
# Testing Functions
# ================================================================

test_configuration_with_services() {
    log_section "Testing Configuration with Services"

    # Test Docker Compose configuration
    test_docker_compose_config

    # Test database connections
    test_database_connections

    # Test environment variable resolution
    test_environment_variables

    log_success "Configuration testing completed"
}

test_docker_compose_config() {
    log_info "Testing Docker Compose configuration"

    if ! command_exists docker; then
        log_warning "Docker not found, skipping Docker tests"
        return 0
    fi

    cd "$PROJECT_ROOT"

    # Test configuration validation
    if docker compose config >/dev/null 2>&1; then
        log_success "Docker Compose configuration is valid"
    else
        log_error "Docker Compose configuration validation failed"
        return 1
    fi

    # Test service definitions
    local services=(postgres neo4j mem0 openmemory-mcp openmemory-ui)
    for service in "${services[@]}"; do
        if docker compose config --services | grep -q "^${service}$"; then
            log_success "Service '$service' is properly configured"
        else
            log_warning "Service '$service' not found in configuration"
        fi
    done

    return 0
}

test_database_connections() {
    log_info "Testing database connection configuration"

    if [[ ! -f "$ENV_FILE" ]]; then
        log_error "Environment file not found"
        return 1
    fi

    # Source environment variables
    source "$ENV_FILE"

    # Test DATABASE_URL construction
    local expected_url="postgresql://${DATABASE_USER}:${DATABASE_PASSWORD}@${DATABASE_HOST}:${DATABASE_PORT}/${DATABASE_NAME}"
    
    if [[ "$DATABASE_URL" == "$expected_url" ]]; then
        log_success "DATABASE_URL is correctly constructed"
    else
        log_warning "DATABASE_URL construction mismatch"
        log_info "Expected: $expected_url"
        log_info "Actual: $DATABASE_URL"
    fi

    # Test Neo4j URI construction
    local expected_neo4j_uri="bolt://${NEO4J_HOST}:${NEO4J_PORT}"
    
    if [[ "$NEO4J_URI" == "$expected_neo4j_uri" ]]; then
        log_success "NEO4J_URI is correctly constructed"
    else
        log_warning "NEO4J_URI construction mismatch"
        log_info "Expected: $expected_neo4j_uri"
        log_info "Actual: $NEO4J_URI"
    fi

    return 0
}

test_environment_variables() {
    log_info "Testing environment variable resolution"

    if [[ ! -f "$ENV_FILE" ]]; then
        log_error "Environment file not found"
        return 1
    fi

    # Source environment variables
    source "$ENV_FILE"

    # Test required variables
    local required_vars=(
        "APP_ENVIRONMENT"
        "APP_USER_ID"
        "DATABASE_USER"
        "DATABASE_PASSWORD"
        "NEO4J_PASSWORD"
        "OPENAI_API_KEY"
    )

    for var in "${required_vars[@]}"; do
        if [[ -n "${!var:-}" ]]; then
            log_success "Variable $var is set"
        else
            log_error "Variable $var is not set or empty"
        fi
    done

    return 0
}

# ================================================================
# Main Function
# ================================================================

main() {
    log_section "mem0-stack Environment Configuration Standardization"

    # Parse command line arguments
    parse_arguments "$@"

    # If no modes specified, show help
    if [[ "$SETUP_MODE" == "false" && "$VALIDATE_MODE" == "false" && "$MIGRATE_MODE" == "false" && "$GENERATE_CI_MODE" == "false" && "$TEST_MODE" == "false" ]]; then
        show_help
        exit 0
    fi

    # Change to project root
    cd "$PROJECT_ROOT"

    # Execute requested operations
    if [[ "$SETUP_MODE" == "true" ]]; then
        setup_standardized_environment
    fi

    if [[ "$MIGRATE_MODE" == "true" ]]; then
        migrate_from_old_configuration
    fi

    if [[ "$VALIDATE_MODE" == "true" ]]; then
        validate_environment_configuration
    fi

    if [[ "$GENERATE_CI_MODE" == "true" ]]; then
        generate_ci_environment_variables
    fi

    if [[ "$TEST_MODE" == "true" ]]; then
        test_configuration_with_services
    fi

    log_success "Environment configuration standardization completed successfully"
}

# Run main function with all arguments
main "$@"