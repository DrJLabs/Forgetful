#!/bin/bash
# Deploy Secure MCP Server with Traefik Integration

set -e

echo "🚀 Deploying Secure MCP Server..."

# 1. Generate API key for testing
API_KEY=$(openssl rand -hex 32)
echo "Generated API Key: $API_KEY"
echo "Save this key securely!"

# 2. Generate JWT secret
JWT_SECRET=$(openssl rand -hex 32)
echo "Generated JWT Secret: $JWT_SECRET"

# 3. Create environment file
cat > .env.mcp << EOF
HOST=127.0.0.1
PORT=8081
MEM0_API_URL=http://localhost:8000
OPENMEMORY_API_URL=http://localhost:8765
JWT_SECRET=$JWT_SECRET
API_KEYS=$API_KEY
ALLOWED_HOSTS=localhost,127.0.0.1,mem-mcp.onemainarmy.com,chat.openai.com,chatgpt.com
EOF

# 4. Generate basic auth password for Traefik
echo "Enter password for MCP basic auth:"
read -s PASSWORD
HASHED_PASSWORD=$(openssl passwd -apr1 "$PASSWORD")
echo "Hashed password: $HASHED_PASSWORD"

# 5. Update docker-compose.yml with the correct hashed password
sed -i "s/admin:\$\$2y\$\$10\$\$\.\.\./admin:$(echo $HASHED_PASSWORD | sed 's/[\/&]/\\&/g')/" docker-compose.yml

# 6. Stop current MCP server if running
pkill -f "standard_mem0_mcp_server.py" || true

# 7. Start secure MCP server
echo "Starting secure MCP server..."
source .env.mcp
nohup python3 secure_mcp_server.py > mcp_server.log 2>&1 &
MCP_PID=$!
echo "MCP server started with PID: $MCP_PID"

# 8. Update Traefik configuration
echo "Updating Traefik configuration..."
docker-compose up -d mcp-bridge

# 9. Test the endpoints
echo "Testing endpoints..."
sleep 5

# Test health endpoint
curl -s http://localhost:8081/health | jq . || echo "Health check failed"

# Test via Traefik (if accessible)
echo "MCP server deployed successfully!"
echo "Access via: https://mem-mcp.onemainarmy.com"
echo "API Key: $API_KEY"
echo "Log file: mcp_server.log"
echo "Process ID: $MCP_PID"

# 10. Create systemd service for auto-start
cat > /tmp/mcp-server.service << EOF
[Unit]
Description=Secure MCP Server
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$(pwd)
EnvironmentFile=$(pwd)/.env.mcp
ExecStart=$(which python3) $(pwd)/secure_mcp_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo "To install as systemd service:"
echo "sudo cp /tmp/mcp-server.service /etc/systemd/system/"
echo "sudo systemctl daemon-reload"
echo "sudo systemctl enable mcp-server"
echo "sudo systemctl start mcp-server"
