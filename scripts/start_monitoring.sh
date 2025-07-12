#!/bin/bash

# mem0-Stack Monitoring System Startup Script
# This script deploys the complete observability stack for mem0-stack

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
MONITORING_COMPOSE="$PROJECT_ROOT/docker-compose.monitoring.yml"
MAIN_COMPOSE="$PROJECT_ROOT/docker-compose.yml"

# Default settings
DEFAULT_WAIT_TIMEOUT=300
DEFAULT_HEALTH_CHECK_INTERVAL=10
DEFAULT_MAX_RETRIES=30

# Functions
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] ✅${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] ⚠️${NC} $1"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ❌${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi

    # Check Docker Compose
    if ! docker compose version &> /dev/null; then
        log_error "Docker Compose V2 is not available"
        exit 1
    fi

    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi

    # Check available disk space (minimum 10GB)
    AVAILABLE_SPACE=$(df "$PROJECT_ROOT" | awk 'NR==2 {print $4}')
    REQUIRED_SPACE=$((10 * 1024 * 1024)) # 10GB in KB

    if [ "$AVAILABLE_SPACE" -lt "$REQUIRED_SPACE" ]; then
        log_warning "Low disk space: $(($AVAILABLE_SPACE / 1024 / 1024))GB available, 10GB recommended"
    fi

    # Check if required files exist
    if [ ! -f "$MONITORING_COMPOSE" ]; then
        log_error "Monitoring docker-compose file not found: $MONITORING_COMPOSE"
        exit 1
    fi

    if [ ! -f "$MAIN_COMPOSE" ]; then
        log_error "Main docker-compose file not found: $MAIN_COMPOSE"
        exit 1
    fi

    log_success "Prerequisites check passed"
}

# Create required directories
create_directories() {
    log "Creating required directories..."

    local dirs=(
        "data/prometheus"
        "data/grafana"
        "data/alertmanager"
        "data/elasticsearch"
        "data/uptime-kuma"
        "logs/monitoring"
    )

    for dir in "${dirs[@]}"; do
        mkdir -p "$PROJECT_ROOT/$dir"
        log "Created directory: $dir"
    done

    # Set proper permissions for Grafana
    chmod 777 "$PROJECT_ROOT/data/grafana"

    # Set proper permissions for Elasticsearch
    if [ "$(id -u)" = "0" ]; then
        chown -R 1000:1000 "$PROJECT_ROOT/data/elasticsearch"
    else
        log_warning "Not running as root, Elasticsearch permissions may need adjustment"
    fi

    log_success "Directories created successfully"
}

# Start core services first
start_core_services() {
    log "Starting core mem0-stack services..."

    cd "$PROJECT_ROOT"

    # Start core services
    docker compose up -d mem0 postgres-mem0 neo4j-mem0 openmemory-mcp openmemory-ui

    log "Waiting for core services to be healthy..."
    wait_for_service_health "postgres-mem0" "pg_isready -U ${POSTGRES_USER:-drj} -d mem0"
    wait_for_service_health "neo4j-mem0" "wget -O /dev/null http://localhost:7474/"
    wait_for_service_health "mem0" "curl -f http://localhost:8000/health"
    wait_for_service_health "openmemory-mcp" "curl -f http://localhost:8765/health"
    wait_for_service_health "openmemory-ui" "curl -f http://localhost:3000/"

    log_success "Core services are healthy and running"
}

# Start monitoring stack
start_monitoring_stack() {
    log "Starting monitoring stack..."

    cd "$PROJECT_ROOT"

    # Start monitoring services in stages
    log "Starting system monitoring..."
    docker compose -f docker-compose.monitoring.yml up -d node-exporter postgres-exporter

    log "Starting metrics collection..."
    docker compose -f docker-compose.monitoring.yml up -d prometheus alertmanager

    log "Starting visualization..."
    docker compose -f docker-compose.monitoring.yml up -d grafana

    log "Starting logging stack..."
    docker compose -f docker-compose.monitoring.yml up -d elasticsearch
    sleep 30  # Wait for Elasticsearch to initialize
    docker compose -f docker-compose.monitoring.yml up -d logstash kibana filebeat

    log "Starting tracing..."
    docker compose -f docker-compose.monitoring.yml up -d jaeger

    log "Starting uptime monitoring..."
    docker compose -f docker-compose.monitoring.yml up -d uptime-kuma

    log_success "Monitoring stack deployment initiated"
}

