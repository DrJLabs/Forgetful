"""
OIDC Authentication Server for ChatGPT Integration

Provides OAuth2/OIDC endpoints that proxy to Google OAuth
and issue JWTs for ChatGPT Actions to use with the MCP server.
"""

import os
import secrets
import jwt
import httpx
import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Optional
from fastapi import FastAPI, Request, HTTPException, Depends, Response
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import base64

app = FastAPI(title="OIDC Auth Server", version="1.0.0")

# Environment variables
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
BASE_URL = os.getenv("OIDC_BASE_URL", "https://oidc.drjlabs.com")
JWT_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 30

# Generate RSA key pair for JWT signing (use external key management in production)
def load_or_generate_rsa_keypair():
    """
    Load RSA key pair from environment/file or generate new one
    Production: mount private key as Docker secret or env var
    Development: generate new key pair
    """
    # Try to load from environment or file (production)
    private_key_path = os.getenv("RSA_PRIVATE_KEY_PATH", "/run/secrets/rsa_private_key")
    private_key_pem = os.getenv("RSA_PRIVATE_KEY_PEM")

    if private_key_pem:
        # Load from environment variable
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode(),
            password=None
        )
        print("✅ Loaded RSA private key from environment")
        return private_key
    elif os.path.exists(private_key_path):
        # Load from mounted secret file
        with open(private_key_path, 'rb') as key_file:
            private_key = serialization.load_pem_private_key(
                key_file.read(),
                password=None
            )
        print(f"✅ Loaded RSA private key from {private_key_path}")
        return private_key
    else:
        # Development: generate new key pair
        print("⚠️ Generating new RSA key pair (development mode)")
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        return private_key

# RSA key pair for JWT signing
RSA_PRIVATE_KEY = load_or_generate_rsa_keypair()
RSA_PUBLIC_KEY = RSA_PRIVATE_KEY.public_key()
JWT_ALGORITHM = "RS256"
KEY_ID = os.getenv("JWT_KEY_ID", "key1")  # Key identifier for JWKS

# In-memory storage for demo (use Redis in production)
auth_codes = {}
access_tokens = {}
refresh_tokens = {}  # New: Storage for refresh tokens

# CORS for ChatGPT - tightened security
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://chat.openai.com",
        "https://chatgpt.com"
    ],
    allow_credentials=False,  # Bearer tokens don't need credentials
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

class TokenRequest(BaseModel):
    grant_type: str
    code: Optional[str] = None
    redirect_uri: Optional[str] = None
    client_id: Optional[str] = None
    code_verifier: Optional[str] = None  # PKCE verification
    refresh_token: Optional[str] = None  # For refresh token flow

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "oidc-auth-server"}

@app.get("/.well-known/openid-configuration")
async def openid_configuration():
    """
    OIDC Discovery endpoint - uses configurable base URL
    """
    return {
        "issuer": BASE_URL,
        "authorization_endpoint": f"{BASE_URL}/auth/authorize",
        "token_endpoint": f"{BASE_URL}/auth/token",
        "userinfo_endpoint": f"{BASE_URL}/auth/userinfo",
        "jwks_uri": f"{BASE_URL}/auth/jwks",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "scopes_supported": ["openid", "profile", "email"],
        "subject_types_supported": ["public"],
        "id_token_signing_alg_values_supported": ["RS256"],
        "token_endpoint_auth_methods_supported": ["client_secret_post", "client_secret_basic", "none"],
        "code_challenge_methods_supported": ["S256", "plain"]  # Advertise both supported methods
    }

@app.get("/auth/authorize")
async def authorize(
    request: Request,
    client_id: str,
    redirect_uri: str,
    response_type: str = "code",
    scope: str = "openid profile email",
    state: Optional[str] = None,
    code_challenge: Optional[str] = None,
    code_challenge_method: Optional[str] = None,
    resource: Optional[str] = None
):
    """
    OAuth2 Authorization endpoint
    Redirects to Google OAuth for authentication
    """
    if response_type != "code":
        raise HTTPException(400, "Only 'code' response_type supported")

    # PKCE validation (optional)
    code_challenge = request.query_params.get("code_challenge")
    code_challenge_method = request.query_params.get("code_challenge_method")

    # RFC 7636 edge case: code_challenge_method without code_challenge should be rejected
    if code_challenge_method and not code_challenge:
        raise HTTPException(
            status_code=400,
            detail="code_challenge required when code_challenge_method is supplied"
        )

    if code_challenge:
        # Default to S256 if method not specified (recommended by RFC 7636)
        if not code_challenge_method:
            code_challenge_method = "S256"

        # Validate code_challenge_method
        if code_challenge_method not in ["S256", "plain"]:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported code_challenge_method: {code_challenge_method}. Supported methods: S256, plain"
            )

    # Store request info for later callback
    auth_state = secrets.token_urlsafe(32)
    auth_codes[auth_state] = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "original_state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
        "resource": resource,
        "created_at": datetime.utcnow()
    }

    # Build Google OAuth URL
    google_oauth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={os.getenv('GOOGLE_REDIRECT_URI', 'https://oidc.drjlabs.com/auth/callback')}"
        f"&response_type=code"
        f"&scope=openid email profile"
        f"&state={auth_state}"
    )

    return RedirectResponse(google_oauth_url)

