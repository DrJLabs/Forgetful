#!/bin/bash
set -e

# Configure cloud environment for background agent testing
echo "🌩️ Configuring cloud environment: $1"

# Create cloud-specific environment configuration
cat > .env.background << EOF
# Background agent testing configuration
CLOUD_PROVIDER=$1
AGENT_TYPE=$2
BACKGROUND_TESTING=true
LONG_RUNNING_TESTS=true
TEST_DURATION_MINUTES=${TEST_DURATION_MINUTES}
BACKGROUND_AGENT_COUNT=${BACKGROUND_AGENT_COUNT}

# Extended timeouts for background testing
DATABASE_CONNECTION_TIMEOUT=300
AGENT_STARTUP_TIMEOUT=${AGENT_STARTUP_TIMEOUT}
HEALTH_CHECK_TIMEOUT=60

# Memory and performance configuration
MEMORY_OPTIMIZATION=true
PERFORMANCE_MONITORING=true
RESOURCE_MONITORING=true
EOF

echo "Environment configuration created:"
cat .env.background
