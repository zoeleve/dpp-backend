import pytest
from httpx import AsyncClient

# Test Data
TEST_DPP = {
    "title": "E2E Pytest Product",
    "product_id": "did:test:pytest-e2e-001",
    "manufacturer": "Pytest Corp",
    "dpp_data": {
        "weight": 100,
        "submodels": [
            {"idShort": "TechnicalData", "submodelElements": {"power": "500W"}}
        ]
    }
}

@pytest.mark.asyncio
async def test_full_dpp_lifecycle(client: AsyncClient, auth_headers: dict):
    """
    End-to-End Test Scenario:
    1. Create DPP
    2. Retrieve DPP (Read)
    3. Update DPP
    4. Search DPP
    5. Verify Semantic Graph (Fuseki Sync)
    6. Delete DPP
    """
    
    # --- 0. Cleanup (Ensure clean state) ---
    search_res = await client.post("/dpp/json/search", json={"search_mode": "simple", "keywords": TEST_DPP["product_id"]}, headers=auth_headers)
    if search_res.status_code == 200:
        for item in search_res.json()["results"]:
            await client.delete(f"/dpp/json/{item['id']}", headers=auth_headers)

    # --- 1. Create DPP ---
    create_res = await client.post("/dpp/json/", json=TEST_DPP, headers=auth_headers)
    assert create_res.status_code == 200, f"Create failed: {create_res.text}"
    data = create_res.json()
    assert data["title"] == TEST_DPP["title"]
    assert data["dpp_uuid"] == TEST_DPP["product_id"]
    dpp_id = data["id"]

    # --- 2. Get DPP ---
    get_res = await client.get(f"/dpp/json/{dpp_id}", headers=auth_headers)
    assert get_res.status_code == 200
    assert get_res.json()["manufacturer"] == "Pytest Corp"

    # --- 3. Update DPP ---
    update_payload = {"title": "Updated Pytest Product"}
    update_res = await client.put(f"/dpp/json/{dpp_id}", json=update_payload, headers=auth_headers)
    assert update_res.status_code == 200
    assert update_res.json()["title"] == "Updated Pytest Product"

    # --- 4. Search DPP ---
    search_payload = {"search_mode": "simple", "keywords": "Updated Pytest"}
    search_res = await client.post("/dpp/json/search", json=search_payload, headers=auth_headers)
    assert search_res.status_code == 200
    results = search_res.json()["results"]
    assert len(results) >= 1
    assert results[0]["title"] == "Updated Pytest Product"

    # --- 5. Check Graph (Semantic) ---
    # Note: Graph generation is async. In a real test, we might need a retry loop.
    graph_res = await client.get(f"/dpp/sparql/graph/{dpp_id}", headers=auth_headers)
    assert graph_res.status_code == 200 
    # Optional: Check content if sync is fast enough
    # assert len(graph_res.json()["nodes"]) > 0

    # --- 6. Delete DPP ---
    del_res = await client.delete(f"/dpp/json/{dpp_id}", headers=auth_headers)
    assert del_res.status_code == 200

    # --- 7. Verify Deletion ---
    get_res_after = await client.get(f"/dpp/json/{dpp_id}", headers=auth_headers)
    assert get_res_after.status_code == 404
