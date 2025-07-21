from typing import Dict, List, Optional, Any
from datetime import datetime
from app.security.password import PasswordManager

# Mock user database (in real app, this would be a real database)
users_db: List[Dict[str, Any]] = []
user_id_counter: int = 1

class User:
    """User model for authentication"""
    
    def __init__(self, user_data: Dict[str, Any]):
        self.id = user_data["id"]
        self.username = user_data["username"]
        self.email = user_data["email"]
        self.hashed_password = user_data["hashed_password"]
        self.role = user_data.get("role", "user")
        self.is_active = user_data.get("is_active", True)
        self.created_at = user_data.get("created_at", datetime.now())
        self.last_login = user_data.get("last_login")
    
    def check_password(self, password: str) -> bool:
        """Verify password against stored hash"""
        return PasswordManager.verify_password(password, self.hashed_password)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary (excluding password)"""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "last_login": self.last_login
        }

class UserManager:
    """User database operations"""
    
    @staticmethod
    def create_user(username: str, email: str, password: str, role: str = "user") -> User:
        """
        Create a new user with hashed password
        
        Process:
        1. Check if username/email already exists
        2. Hash the password securely
        3. Create user record
        4. Store in database
        """
        global user_id_counter
        
        # Check if user already exists
        if UserManager.get_user_by_username(username):
            raise ValueError(f"Username '{username}' already exists")
        
        if UserManager.get_user_by_email(email):
            raise ValueError(f"Email '{email}' already exists")
        
        # Validate password strength
        is_strong, issues = PasswordManager.is_password_strong(password)
        if not is_strong:
            raise ValueError(f"Password requirements not met: {', '.join(issues)}")
        
        # Hash password
        hashed_password = PasswordManager.hash_password(password)
        
        # Create user data
        user_data = {
            "id": user_id_counter,
            "username": username,
            "email": email,
            "hashed_password": hashed_password,
            "role": role,
            "is_active": True,
            "created_at": datetime.now(),
            "last_login": None
        }
        
        # Store in database
        users_db.append(user_data)
        user_id_counter += 1
        
        return User(user_data)
    
    @staticmethod
    def authenticate_user(username: str, password: str) -> Optional[User]:
        """
        Authenticate user with username/password
        
        Process:
        1. Find user by username
        2. Verify password hash
        3. Update last login time
        4. Return user if valid, None if invalid
        """
        user_data = UserManager.get_user_by_username(username)
        if not user_data:
            return None
        
        user = User(user_data)
        
        # Check if account is active
        if not user.is_active:
            return None
        
        # Verify password
        if not user.check_password(password):
            return None
        
        # Update last login
        user_data["last_login"] = datetime.now()
        
        return user
    
    @staticmethod
    def get_all_users() -> List[User]:
        """Get all users"""
        return [User(user_data) for user_data in users_db]
    
    @staticmethod
    def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
        """Find user by username"""
        for user_data in users_db:
            if user_data["username"] == username:
                return user_data
        return None
    
    @staticmethod
    def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
        """Find user by email"""
        for user_data in users_db:
            if user_data["email"] == email:
                return user_data
        return None
    
    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[User]:
        """Find user by ID"""
        for user_data in users_db:
            if user_data["id"] == user_id:
                return User(user_data)
        return None
    
    @staticmethod
    def update_user_role(user_id: int, new_role: str) -> bool:
        """Update user role (admin function)"""
        for user_data in users_db:
            if user_data["id"] == user_id:
                user_data["role"] = new_role
                return True
        return False
    
    @staticmethod
    def deactivate_user(user_id: int) -> bool:
        """Deactivate user account"""
        for user_data in users_db:
            if user_data["id"] == user_id:
                user_data["is_active"] = False
                return True
        return False

# Create default admin user for testing
def create_default_users():
    """Create default users for testing"""
    try:
        # Admin user
        UserManager.create_user(
            username="admin",
            email="admin@example.com", 
            password="Admin123!",
            role="admin"
        )
        
        # Regular user
        UserManager.create_user(
            username="testuser",
            email="user@example.com",
            password="User123!",
            role="user"
        )
        
        # Guest user
        UserManager.create_user(
            username="guest",
            email="guest@example.com",
            password="Guest123!",
            role="guest"
        )
        
        print("Default users created successfully")
    except ValueError as e:
        print(f"Default users already exist: {e}")

# Initialize default users
create_default_users()