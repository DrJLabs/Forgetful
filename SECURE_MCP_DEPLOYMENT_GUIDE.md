# Secure MCP Server Deployment Guide

## Overview

This guide covers the deployment of a secure, internet-facing MCP (Model Context Protocol) server for your mem0 stack. The server will be accessible at `https://mem-mcp.onemainarmy.com` with API key authentication.

## 🔐 Security Features

- **API Key Authentication**: Secure token-based access
- **Rate Limiting**: Protection against abuse
- **Input Validation**: Prevents injection attacks
- **CORS Protection**: Restricts cross-origin requests
- **Security Headers**: XSS, clickjacking, and MIME-type protection
- **Localhost Binding**: Server only accessible through Cloudflare tunnel
- **Credential Protection**: Sensitive files excluded from git

## 📋 Prerequisites

1. **Running mem0 stack**:
   ```bash
   docker-compose up -d mem0 postgres-mem0 neo4j-mem0
   ```

2. **Python dependencies**:
   ```bash
   pip install aiohttp PyJWT fastapi slowapi python-multipart
   ```

3. **Cloudflare tunnel configured** for `mem-mcp.onemainarmy.com`
4. **ChatGPT integration ready** - CORS configured for `chat.openai.com`

## 🚀 Production Deployment

### Step 1: Run Security Tests and Deploy

```bash
./deploy_production_mcp.sh
```

This script will:
- ✅ Check prerequisites
- 🔑 Generate secure API keys
- 🔒 Run comprehensive security tests
- 🚀 Deploy to production (only if all tests pass)
- 📝 Create systemd service file

### Step 2: Verify Deployment

```bash
./test_production_deployment.py
```

This will test:
- Health endpoint
- Authentication
- Memory operations
- Search functionality

### Step 3: Install as System Service (Optional)

```bash
sudo cp /tmp/mcp-production.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable mcp-production
sudo systemctl start mcp-production
```

## 🔧 Configuration Files

### Environment Variables (`.env.mcp.production`)
```bash
HOST=127.0.0.1
PORT=8081
MEM0_API_URL=http://localhost:8000
OPENMEMORY_API_URL=http://localhost:8765
JWT_SECRET=<generated-secret>
API_KEYS=<generated-api-key>
ALLOWED_HOSTS=localhost,127.0.0.1,mem-mcp.onemainarmy.com
```

### Traefik Configuration (in `docker-compose.yml`)
```yaml
mcp-bridge:
  image: nginx:alpine
  labels:
    - 'traefik.http.routers.mcp-bridge.rule=Host(`mem-mcp.onemainarmy.com`)'
    - 'traefik.http.routers.mcp-bridge.middlewares=mcp-auth,mcp-ratelimit'
```

## 🧪 Security Testing

### Manual Security Test

```bash
./security_test_suite.py
```

Tests performed:
- 🔒 Authentication bypass attempts
- 🚦 Rate limiting protection
- 🛡️ Input validation
- 🌐 CORS policy enforcement
- 🔐 Security headers
- 🕵️ Information disclosure
- 🛡️ DoS protection
- 🔍 Credential exposure
- ✅ Valid functionality

### Test Results

Results are saved to `security_test_report.txt`. **DO NOT deploy** if any tests fail.

## 📡 External Access

### API Endpoints

- **Health Check**: `GET /health` (no auth required)
- **SSE Stream**: `GET /sse` (auth required)
- **Tool Calls**: `POST /tools/call` (auth required)
- **JWT Token**: `POST /auth/token` (for testing only)

### ChatGPT Integration

The server is configured to work with ChatGPT custom GPTs:

1. **Allowed origins**: `chat.openai.com` and `chatgpt.com`
2. **CORS headers**: Properly configured for browser requests
3. **API key auth**: Use bearer token authentication

#### Creating a Custom GPT

1. Go to ChatGPT and create a new GPT
2. In the configuration, add your MCP server URL: `https://mem-mcp.onemainarmy.com`
3. Configure authentication with your API key
4. Set up actions for memory operations (add, search, list)

### Example Usage

