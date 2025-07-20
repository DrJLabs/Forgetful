# OIDC Authentication Server for ChatGPT Actions

This server provides OAuth2/OIDC authentication endpoints that integrate with Google OAuth and issue JWTs for ChatGPT Actions to access the memory API.

## 🏗️ Architecture

```
ChatGPT Actions → mcp.drjlabs.com/.well-known/openid-configuration 
                ↓ (discovers auth endpoints)
                → oidc.drjlabs.com/auth/* (OAuth2 flow)
                ↓ (gets JWT token)
                → mcp.drjlabs.com/api/v1/memories/* (with Bearer token)
```

## 🚀 Quick Setup

### 1. Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit with your Google OAuth credentials
nano .env
```

Required variables:
```env
GOOGLE_CLIENT_ID=your_google_oauth_client_id
GOOGLE_CLIENT_SECRET=your_google_oauth_client_secret
GOOGLE_REDIRECT_URI=https://oidc.drjlabs.com/auth/callback
JWT_SECRET=your_secure_jwt_secret_here
```

### 2. Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project or select existing
3. Enable "Google+ API" 
4. Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client IDs"
5. Set authorized redirect URI: `https://oidc.drjlabs.com/auth/callback`
6. Copy Client ID and Secret to `.env` file

### 3. Deploy OIDC Server

```bash
# Build and run
docker-compose up -d

# Check health
curl http://localhost:8766/health
```

### 4. Configure Cloudflare DNS

Point `oidc.drjlabs.com` to your server and add bypass rules:

**Bypass Rules (no authentication required):**
```
oidc.drjlabs.com/auth/*
oidc.drjlabs.com/health
```

### 5. ChatGPT Action Configuration

In ChatGPT Custom Action setup:

**Server URL:** `https://mcp.drjlabs.com/mcp/sse`

**Authentication:**
- Type: OAuth2
- Client ID: (from ChatGPT - they provide this)
- Authorization URL: `https://oidc.drjlabs.com/auth/authorize`
- Token URL: `https://oidc.drjlabs.com/auth/token`
- Scope: `openid profile email`

## 📋 API Endpoints

### OIDC Endpoints (oidc.drjlabs.com)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/authorize` | GET | OAuth2 authorization (redirects to Google) |
| `/auth/callback` | GET | Google OAuth callback handler |
| `/auth/token` | POST | Exchange code for JWT token |
| `/auth/userinfo` | GET | Get user info from JWT |
| `/auth/jwks` | GET | JSON Web Key Set for JWT verification |
| `/health` | GET | Health check |

### Discovery Endpoint (mcp.drjlabs.com)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/.well-known/openid-configuration` | GET | OIDC discovery (points to oidc.drjlabs.com) |

## 🔄 Authentication Flow

1. **ChatGPT Discovery:** 
   - `GET mcp.drjlabs.com/.well-known/openid-configuration`
   - Returns OIDC config pointing to `oidc.drjlabs.com`

2. **User Authorization:**
   - ChatGPT redirects user to `oidc.drjlabs.com/auth/authorize`
   - Server redirects to Google OAuth
   - User grants permission
   - Google redirects back to `/auth/callback`

3. **Token Exchange:**
   - ChatGPT calls `oidc.drjlabs.com/auth/token` with authorization code
   - Server returns JWT access token

4. **API Access:**
   - ChatGPT includes JWT in `Authorization: Bearer <token>` header
   - MCP server validates JWT and allows access to memory operations

## 🔒 Security Features

- **JWT Tokens:** Short-lived (15 minutes) with user identity
- **Google OAuth Integration:** Leverages existing Google authentication
- **Scope Validation:** Ensures proper permissions
- **CORS Protection:** Restricts origins to ChatGPT domains
- **Token Validation:** MCP server validates JWT signatures

## 🚨 Troubleshooting

### Common Issues

1. **"Invalid redirect_uri" from Google:**
   - Verify `GOOGLE_REDIRECT_URI` matches exactly in Google Console
   - Ensure using `https://` not `http://`

2. **"Invalid authorization code":**
   - Check JWT_SECRET matches between OIDC server and MCP server
   - Verify token hasn't expired (15 minutes)

3. **CORS errors:**
   - Ensure ChatGPT domains are in CORS allowlist
   - Check for typos in domain names

### Debug Logging

```bash
# Check OIDC server logs
docker-compose logs -f oidc-server

# Test endpoints manually
curl -v https://oidc.drjlabs.com/health
curl -v https://mcp.drjlabs.com/.well-known/openid_configuration
```

## 🔧 Production Considerations

1. **Use Redis for token storage** instead of in-memory
2. **Implement proper RSA keys** for JWT signing (not HMAC)
3. **Add rate limiting** on auth endpoints
4. **Monitor token usage** and implement refresh tokens
5. **Use environment-specific secrets** (not hardcoded)
6. **Add comprehensive logging** and monitoring

## 📚 API Documentation

The server automatically generates OpenAPI documentation:
- OIDC Server: `http://localhost:8766/docs`
- MCP Server: `http://localhost:8765/docs`

## 🤝 Integration with Existing Systems

This solution maintains full backward compatibility:
- ✅ Existing Cursor/MCP usage unchanged
- ✅ API endpoints remain the same
- ✅ No breaking changes to current functionality
- ✅ Optional authentication (graceful fallback) 