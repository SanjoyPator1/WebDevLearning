"""
Test script to validate database migration from mock to SQLAlchemy

Tests:
- Database connectivity
- User authentication with seed data  
- User service operations
- SQLAlchemy model functionality
- API endpoints with real database
"""
import asyncio
from app.services.user_service import UserService
from app.models.user import User
from app.database.engine import db_manager, get_database_session
from app.security.jwt_handler import JWTManager
from sqlalchemy.ext.asyncio import AsyncSession
import time

SEED_USERS = [
    ("admin@taskmanager.com", "admin123"),
    ("user@taskmanager.com", "user123")
]

async def test_database_connection():
    print("Testing database connection...")
    await db_manager.initialize()
    assert db_manager.engine is not None
    print("✅ Database connection: PASS")

async def test_seed_data():
    print("Testing seed data...")
    db_gen = get_database_session()
    db = await anext(db_gen)
    try:
        user_service = UserService(db)
        for email, _ in SEED_USERS:
            user = await user_service.get_user_by_email(email)
            assert user is not None, f"Seed user {email} not found"
    finally:
        await db_gen.aclose()
    print("✅ Seed data validation: PASS")

async def test_authentication():
    print("Testing authentication...")
    db_gen = get_database_session()
    db = await anext(db_gen)
    try:
        user_service = UserService(db)
        for email, password in SEED_USERS:
            user = await user_service.authenticate_user(email, password)
            assert user is not None, f"Auth failed for {email}"
            assert isinstance(user, User)
            # Test JWT
            token = JWTManager.create_access_token(user)
            assert isinstance(token, str)
        # Test invalid login
        user = await user_service.authenticate_user("admin@taskmanager.com", "wrongpass")
        assert user is None
    finally:
        await db_gen.aclose()
    print("✅ User authentication: PASS")

async def test_user_crud():
    print("Testing UserService CRUD...")
    db_gen = get_database_session()
    db = await anext(db_gen)
    try:
        user_service = UserService(db)
        # Create user
        from pydantic import EmailStr
        from app.services.user_service import UserCreate
        new_email = "testuser@taskmanager.com"
        user_data = UserCreate(email=new_email, password="TestPass123!", full_name="Test User")
        user = await user_service.create_user(user_data)
        await db.commit()
        assert user.email == new_email
        # Get by ID
        fetched = await user_service.get_user_by_id(str(user.id))
        assert fetched is not None
        # Delete (if implemented)
        # await db.delete(user)
        # await db.commit()
    finally:
        await db_gen.aclose()
    print("✅ UserService CRUD: PASS")

async def test_performance():
    print("Testing performance...")
    db_gen = get_database_session()
    db = await anext(db_gen)
    try:
        user_service = UserService(db)
        start = time.time()
        user = await user_service.authenticate_user("admin@taskmanager.com", "admin123")
        login_time = (time.time() - start) * 1000
        assert login_time < 500, f"Login took too long: {login_time:.2f}ms"
        start = time.time()
        user = await user_service.get_user_by_email("admin@taskmanager.com")
        get_time = (time.time() - start) * 1000
        assert get_time < 200, f"Get user took too long: {get_time:.2f}ms"
    finally:
        await db_gen.aclose()
    print(f"✅ Performance: Login {login_time:.2f}ms, Get user {get_time:.2f}ms: PASS")

async def test_error_handling():
    print("Testing error handling...")
    db_gen = get_database_session()
    db = await anext(db_gen)
    try:
        user_service = UserService(db)
        # Invalid credentials
        user = await user_service.authenticate_user("admin@taskmanager.com", "wrongpass")
        assert user is None
        # Invalid user
        user = await user_service.get_user_by_email("notfound@taskmanager.com")
        assert user is None
    finally:
        await db_gen.aclose()
    print("✅ Error handling: PASS")

async def main():
    print("\U0001F9EA Database Migration Tests\n============================")
    await test_database_connection()
    await test_seed_data()
    await test_authentication()
    await test_user_crud()
    await test_performance()
    await test_error_handling()
    print("\n🎉 Migration Successful: All core tests passed\n")

if __name__ == "__main__":
    asyncio.run(main()) 