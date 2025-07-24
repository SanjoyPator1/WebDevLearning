from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./task_management.db"
    
    # Security
    secret_key: str = "your-super-secret-key-change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Environment
    environment: str = "development"
    debug: bool = True

    # Email Settings - MailHog Configuration
    smtp_host: str = "localhost"
    smtp_port: int = 1025  # MailHog SMTP port
    smtp_user: str = ""    # MailHog doesn't require authentication
    smtp_password: str = ""
    smtp_from_email: str = "Task Manager <noreply@taskmanager.local>"

    # Email Features
    send_emails: bool = True  # Set to False to completely disable emails
    
    class Config:
        env_file = ".env"

# Create settings instance
settings = Settings()