# Wait for service health
wait_for_service_health() {
    local service_name=$1
    local health_command=$2
    local max_attempts=${3:-$DEFAULT_MAX_RETRIES}
    local interval=${4:-$DEFAULT_HEALTH_CHECK_INTERVAL}

    log "Waiting for $service_name to be healthy..."

    for ((i=1; i<=max_attempts; i++)); do
        if docker exec "$service_name" bash -c "$health_command" &> /dev/null; then
            log_success "$service_name is healthy (attempt $i/$max_attempts)"
            return 0
        fi

        if [ $i -eq $max_attempts ]; then
            log_error "$service_name failed to become healthy after $max_attempts attempts"
            return 1
        fi

        log "Attempt $i/$max_attempts: $service_name not ready, waiting ${interval}s..."
        sleep $interval
    done
}

# Wait for HTTP endpoint
wait_for_http_endpoint() {
    local service_name=$1
    local url=$2
    local max_attempts=${3:-$DEFAULT_MAX_RETRIES}
    local interval=${4:-$DEFAULT_HEALTH_CHECK_INTERVAL}

    log "Waiting for $service_name at $url..."

    for ((i=1; i<=max_attempts; i++)); do
        if curl -s -f "$url" &> /dev/null; then
            log_success "$service_name is responding (attempt $i/$max_attempts)"
            return 0
        fi

        if [ $i -eq $max_attempts ]; then
            log_error "$service_name at $url failed to respond after $max_attempts attempts"
            return 1
        fi

        log "Attempt $i/$max_attempts: $service_name not responding, waiting ${interval}s..."
        sleep $interval
    done
}

# Verify monitoring stack
verify_monitoring_stack() {
    log "Verifying monitoring stack health..."

    # Check Prometheus
    wait_for_http_endpoint "Prometheus" "http://localhost:9090/-/healthy"

    # Check Grafana
    wait_for_http_endpoint "Grafana" "http://localhost:3001/api/health"

    # Check Alertmanager
    wait_for_http_endpoint "Alertmanager" "http://localhost:9093/-/healthy"

    # Check Elasticsearch
    wait_for_http_endpoint "Elasticsearch" "http://localhost:9200/_cluster/health"

    # Check Kibana
    wait_for_http_endpoint "Kibana" "http://localhost:5601/api/status"

    # Check Jaeger
    wait_for_http_endpoint "Jaeger" "http://localhost:16686/"

    log_success "All monitoring services are healthy"
}

# Configure initial dashboards and data sources
configure_monitoring() {
    log "Configuring initial monitoring setup..."

    # Wait a bit more for Grafana to fully initialize
    sleep 30

    # Import system overview dashboard
    log "Importing system overview dashboard..."
    if [ -f "$PROJECT_ROOT/monitoring/grafana/dashboards/system-overview.json" ]; then
        curl -X POST \
            -H "Content-Type: application/json" \
            -d @"$PROJECT_ROOT/monitoring/grafana/dashboards/system-overview.json" \
            "http://admin:${GRAFANA_PASSWORD:-admin123}@localhost:3001/api/dashboards/db" \
            || log_warning "Failed to import system overview dashboard"
    fi

    # Create initial Kibana index patterns
    log "Creating Kibana index patterns..."
    sleep 10
    curl -X POST "http://localhost:5601/api/saved_objects/index-pattern/mem0-stack-logs" \
        -H "Content-Type: application/json" \
        -H "kbn-xsrf: true" \
        -d '{
            "attributes": {
                "title": "mem0-stack-logs-*",
                "timeFieldName": "@timestamp"
            }
        }' || log_warning "Failed to create Kibana index pattern"

    log_success "Initial monitoring configuration completed"
}

