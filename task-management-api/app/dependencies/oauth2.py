from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
from app.security.jwt_handler import JWTManager
from app.database.users import UserManager, User

# OAuth2 password bearer scheme
# This tells FastAPI to look for "Authorization: Bearer <token>" headers
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login",  # Where to get tokens
    scopes={
        "read": "Read access",
        "write": "Write access", 
        "admin": "Admin access"
    }
)

class OAuth2Handler:
    """OAuth2 authentication handler"""
    
    @staticmethod
    def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
        """
        Extract and validate current user from JWT token
        
        Process:
        1. Extract token from Authorization header
        2. Verify JWT signature and expiration
        3. Get user from database
        4. Return authenticated user
        """
        
        # Create credentials exception for invalid tokens
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
        try:
            # Verify and decode JWT token
            payload = JWTManager.verify_token(token)
            if payload is None:
                raise credentials_exception
            
            # Extract username from token payload
            username: str = payload.get("sub")
            if username is None:
                raise credentials_exception
                
        except Exception:
            raise credentials_exception
        
        # Get user from database
        user = UserManager.get_user_by_id(payload.get("user_id"))
        if user is None:
            raise credentials_exception
        
        # Check if user account is still active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is disabled"
            )
        
        return user
    
    @staticmethod
    def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
        """
        Get current active user (additional check for active status)
        This dependency can be used when you want to be extra sure user is active
        """
        if not current_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Inactive user"
            )
        return current_user
    
    @staticmethod
    def get_optional_user(token: Optional[str] = Depends(oauth2_scheme)) -> Optional[User]:
        """
        Get current user if authenticated, None if not
        Useful for endpoints that work with or without authentication
        """
        if not token:
            return None
        
        try:
            payload = JWTManager.verify_token(token)
            if payload is None:
                return None
            
            user = UserManager.get_user_by_id(payload.get("user_id"))
            return user if user and user.is_active else None
            
        except Exception:
            return None

# Dependency functions (these are what you use in your endpoints)
def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Get current authenticated user"""
    return OAuth2Handler.get_current_user(token)

def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user"""
    return OAuth2Handler.get_current_active_user(current_user)

def get_optional_user() -> Optional[User]:
    """Get current user if authenticated, None otherwise"""
    return OAuth2Handler.get_optional_user()