@app.get("/auth/callback")
async def google_callback(code: str, state: str):
    """
    Handle Google OAuth callback
    Exchange Google code for tokens and redirect back to ChatGPT
    """
    # Retrieve original request
    if state not in auth_codes:
        raise HTTPException(400, "Invalid state parameter")

    original_request = auth_codes[state]

    # Exchange Google code for tokens
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": os.getenv('GOOGLE_REDIRECT_URI', 'https://oidc.drjlabs.com/auth/callback')
            }
        )

        if token_response.status_code != 200:
            raise HTTPException(400, "Failed to exchange Google code")

        google_tokens = token_response.json()

        # Get user info from Google
        userinfo_response = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {google_tokens['access_token']}"}
        )

        if userinfo_response.status_code != 200:
            raise HTTPException(400, "Failed to get user info")

        user_info = userinfo_response.json()

    # Generate our authorization code for ChatGPT
    chatgpt_code = secrets.token_urlsafe(32)
    auth_codes[chatgpt_code] = {
        "user_info": user_info,
        "google_tokens": google_tokens,
        "original_request": original_request,
        "created_at": datetime.utcnow()
    }

    # Clean up state
    del auth_codes[state]

    # Redirect back to ChatGPT with our code
    redirect_url = f"{original_request['redirect_uri']}?code={chatgpt_code}"
    if original_request.get('original_state'):
        redirect_url += f"&state={original_request['original_state']}"

    return RedirectResponse(redirect_url)

@app.post("/auth/token")
async def token_endpoint(token_request: TokenRequest):
    """
    OAuth2 Token endpoint
    Exchange authorization code or refresh token for JWT access token
    """
    if token_request.grant_type == "authorization_code":
        return await handle_authorization_code_grant(token_request)
    elif token_request.grant_type == "refresh_token":
        return await handle_refresh_token_grant(token_request)
    else:
        return JSONResponse(
            status_code=400,
            content={
                "error": "unsupported_grant_type",
                "error_description": "Only 'authorization_code' and 'refresh_token' grant_types are supported"
            }
        )

async def handle_authorization_code_grant(token_request: TokenRequest):
    """Handle authorization code grant flow"""

    if not token_request.code or token_request.code not in auth_codes:
        return JSONResponse(
            status_code=400,
            content={
                "error": "invalid_grant",
                "error_description": "The provided authorization code is invalid"
            }
        )

    code_data = auth_codes[token_request.code]
    user_info = code_data["user_info"]

    # PKCE verification (if code_challenge was provided)
    original_request = code_data["original_request"]
    if original_request.get("code_challenge"):
        if not token_request.code_verifier:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "invalid_grant",
                    "error_description": "Code verifier is required for PKCE"
                }
            )

        # Validate code_verifier length per RFC 7636 §4.1 (43-128 characters)
        if len(token_request.code_verifier) < 43 or len(token_request.code_verifier) > 128:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "invalid_grant",
                    "error_description": "Code verifier must be between 43 and 128 characters"
                }
            )

        # Verify code_challenge
        challenge_method = original_request.get("code_challenge_method", "S256")
        if challenge_method == "S256":
            # SHA256 hash of code_verifier, base64url encoded
            verifier_hash = hashlib.sha256(token_request.code_verifier.encode()).digest()
            computed_challenge = base64.urlsafe_b64encode(verifier_hash).decode().rstrip('=')
        elif challenge_method == "plain":
            computed_challenge = token_request.code_verifier
        else:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "invalid_grant",
                    "error_description": f"Unsupported code_challenge_method: {challenge_method}"
                }
            )

        if computed_challenge != original_request["code_challenge"]:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "invalid_grant",
                    "error_description": "Code verifier does not match code challenge"
                }
            )

    # Create JWT token with RSA signing
    now = datetime.utcnow()

    # Validate audience (client_id) and bind to original authorization request
    if not token_request.client_id:
        return JSONResponse(
            status_code=400,
            content={
                "error": "invalid_request",
                "error_description": "client_id is required"
            }
        )

    # Bind client_id: prevent client-ID substitution attacks per RFC best practices
    if token_request.client_id != original_request["client_id"]:
        return JSONResponse(
            status_code=400,
            content={
                "error": "invalid_grant",
                "error_description": "Client ID does not match original authorization request"
            }
        )

    payload = {
        "sub": user_info["sub"],  # Google user ID
        "email": user_info["email"],
        "name": user_info["name"],
        "picture": user_info.get("picture"),
        "iss": BASE_URL,
        "aud": code_data["original_request"].get("resource") or "https://api.openmemory.io",
        "iat": now,
        "exp": now + timedelta(minutes=JWT_EXPIRE_MINUTES),
        "scope": code_data["original_request"]["scope"]
    }

    # Sign with RSA private key
    private_key_pem = RSA_PRIVATE_KEY.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

    access_token = jwt.encode(
        payload,
        private_key_pem,
        algorithm=JWT_ALGORITHM,
        headers={"kid": KEY_ID}
    )

    # Generate a refresh token
    refresh_token = str(uuid.uuid4())
    refresh_tokens[refresh_token] = {
        "sub": user_info["sub"],
        "client_id": token_request.client_id,
        "scope": code_data["original_request"]["scope"],
        "audience": code_data["original_request"].get("resource") or "https://api.openmemory.io",
        "user_info": user_info,
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    }

    # Store token info
    access_tokens[access_token] = {
        "user_info": user_info,
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)
    }

    # Clean up code
    del auth_codes[token_request.code]

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": JWT_EXPIRE_MINUTES * 60,
        "scope": code_data["original_request"]["scope"],
        "id_token": access_token,  # Same as access token for simplicity
        "refresh_token": refresh_token
    }

