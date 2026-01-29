import requests
import os
from dotenv import load_dotenv

load_dotenv()

host = os.getenv("FUSEKI_HOST", "localhost")
port = os.getenv("FUSEKI_PORT", "3030")
dataset_name = "ds" 

query_url = f"http://{host}:{port}/{dataset_name}/sparql"

print(f"🔍 Inspecting Fuseki Graphs at {query_url}...")

# Query to list all named graphs and count their triples
query = """
SELECT ?g (COUNT(*) AS ?count)
WHERE {
  GRAPH ?g { ?s ?p ?o }
}
GROUP BY ?g
"""

try:
    response = requests.get(query_url, params={"query": query}, headers={"Accept": "application/sparql-results+json"})
    
    if response.status_code == 200:
        data = response.json()
        bindings = data.get("results", {}).get("bindings", [])
        
        if not bindings:
            print("   ⚠️ No Named Graphs found (Dataset is empty or uses default graph).")
            
            # Check default graph
            default_query = "SELECT (COUNT(*) AS ?count) WHERE { ?s ?p ?o }"
            res_def = requests.get(query_url, params={"query": default_query}, headers={"Accept": "application/sparql-results+json"})
            count = res_def.json()["results"]["bindings"][0]["count"]["value"]
            print(f"   - Default Graph: {count} triples")
            
        else:
            print(f"   ✅ Found {len(bindings)} Named Graphs:")
            for b in bindings:
                graph_uri = b["g"]["value"]
                count = b["count"]["value"]
                print(f"   - {graph_uri}: {count} triples")
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")

except Exception as e:
    print(f"💥 Connection Failed: {e}")
