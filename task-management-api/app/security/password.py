from passlib.context import CryptContext
from passlib.hash import bcrypt
import secrets
import string

# Create password context using bcrypt algorithm
# bcrypt is a slow, adaptive hashing function designed for passwords
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class PasswordManager:
    """Utility class for password operations"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a plain text password using bcrypt
        
        bcrypt automatically:
        - Generates a unique salt for each password
        - Uses multiple rounds of hashing (slow by design)
        - Produces a different hash each time, even for same password
        
        Example: "mypassword123" -> "$2b$12$abcd1234..."
        """
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a plain text password against its hash
        
        This is safe because:
        - We never store plain text passwords
        - bcrypt extracts the salt from the stored hash
        - Computes hash of plain_password with same salt
        - Compares the results securely
        """
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def generate_random_password(length: int = 12) -> str:
        """
        Generate a secure random password
        Useful for temporary passwords or password resets
        """
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        return password
    
    @staticmethod
    def is_password_strong(password: str) -> tuple[bool, list[str]]:
        """
        Check if password meets security requirements
        Returns: (is_strong, list_of_issues)
        """
        issues = []
        
        if len(password) < 8:
            issues.append("Password must be at least 8 characters long")
        
        if not any(c.isupper() for c in password):
            issues.append("Password must contain at least one uppercase letter")
        
        if not any(c.islower() for c in password):
            issues.append("Password must contain at least one lowercase letter")
        
        if not any(c.isdigit() for c in password):
            issues.append("Password must contain at least one digit")
        
        if not any(c in "!@#$%^&*()_+-=" for c in password):
            issues.append("Password must contain at least one special character")
        
        return len(issues) == 0, issues

# Example usage:
# hashed = PasswordManager.hash_password("mypassword123")
# is_valid = PasswordManager.verify_password("mypassword123", hashed)