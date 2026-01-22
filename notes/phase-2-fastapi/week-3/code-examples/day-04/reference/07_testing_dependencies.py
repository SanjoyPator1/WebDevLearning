"""
07_testing_dependencies.py

Topics covered:
- Dependency overrides for testing
- Mocking external services
- Testing with different user roles
- Testing database dependencies

This file includes both the app and test examples.

Run app: uvicorn 07_testing_dependencies:app --reload
Run tests: pytest 07_testing_dependencies.py -v
"""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.testclient import TestClient
import pytest

app = FastAPI()


# ============================================================================
# PRODUCTION DEPENDENCIES
# ============================================================================

class RealDatabase:
    """Production database"""
    
    def get_user(self, user_id: int):
        return {"id": user_id, "name": "Real User", "source": "production"}


class RealExternalAPI:
    """Production external API"""
    
    def fetch_data(self):
        return {"data": "from real API", "source": "production"}


def get_database() -> RealDatabase:
    """Production database dependency"""
    return RealDatabase()


def get_external_api() -> RealExternalAPI:
    """Production external API dependency"""
    return RealExternalAPI()


def get_current_user(token: str = "default") -> dict:
    """Production authentication"""
    if token == "valid":
        return {"id": 1, "username": "alice", "role": "user"}
    raise HTTPException(401, "Invalid token")


# ============================================================================
# ENDPOINTS USING DEPENDENCIES
# ============================================================================

@app.get("/user/{user_id}")
async def get_user(
    user_id: int,
    db: RealDatabase = Depends(get_database)
):
    """Get user from database"""
    return db.get_user(user_id)


@app.get("/external-data")
async def get_external_data(
    api: RealExternalAPI = Depends(get_external_api)
):
    """Fetch data from external API"""
    return api.fetch_data()


@app.get("/protected")
async def protected_endpoint(
    user: dict = Depends(get_current_user)
):
    """Protected endpoint requiring authentication"""
    return {"message": "Access granted", "user": user}


@app.get("/admin-only")
async def admin_only(
    user: dict = Depends(get_current_user)
):
    """Admin-only endpoint"""
    if user["role"] != "admin":
        raise HTTPException(403, "Admin access required")
    return {"message": "Admin access granted"}


# ============================================================================
# TEST DEPENDENCIES (MOCKS)
# ============================================================================

class MockDatabase:
    """Test database with predictable data"""
    
    def get_user(self, user_id: int):
        return {"id": user_id, "name": "Test User", "source": "test"}


class MockExternalAPI:
    """Test external API that doesn't make real network calls"""
    
    def fetch_data(self):
        return {"data": "from mock API", "source": "test"}


def get_mock_database() -> MockDatabase:
    """Test database dependency"""
    return MockDatabase()


def get_mock_external_api() -> MockExternalAPI:
    """Test external API dependency"""
    return MockExternalAPI()


def get_mock_user() -> dict:
    """Test user (always authenticated)"""
    return {"id": 1, "username": "test_user", "role": "user"}


def get_mock_admin() -> dict:
    """Test admin user"""
    return {"id": 2, "username": "test_admin", "role": "admin"}


# ============================================================================
# TESTS
# ============================================================================

def test_user_endpoint_with_mock_db():
    """Test user endpoint with mocked database"""
    app.dependency_overrides[get_database] = get_mock_database
    
    client = TestClient(app)
    response = client.get("/user/123")
    
    assert response.status_code == 200
    assert response.json() == {
        "id": 123,
        "name": "Test User",
        "source": "test"
    }
    
    app.dependency_overrides.clear()


def test_external_api_with_mock():
    """Test external API endpoint without making real API calls"""
    app.dependency_overrides[get_external_api] = get_mock_external_api
    
    client = TestClient(app)
    response = client.get("/external-data")
    
    assert response.status_code == 200
    assert response.json() == {
        "data": "from mock API",
        "source": "test"
    }
    
    app.dependency_overrides.clear()


def test_protected_endpoint_with_mock_user():
    """Test protected endpoint with mocked authentication"""
    app.dependency_overrides[get_current_user] = get_mock_user
    
    client = TestClient(app)
    response = client.get("/protected")
    
    assert response.status_code == 200
    assert "Access granted" in response.json()["message"]
    
    app.dependency_overrides.clear()


def test_admin_endpoint_with_regular_user():
    """Test admin endpoint with regular user (should fail)"""
    app.dependency_overrides[get_current_user] = get_mock_user
    
    client = TestClient(app)
    response = client.get("/admin-only")
    
    assert response.status_code == 403
    
    app.dependency_overrides.clear()


def test_admin_endpoint_with_admin_user():
    """Test admin endpoint with admin user (should succeed)"""
    app.dependency_overrides[get_current_user] = get_mock_admin
    
    client = TestClient(app)
    response = client.get("/admin-only")
    
    assert response.status_code == 200
    assert "Admin access granted" in response.json()["message"]
    
    app.dependency_overrides.clear()


def test_multiple_overrides():
    """Test with multiple dependency overrides"""
    app.dependency_overrides[get_database] = get_mock_database
    app.dependency_overrides[get_external_api] = get_mock_external_api
    app.dependency_overrides[get_current_user] = get_mock_user
    
    client = TestClient(app)
    
    response1 = client.get("/user/1")
    assert response1.json()["source"] == "test"
    
    response2 = client.get("/external-data")
    assert response2.json()["source"] == "test"
    
    response3 = client.get("/protected")
    assert response3.status_code == 200
    
    app.dependency_overrides.clear()


# ============================================================================
# PYTEST FIXTURES FOR CLEANER TESTS
# ============================================================================

@pytest.fixture
def client():
    """Fixture providing test client"""
    return TestClient(app)


@pytest.fixture
def mock_db():
    """Fixture for database override"""
    app.dependency_overrides[get_database] = get_mock_database
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def mock_user():
    """Fixture for user override"""
    app.dependency_overrides[get_current_user] = get_mock_user
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def mock_admin():
    """Fixture for admin override"""
    app.dependency_overrides[get_current_user] = get_mock_admin
    yield
    app.dependency_overrides.clear()


# Tests using fixtures
def test_with_mock_db_fixture(client, mock_db):
    """Cleaner test using fixture"""
    response = client.get("/user/456")
    assert response.status_code == 200
    assert response.json()["source"] == "test"


def test_with_mock_user_fixture(client, mock_user):
    """Cleaner test using fixture"""
    response = client.get("/protected")
    assert response.status_code == 200


def test_with_mock_admin_fixture(client, mock_admin):
    """Cleaner test using fixture"""
    response = client.get("/admin-only")
    assert response.status_code == 200


# ============================================================================
# PARAMETRIZED TESTS
# ============================================================================

@pytest.mark.parametrize("user_id,expected_name", [
    (1, "Test User"),
    (100, "Test User"),
    (999, "Test User"),
])
def test_multiple_users(client, mock_db, user_id, expected_name):
    """Test multiple user IDs with parametrization"""
    response = client.get(f"/user/{user_id}")
    assert response.status_code == 200
    assert response.json()["name"] == expected_name


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
