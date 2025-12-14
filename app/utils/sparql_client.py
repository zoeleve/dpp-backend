from typing import Dict, Any, List
from fastapi import HTTPException, status
import httpx
import json
from app.models.user import User
from app.configs.config import settings


class SPARQLException(Exception):
    """Custom exception for SPARQL query/update failures."""
    pass


# MIME types for RDF export/import
RDF_FORMAT_MAPPING = {
    "turtle": "text/turtle",
    "rdfxml": "application/rdf+xml",
    "jsonld": "application/ld+json",
}


async def execute_sparql_query(sparql_query: str, current_user: User) -> List[Dict[str, Any]]:
    """
    Executes a SPARQL SELECT query against the Fuseki query endpoint.
    Returns raw results as a list of dictionaries.
    """

    # Check for UPDATE operations
    if sparql_query.upper().strip().startswith(("INSERT", "DELETE", "CREATE", "DROP", "LOAD")):
        raise SPARQLException("UPDATE or Graph modification operations are not allowed via the query endpoint.")

    headers = {
        "Accept": "application/sparql-results+json"
    }
    params = {
        "query": sparql_query
    }

    print(f"Attempting to connect to Fuseki at: {settings.FUSEKI_QUERY_URL}") # DEBUG PRINT

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(settings.FUSEKI_QUERY_URL, params=params, headers=headers)
            response.raise_for_status()

            data = response.json()

            # Extract and simplify results
            bindings = data.get('results', {}).get('bindings', [])
            results = [{k: v['value'] for k, v in binding.items()} for binding in bindings]

            # TODO: Implement Post-Query Security Filtering here, if results contain un-authorized DPP URIs.

            return results

    except httpx.HTTPStatusError as e:
        print(f"Fuseki HTTP Error: {e}") # DEBUG PRINT
        raise SPARQLException(f"Fuseki HTTP Error: {e.response.status_code} - {e.response.text}")
    except httpx.RequestError as e:
        print(f"Fuseki Connection Error: {e}") # DEBUG PRINT
        raise SPARQLException(f"Could not connect to Fuseki endpoint at {settings.FUSEKI_QUERY_URL}: {e}")
    except json.JSONDecodeError:
        print("Fuseki JSON Decode Error") # DEBUG PRINT
        raise SPARQLException("Invalid JSON response from Fuseki.")


async def execute_sparql_update(sparql_update: str):
    """
    Executes a SPARQL UPDATE query (INSERT/DELETE) against the Fuseki update endpoint.
    """

    # Basic check to ensure it's actually an UPDATE operation
    if not sparql_update.upper().strip().startswith(("INSERT", "DELETE", "LOAD", "CLEAR")):
        raise SPARQLException("Only SPARQL UPDATE operations are allowed for this endpoint.")

    headers = {
        "Content-Type": "application/sparql-update"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(settings.FUSEKI_UPDATE_URL, content=sparql_update, headers=headers)
            response.raise_for_status()
            return True

    except httpx.HTTPStatusError as e:
        raise SPARQLException(f"Fuseki UPDATE Error: {e.response.status_code} - {e.response.text}")
    except httpx.RequestError as e:
        raise SPARQLException(f"Could not connect to Fuseki update endpoint: {e}")


async def get_dpp_rdf_data(dpp_uri: str, format: str) -> str:
    """
    Fetches the RDF data for a specific DPP (identified by its URI/Graph name)
    from the Fuseki data endpoint in the specified format.
    """
    mime_type = RDF_FORMAT_MAPPING.get(format.lower())
    if not mime_type:
        raise ValueError(f"Unsupported RDF format: {format}")

    headers = {
        "Accept": mime_type
    }
    params = {
        "graph": dpp_uri  # Use the DPP URI as the Named Graph identifier
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # We use the FUSEKI_DATA_URL to query a specific named graph
            response = await client.get(settings.FUSEKI_DATA_URL, params=params, headers=headers)
            response.raise_for_status()

            return response.text

    except httpx.HTTPStatusError as e:
        # 404 is acceptable if the graph hasn't been created yet
        if e.response.status_code == 404:
            return ""
        raise SPARQLException(f"Fuseki Data Fetch Error: {e.response.status_code}")
    except httpx.RequestError as e:
        raise SPARQLException(f"Could not connect to Fuseki data endpoint: {e}")
