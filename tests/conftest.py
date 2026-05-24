import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
import os

TEST_USERNAME = os.getenv("API_USERNAME", "zoe")
TEST_PASSWORD = os.getenv("API_PASSWORD", "test")

@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac

@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient):
    response = await client.post(
        "/auth/login",
        json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
    )
    assert response.status_code == 200, (
        f"Login failed ({response.status_code}): {response.text}"
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}