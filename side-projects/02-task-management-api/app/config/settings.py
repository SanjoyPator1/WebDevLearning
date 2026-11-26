"""
Main application settings - NO database config here
"""
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Security
    secret_key: str = "your-super-secret-key-change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Environment
    environment: str = "development"
    debug: bool = True

    # Email Settings
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "Task Manager <noreply@taskmanager.local>"
    send_emails: bool = True
    
    class Config:
        env_file = ".env"
        extra = "allow"

# Create settings instance
settings = Settings()