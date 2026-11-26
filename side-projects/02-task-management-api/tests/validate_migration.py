"""
Quick validation script for database migration

Performs essential checks:
- No remaining UserManager imports
- Database connectivity
- Seed data exists
- Authentication works
- Basic API functionality
"""
import asyncio
import importlib.util
import time
import httpx
from app.database.engine import db_manager, get_database_session
from app.services.user_service import UserService

async def check_no_usermanager():
    print("Checking for UserManager imports...")
    # Check for UserManager in active code
    import os
    for root, _, files in os.walk("app"):
        for file in files:
            if file.endswith(".py"):
                with open(os.path.join(root, file)) as f:
                    content = f.read()
                    if "UserManager" in content and not file == "users.py":
                        print(f"❌ UserManager found in {os.path.join(root, file)}")
                        return False
    print("✅ No UserManager imports: PASS")
    return True

async def check_db():
    print("Checking database connectivity...")
    await db_manager.initialize()
    assert db_manager.engine is not None
    print("✅ Database connectivity: PASS")
    return True

async def check_seed():
    print("Checking seed data...")
    db_gen = get_database_session()
    db = await anext(db_gen)
    try:
        user_service = UserService(db)
        user = await user_service.get_user_by_email("admin@taskmanager.com")
        assert user is not None
    finally:
        await db_gen.aclose()
    print("✅ Seed data: PASS")
    return True

async def check_auth():
    print("Checking authentication...")
    db_gen = get_database_session()
    db = await anext(db_gen)
    try:
        user_service = UserService(db)
        user = await user_service.authenticate_user("admin@taskmanager.com", "admin123")
        assert user is not None
    finally:
        await db_gen.aclose()
    print("✅ Authentication: PASS")
    return True

async def check_performance():
    print("Checking performance...")
    db_gen = get_database_session()
    db = await anext(db_gen)
    try:
        user_service = UserService(db)
        start = time.time()
        user = await user_service.authenticate_user("admin@taskmanager.com", "admin123")
        login_time = (time.time() - start) * 1000
        assert login_time < 500, f"Login took too long: {login_time:.2f}ms"
    finally:
        await db_gen.aclose()
    print(f"✅ Performance: Login {login_time:.2f}ms: PASS")
    return True

async def check_error_handling():
    print("Checking error handling...")
    db_gen = get_database_session()
    db = await anext(db_gen)
    try:
        user_service = UserService(db)
        user = await user_service.authenticate_user("admin@taskmanager.com", "wrongpass")
        assert user is None
    finally:
        await db_gen.aclose()
    print("✅ Error handling: PASS")
    return True

async def check_api():
    print("Checking API endpoints...")
    async with httpx.AsyncClient() as client:
        resp = await client.post("http://localhost:8000/auth/login", data={"username": "admin@taskmanager.com", "password": "admin123"})
        assert resp.status_code == 200
        token = resp.json()["access_token"]
        resp = await client.get("http://localhost:8000/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
    print("✅ API endpoints: PASS")
    return True

async def main():
    print("\U0001F9EA Quick Migration Validation\n============================")
    results = []
    results.append(await check_no_usermanager())
    results.append(await check_db())
    results.append(await check_seed())
    results.append(await check_auth())
    results.append(await check_performance())
    results.append(await check_error_handling())
    results.append(await check_api())
    if all(results):
        print("\n🎉 Migration Validation: PASS\n")
    else:
        print("\n❌ Migration Validation: FAIL\n")

if __name__ == "__main__":
    asyncio.run(main()) 