```bash
# Health check
curl https://mem-mcp.onemainarmy.com/health

# Add memory
curl -H "Authorization: Bearer YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     -X POST "https://mem-mcp.onemainarmy.com/tools/call" \
     -d '{"name": "add_memories", "arguments": {"text": "Hello from external agent"}}'

# Search memory
curl -H "Authorization: Bearer YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     -X POST "https://mem-mcp.onemainarmy.com/tools/call" \
     -d '{"name": "search_memory", "arguments": {"query": "external agent"}}'

# List memories
curl -H "Authorization: Bearer YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     -X POST "https://mem-mcp.onemainarmy.com/tools/call" \
     -d '{"name": "list_memories", "arguments": {}}'
```

## 🔑 API Key Management

### Production API Key
- Generated during deployment
- Saved to `mcp_production_api_key.txt` (secure permissions)
- **Store securely** - this key provides full access to your memory system

### API Key Format
- 64-character hexadecimal string
- Example: `a1b2c3d4e5f6789...`

### Using API Keys
```bash
# In headers
Authorization: Bearer YOUR_API_KEY

# In environment
export MCP_API_KEY="your-api-key-here"
```

## 📊 Monitoring

### Log Files
- **Production**: `mcp_server_production.log`
- **Test**: `mcp_server_test.log`

### Health Monitoring
```bash
# Check health
curl http://localhost:8081/health

# Monitor logs
tail -f mcp_server_production.log

# Check process
ps aux | grep secure_mcp_server
```

### System Service Status
```bash
# Check service status
sudo systemctl status mcp-production

# View logs
sudo journalctl -u mcp-production -f
```

## 🚨 Troubleshooting

### Common Issues

1. **Security tests fail**
   - Check mem0 backend is running
   - Verify Python dependencies installed
   - Check port 8081 is available

2. **Authentication errors**
   - Verify API key is correct
   - Check Authorization header format
   - Ensure HTTPS is used for external access

3. **CORS errors**
   - Check if origin is in allowed list
   - Verify domain configuration
   - Use HTTPS (not HTTP)

4. **Rate limiting**
   - Reduce request frequency
   - Check if hitting 60 requests/minute limit
   - Wait for rate limit to reset

### Debug Commands

```bash
# Check running processes
lsof -i :8081

# Test local connectivity
curl -v http://localhost:8081/health

# Check Traefik routing
docker logs traefik-container-name

# Verify environment
cat .env.mcp.production
```

## 🔄 Updates and Maintenance

### Updating the Server

1. Stop the current server:
   ```bash
   sudo systemctl stop mcp-production
   # or
   pkill -f secure_mcp_server.py
   ```

2. Update code and run tests:
   ```bash
   git pull
   ./security_test_suite.py
   ```

3. Restart the server:
   ```bash
   sudo systemctl start mcp-production
   # or
   ./deploy_production_mcp.sh
   ```

### Rotating API Keys

1. Generate new API key:
   ```bash
   openssl rand -hex 32
   ```

2. Update `.env.mcp.production`
3. Restart the server
4. Update external agents with new key

## 🛡️ Security Best Practices

1. **Never commit API keys** - already configured in `.gitignore`
2. **Rotate keys regularly** - monthly recommended
3. **Monitor logs** - watch for suspicious activity
4. **Use HTTPS only** - never send API keys over HTTP
5. **Limit API key scope** - one key per external agent
6. **Regular security testing** - run tests before updates

## 📝 File Structure

```
/home/drj/projects/mem0-stack/
├── secure_mcp_server.py           # Main secure server
├── security_test_suite.py         # Security tests
├── deploy_production_mcp.sh       # Deployment script
├── test_production_deployment.py  # Production test
├── nginx-mcp-proxy.conf           # Nginx proxy config
├── .env.mcp.production           # Production environment
├── mcp_production_api_key.txt    # API key (secure)
├── mcp_server_production.log     # Server logs
├── security_test_report.txt      # Test results
├── chatgpt_custom_gpt_config.json # OpenAPI schema for ChatGPT
└── CHATGPT_CUSTOM_GPT_SETUP.md   # ChatGPT integration guide
```

## 🎯 Next Steps

1. **Deploy to production**: Run `./deploy_production_mcp.sh`
2. **Verify deployment**: Run `./test_production_deployment.py`
3. **Configure external agents**: Use the generated API key
4. **Set up monitoring**: Configure log rotation and alerts
5. **Schedule testing**: Regular security test runs

## 📞 Support

For issues or questions:
- Check `security_test_report.txt` for test results
- Review `mcp_server_production.log` for server logs
- Run `./test_production_deployment.py` for diagnosis

---

🎉 **Your secure MCP server is now ready for production use!**
