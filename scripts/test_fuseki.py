import requests
import os
from dotenv import load_dotenv

load_dotenv()

host = os.getenv("FUSEKI_HOST", "localhost")
port = os.getenv("FUSEKI_PORT", "3030")
dataset_name = "ds" 

base_url = f"http://{host}:{port}/{dataset_name}"

print(f"🔍 Probing QUERY endpoints for dataset '{dataset_name}'...")

query_endpoints = [
    f"{base_url}/sparql",
    f"{base_url}/query",
]

query = "SELECT * { ?s ?p ?o } LIMIT 1"

for url in query_endpoints:
    print(f"   Testing: {url}")
    try:
        response = requests.get(url, params={"query": query})
        if response.status_code == 200:
            print(f"   ✅ SUCCESS! Found Query endpoint: {url}")
        else:
            print(f"      ❌ {response.status_code}")
    except Exception as e:
        print(f"      💥 Error: {e}")