async def handle_refresh_token_grant(token_request: TokenRequest):
    """Handle refresh token grant flow"""
    if not token_request.refresh_token:
        return JSONResponse(
            status_code=400,
            content={
                "error": "invalid_request",
                "error_description": "refresh_token is required for refresh_token grant"
            }
        )

    if token_request.refresh_token not in refresh_tokens:
        return JSONResponse(
            status_code=400,
            content={
                "error": "invalid_grant",
                "error_description": "The provided refresh token is invalid"
            }
        )

    refresh_token_data = refresh_tokens[token_request.refresh_token]

    # Check if refresh token is expired
    if refresh_token_data["expires_at"] < datetime.utcnow():
        # Remove expired refresh token
        del refresh_tokens[token_request.refresh_token]
        return JSONResponse(
            status_code=400,
            content={
                "error": "invalid_grant",
                "error_description": "The refresh token has expired"
            }
        )

    # Generate a new access token
    now = datetime.utcnow()
    user_info = refresh_token_data["user_info"]

    payload = {
        "sub": user_info["sub"],
        "email": user_info["email"],
        "name": user_info["name"],
        "picture": user_info.get("picture"),
        "iss": BASE_URL,
        "aud": refresh_token_data.get("audience", "https://api.openmemory.io"),
        "iat": now,
        "exp": now + timedelta(minutes=JWT_EXPIRE_MINUTES),
        "scope": refresh_token_data["scope"]
    }

    # Sign with RSA private key
    private_key_pem = RSA_PRIVATE_KEY.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

    new_access_token = jwt.encode(
        payload,
        private_key_pem,
        algorithm=JWT_ALGORITHM,
        headers={"kid": KEY_ID}
    )

    # Implement refresh token rotation: invalidate old token and create new one
    old_refresh_token = token_request.refresh_token
    new_refresh_token = str(uuid.uuid4())

    # Remove old refresh token
    del refresh_tokens[old_refresh_token]

    # Create new refresh token
    refresh_tokens[new_refresh_token] = {
        "sub": user_info["sub"],
        "client_id": refresh_token_data["client_id"],
        "scope": refresh_token_data["scope"],
        "audience": refresh_token_data.get("audience", "https://api.openmemory.io"),
        "user_info": user_info,
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    }

    # Store new access token info
    access_tokens[new_access_token] = {
        "user_info": user_info,
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)
    }

    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "expires_in": JWT_EXPIRE_MINUTES * 60,
        "scope": refresh_token_data["scope"],
        "id_token": new_access_token,
        "refresh_token": new_refresh_token
    }

@app.get("/auth/userinfo")
async def userinfo(request: Request):
    """
    OIDC UserInfo endpoint
    Return user information from JWT token
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid Authorization header")

    token = auth_header.split(" ")[1]

    try:
        # Verify with RSA public key
        public_key_pem = RSA_PUBLIC_KEY.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        payload = jwt.decode(
            token,
            public_key_pem,
            algorithms=[JWT_ALGORITHM],
            issuer=BASE_URL
        )
        return {
            "sub": payload["sub"],
            "email": payload["email"],
            "name": payload["name"],
            "picture": payload.get("picture"),
            "email_verified": True
        }
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")

@app.get("/auth/jwks")
async def jwks(response: Response):
    """
    JSON Web Key Set endpoint
    Returns RSA public key for JWT signature verification with caching headers
    """
    # Add cache headers (10 minutes)
    response.headers["Cache-Control"] = "public, max-age=600"
    response.headers["ETag"] = f'"{KEY_ID}"'

    # Get RSA public key numbers
    public_numbers = RSA_PUBLIC_KEY.public_numbers()

    # Convert to base64url format for JWKS
    def int_to_base64url_uint(val):
        """Convert integer to base64url-encoded string without padding"""
        byte_length = (val.bit_length() + 7) // 8
        return base64.urlsafe_b64encode(val.to_bytes(byte_length, 'big')).decode('ascii').rstrip('=')

    return {
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "alg": "RS256",
                "kid": KEY_ID,
                "n": int_to_base64url_uint(public_numbers.n),  # modulus
                "e": int_to_base64url_uint(public_numbers.e)   # exponent
            }
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8766)