# Display access information
display_access_info() {
    log_success "🎉 mem0-Stack Observability System Deployed Successfully!"
    echo
    echo "================================================================================"
    echo "                              ACCESS INFORMATION"
    echo "================================================================================"
    echo
    echo "📊 MONITORING DASHBOARDS:"
    echo "  • Grafana:       http://localhost:3001"
    echo "    Login:         admin / ${GRAFANA_PASSWORD:-admin123}"
    echo "  • Prometheus:    http://localhost:9090"
    echo "  • Alertmanager:  http://localhost:9093"
    echo
    echo "📋 LOGGING & TRACING:"
    echo "  • Kibana:        http://localhost:5601"
    echo "  • Elasticsearch: http://localhost:9200"
    echo "  • Jaeger:        http://localhost:16686"
    echo
    echo "⏰ UPTIME MONITORING:"
    echo "  • Uptime Kuma:   http://localhost:3001"
    echo
    echo "🔧 CORE SERVICES:"
    echo "  • mem0 API:      http://localhost:8000"
    echo "  • OpenMemory:    http://localhost:8765"
    echo "  • OpenMemory UI: http://localhost:3000"
    echo
    echo "================================================================================"
    echo "                              NEXT STEPS"
    echo "================================================================================"
    echo
    echo "1. 📈 Open Grafana and explore the system overview dashboard"
    echo "2. 🔍 Configure Kibana index patterns for log analysis"
    echo "3. 🚨 Set up notification channels in Alertmanager"
    echo "4. 📊 Create custom dashboards for your specific needs"
    echo "5. 🔄 Monitor the system for a few minutes to see data flowing"
    echo
    echo "📚 For more information, see:"
    echo "  • docs/monitoring-implementation-plan.md"
    echo "  • docs/agent-assignments/agent-3-observability.md"
    echo
    echo "================================================================================"
}

# Cleanup function
cleanup() {
    if [ $? -ne 0 ]; then
        log_error "Deployment failed. Cleaning up..."
        docker compose -f docker-compose.monitoring.yml down -v || true
        docker compose down || true
    fi
}

# Main execution
main() {
    trap cleanup EXIT

    log "🚀 Starting mem0-Stack Observability System Deployment"
    echo "================================================================================"

    # Step 1: Prerequisites
    check_prerequisites

    # Step 2: Prepare environment
    create_directories

    # Step 3: Start core services
    start_core_services

    # Step 4: Start monitoring stack
    start_monitoring_stack

    # Step 5: Verify health
    verify_monitoring_stack

    # Step 6: Configure monitoring
    configure_monitoring

    # Step 7: Display access information
    display_access_info

    log_success "Deployment completed successfully! 🎉"
}

# Handle command line arguments
case "${1:-}" in
    "stop")
        log "Stopping monitoring stack..."
        docker compose -f docker-compose.monitoring.yml down
        log_success "Monitoring stack stopped"
        ;;
    "restart")
        log "Restarting monitoring stack..."
        docker compose -f docker-compose.monitoring.yml down
        sleep 5
        main
        ;;
    "status")
        log "Checking monitoring stack status..."
        docker compose -f docker-compose.monitoring.yml ps
        ;;
    "logs")
        service="${2:-}"
        if [ -n "$service" ]; then
            docker compose -f docker-compose.monitoring.yml logs -f "$service"
        else
            docker compose -f docker-compose.monitoring.yml logs -f
        fi
        ;;
    "help"|"-h"|"--help")
        echo "mem0-Stack Monitoring System Control Script"
        echo
        echo "Usage: $0 [COMMAND]"
        echo
        echo "Commands:"
        echo "  start     Start the monitoring stack (default)"
        echo "  stop      Stop the monitoring stack"
        echo "  restart   Restart the monitoring stack"
        echo "  status    Show service status"
        echo "  logs      Show logs (optionally for specific service)"
        echo "  help      Show this help message"
        echo
        echo "Examples:"
        echo "  $0                    # Start monitoring stack"
        echo "  $0 stop              # Stop monitoring stack"
        echo "  $0 logs prometheus   # Show Prometheus logs"
        ;;
    ""|"start")
        main
        ;;
    *)
        log_error "Unknown command: $1"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac