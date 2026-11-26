"""
API integration test for database migration

Tests all API endpoints work with real database:
- POST /auth/login with seed data
- GET /auth/me with JWT token
- POST /auth/register with new user
- GET /tasks/ with authenticated user
- POST /tasks/ with task creation
"""
import asyncio
import httpx
import time

API_URL = "http://localhost:8000"
SEED_USER = {"username": "admin@taskmanager.com", "password": "admin123"}
NEW_USER = {"username": "apitest@taskmanager.com", "email": "apitest@taskmanager.com", "password": "ApiTest123!", "role": "user"}

async def test_login(client):
    print("Testing /auth/login...")
    start = time.time()
    resp = await client.post(f"{API_URL}/auth/login", data=SEED_USER)
    login_time = (time.time() - start) * 1000
    assert resp.status_code == 200, resp.text
    assert login_time < 500, f"Login took too long: {login_time:.2f}ms"
    token = resp.json()["access_token"]
    print(f"✅ Login: PASS ({login_time:.2f}ms)")
    return token

async def test_me(client, token):
    print("Testing /auth/me...")
    start = time.time()
    resp = await client.get(f"{API_URL}/auth/me", headers={"Authorization": f"Bearer {token}"})
    me_time = (time.time() - start) * 1000
    assert resp.status_code == 200, resp.text
    assert me_time < 200, f"/auth/me took too long: {me_time:.2f}ms"
    data = resp.json()
    assert "id" in data and len(data["id"]) >= 32  # UUID
    print(f"✅ /auth/me: PASS ({me_time:.2f}ms)")

async def test_register(client):
    print("Testing /auth/register...")
    resp = await client.post(f"{API_URL}/auth/register", json=NEW_USER)
    assert resp.status_code == 201, resp.text
    print("✅ Register: PASS")

async def test_tasks(client, token):
    print("Testing /tasks/ endpoints...")
    # Get tasks
    start = time.time()
    resp = await client.get(f"{API_URL}/tasks/", headers={"Authorization": f"Bearer {token}"})
    get_time = (time.time() - start) * 1000
    assert resp.status_code == 200, resp.text
    assert get_time < 200, f"Get tasks took too long: {get_time:.2f}ms"
    # Create task
    task_data = {"title": "API Test Task", "priority": "high"}
    start = time.time()
    resp = await client.post(f"{API_URL}/tasks/", json=task_data, headers={"Authorization": f"Bearer {token}"})
    create_time = (time.time() - start) * 1000
    assert resp.status_code in (200, 201), resp.text
    assert create_time < 300, f"Create task took too long: {create_time:.2f}ms"
    print(f"✅ /tasks/: PASS (get {get_time:.2f}ms, create {create_time:.2f}ms)")

async def test_error_handling(client):
    print("Testing error handling...")
    # Invalid credentials
    resp = await client.post(f"{API_URL}/auth/login", data={"username": "admin@taskmanager.com", "password": "wrongpass"})
    assert resp.status_code == 401
    # Invalid JWT
    resp = await client.get(f"{API_URL}/auth/me", headers={"Authorization": "Bearer invalidtoken"})
    assert resp.status_code == 401
    print("✅ Error handling: PASS")

async def main():
    print("\U0001F9EA API Integration Tests\n============================")
    async with httpx.AsyncClient() as client:
        token = await test_login(client)
        await test_me(client, token)
        await test_register(client)
        await test_tasks(client, token)
        await test_error_handling(client)
    print("\n🎉 API Integration: All tests passed\n")

if __name__ == "__main__":
    asyncio.run(main()) 