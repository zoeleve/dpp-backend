import requests
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
LOGIN_URL = f"{BASE_URL}/auth/login"
GRAPH_URL = f"{BASE_URL}/dpp/sparql/graph/"
SEARCH_URL = f"{BASE_URL}/dpp/json/search"

USERNAME = os.getenv("API_USERNAME", "zoe")
PASSWORD = os.getenv("API_PASSWORD", "test")

def get_token():
    res = requests.post(LOGIN_URL, json={"username": USERNAME, "password": PASSWORD})
    return res.json().get("access_token")

def check_graphs():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Get all DPPs
    res = requests.post(SEARCH_URL, json={"search_mode": "simple", "keywords": " ", "limit": 100}, headers=headers)
    items = res.json().get("results", [])
    
    print(f"🔍 Checking Graphs for {len(items)} DPPs...")
    
    for item in items:
        dpp_id = item['id']
        title = item['title']
        
        # 2. Fetch Graph
        graph_res = requests.get(f"{GRAPH_URL}{dpp_id}", headers=headers)
        
        if graph_res.status_code == 200:
            data = graph_res.json()
            nodes = len(data.get("nodes", []))
            edges = len(data.get("edges", []))
            
            if nodes > 0:
                print(f"   ✅ ID {dpp_id}: {title[:30]}... -> {nodes} Nodes, {edges} Edges")
            else:
                print(f"   ⚠️ ID {dpp_id}: {title[:30]}... -> EMPTY GRAPH (0 Nodes)")
        else:
            print(f"   ❌ ID {dpp_id}: Failed ({graph_res.status_code})")

if __name__ == "__main__":
    check_graphs()
