from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from app.config import settings

# JWT Configuration
SECRET_KEY = settings.secret_key  # Should be a long, random string
ALGORITHM = "HS256"  # HMAC with SHA-256
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes

class JWTManager:
    """JWT token creation and validation"""
    
    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """
        Create a JWT access token
        
        JWT Structure:
        - Header: Algorithm and token type {"alg": "HS256", "typ": "JWT"}
        - Payload: Data + expiration {"sub": "user123", "exp": 1234567890, ...}
        - Signature: Encoded header + payload signed with secret key
        
        The token looks like: xxxxx.yyyyy.zzzzz (header.payload.signature)
        """
        to_encode = data.copy()
        
        # Set expiration time
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        # Add expiration to payload
        to_encode.update({"exp": expire})
        
        # Create and sign the token
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode a JWT token
        
        Verification process:
        1. Check token format (3 parts separated by dots)
        2. Verify signature using secret key
        3. Check expiration time
        4. Return payload if valid, None if invalid
        """
        try:
            # Decode and verify the token
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            
            # Extract username (subject) from payload
            username: str = payload.get("sub")
            if username is None:
                return None
            
            return payload
            
        except JWTError as e:
            # Token is invalid (expired, tampered with, or malformed)
            print(f"JWT Error: {e}")
            return None
    
    @staticmethod
    def create_refresh_token(data: Dict[str, Any]) -> str:
        """
        Create a refresh token (longer expiration, used to get new access tokens)
        
        Refresh tokens:
        - Last longer than access tokens (days/weeks vs minutes/hours)
        - Used to get new access tokens without re-login
        - Should be stored securely and can be revoked
        """
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(days=7)  # 7 days
        to_encode.update({"exp": expire, "type": "refresh"})
        
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def decode_token(token: str) -> Dict[str, Any]:
        """
        Decode token without verification (for debugging)
        WARNING: Only use for debugging, not for security decisions!
        """
        try:
            # Decode without verification (options={"verify_signature": False})
            payload = jwt.decode(token, options={"verify_signature": False})
            return payload
        except JWTError:
            return {}

# Example JWT payload structure:
# {
#   "sub": "user123",           # Subject (user identifier)
#   "exp": 1640995200,         # Expiration time (Unix timestamp)
#   "iat": 1640908800,         # Issued at time
#   "role": "user",            # Custom claims
#   "email": "user@example.com"
# }