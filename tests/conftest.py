import pytest
import asyncio
from typing import AsyncGenerator, Generator
from httpx import AsyncClient, ASGITransport
from app.main import app

# Force session scope for the event loop
@pytest.fixture(scope="session")
def event_loop() -> Generator:
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

@pytest.fixture
async def test_user(client: AsyncClient):
    """
    Ensures a test user exists.
    """
    user_data = {
        "username": "test_user_pytest",
        "password": "test_password_123",
        "email": "pytest@example.com",
        "role": "admin" # Admin role to allow all actions
    }
    
    # Try to register
    # Note: The register endpoint expects Form data usually, let's check router
    # Assuming /users/create expects Form data based on previous checks
    # But for simplicity in tests, we might just use the login if user exists
    # Or try to create.
    
    # Let's try to login first to see if exists
    login_res = await client.post("/auth/login", json={"username": user_data["username"], "password": user_data["password"]})
    
    if login_res.status_code != 200:
        # Create user if not exists
        # We need to send Form data for creation as per user.py router
        await client.post("/users/create", data=user_data)
        
    return user_data

@pytest.fixture
async def auth_headers(client: AsyncClient, test_user) -> dict:
    """
    Logs in the test user and returns Authorization headers.
    """
    res = await client.post("/auth/login", json={
        "username": test_user["username"], 
        "password": test_user["password"]
    })
    assert res.status_code == 200
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

