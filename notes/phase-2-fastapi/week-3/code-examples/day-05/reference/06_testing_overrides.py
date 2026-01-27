from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

app = FastAPI()

# --- Production Dependency ---
def get_current_user():
    # Imagine this connects to Auth0 or a Database
    return {"id": 1, "username": "prod_user"}

@app.get("/me")
async def read_me(user: dict = Depends(get_current_user)):
    return user

# --- Test Logic ---
client = TestClient(app)

def test_override_dependency():
    # 1. Define the mock
    def mock_get_current_user():
        return {"id": 999, "username": "test_user_mock"}

    # 2. Apply the override
    app.dependency_overrides[get_current_user] = mock_get_current_user

    # 3. Run the request
    response = client.get("/me")
    
    # 4. Assertions
    assert response.status_code == 200
    assert response.json() == {"id": 999, "username": "test_user_mock"}
    print("Test Passed: Dependency was overridden successfully.")

    # 5. Cleanup
    app.dependency_overrides = {}

if __name__ == "__main__":
    test_override_dependency()