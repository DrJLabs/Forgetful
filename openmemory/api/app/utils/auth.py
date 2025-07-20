"""
JWT Authentication utilities for validating tokens from OIDC server
"""

import os
import jwt
import httpx
from typing import Optional, Dict, Any
from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

# OIDC Configuration
OIDC_JWKS_URL = os.getenv("OIDC_JWKS_URL", "https://oidc.drjlabs.com/auth/jwks")
OIDC_ISSUER = os.getenv("OIDC_ISSUER", "https://oidc.drjlabs.com")

logger = logging.getLogger(__name__)

# JWKS cache
_jwks_cache = None
_jwks_cache_expiry = None

security = HTTPBearer(auto_error=False)

class JWTPayload:
    """JWT token payload structure"""
    def __init__(self, payload: dict):
        self.sub = payload.get("sub")  # Google user ID
        self.email = payload.get("email")
        self.name = payload.get("name")
        self.picture = payload.get("picture")
        self.iss = payload.get("iss")
        self.aud = payload.get("aud")
        self.exp = payload.get("exp")
        self.scope = payload.get("scope", "")

async def fetch_jwks() -> Dict[str, Any]:
    """Fetch JWKS from OIDC server with caching"""
    global _jwks_cache, _jwks_cache_expiry
    
    from datetime import datetime, timedelta
    now = datetime.utcnow()
    
    # Check cache validity (10 minute TTL)
    if _jwks_cache and _jwks_cache_expiry and now < _jwks_cache_expiry:
        return _jwks_cache
    
    async with httpx.AsyncClient() as client:
        response = await client.get(OIDC_JWKS_URL)
        response.raise_for_status()
        jwks = response.json()
        
        # Cache for 10 minutes
        _jwks_cache = jwks
        _jwks_cache_expiry = now + timedelta(minutes=10)
        
        return jwks

def jwk_to_rsa_key(jwk: Dict[str, Any]):
    """Convert JWK to RSA public key"""
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
    import base64
    
    # Decode base64url-encoded values
    def base64url_decode(data):
        missing_padding = len(data) % 4
        if missing_padding:
            data += '=' * (4 - missing_padding)
        return base64.urlsafe_b64decode(data)
    
    n = int.from_bytes(base64url_decode(jwk['n']), 'big')
    e = int.from_bytes(base64url_decode(jwk['e']), 'big')
    
    public_numbers = rsa.RSAPublicNumbers(e, n)
    return public_numbers.public_key()

async def validate_jwt_token(token: str) -> Optional[JWTPayload]:
    """
    Validate JWT token from OIDC server using RSA public key
    Returns None if token is invalid
    """
    try:
        # Fetch JWKS to get public key
        jwks = await fetch_jwks()
        
        # Get key ID from token header
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get('kid')
        
        # Find matching key in JWKS
        public_key = None
        for key in jwks['keys']:
            if key.get('kid') == kid:
                public_key = jwk_to_rsa_key(key)
                break
        
        if not public_key:
            logger.warning(f"No matching key found for kid: {kid}")
            return None
        
        # Verify token with RSA public key
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            issuer=OIDC_ISSUER,
            options={"verify_aud": False}  # Audience varies by client
        )
        
        return JWTPayload(payload)
        
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {e}")
        return None
    except Exception as e:
        logger.error(f"Error validating JWT token: {e}")
        return None

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Optional[JWTPayload]:
    """
    Dependency to get current user from JWT token
    Returns None if no valid token provided (allows optional auth)
    """
    if not credentials:
        return None
    
    return await validate_jwt_token(credentials.credentials)

async def require_authentication(current_user: JWTPayload = Depends(get_current_user)) -> JWTPayload:
    """
    Dependency that requires valid authentication
    Raises HTTPException if no valid token provided
    """
    if not current_user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user

async def get_user_id_from_auth(current_user: Optional[JWTPayload] = Depends(get_current_user)) -> str:
    """
    Get user_id from JWT token or fall back to default for backward compatibility
    """
    if current_user:
        # Use Google user ID from JWT
        return current_user.sub
    else:
        # Fall back to default user ID for existing usage
        from app.config import USER_ID
        return USER_ID 