from fastapi import APIRouter, HTTPException, Depends, status
from app.utils.jwt_handler import get_current_active_user
from app.models.user import User
from app.models.dpp import DPP
from app.db.database_postgre import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.utils.sparql_client import execute_sparql_query, get_dpp_rdf_data, SPARQLException, RDF_BASE_URI
from app.schemas.dpp_sparql import SPARQLQueryRequest, SPARQLQueryResponse
from app.configs.roles import Role
from loguru import logger
from rdflib import Graph
from app.configs.config import settings
import re

router = APIRouter(prefix="/dpp/sparql", tags=["DPP SPARQL"])


@router.post("/query", response_model=SPARQLQueryResponse)
async def sparql_query_execution(
        request: SPARQLQueryRequest,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """
    Executes a raw SPARQL SELECT query against the semantic store (Fuseki).
    Only SELECT queries are permitted.
    
    SECURITY: 
    - Admins can query everything.
    - Regular users can ONLY query graphs that are PUBLISHED.
    - Queries MUST specify target graphs explicitly (via URIs in the query).
    """

    # 1. Basic Query Validation (Allow PREFIXes)
    # Remove PREFIX lines to check for SELECT
    clean_query = re.sub(r"(?i)PREFIX\s+[\w-]+:\s*<[^>]+>", "", request.query).strip()
    
    if not clean_query.upper().startswith("SELECT"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only SPARQL SELECT queries are allowed for this endpoint."
        )

    # 2. Access Control Logic
    if current_user.role != Role.ADMIN:
        # Extract all URIs that look like DPP Graphs
        base_uri_pattern = re.escape(RDF_BASE_URI + "/dpp/")
        matches = re.findall(f"{base_uri_pattern}([^\\s>}}]+)", request.query)
        
        if not matches:
            # Block queries that don't target specific graphs (to protect default graph)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Non-admin users must specify target Graphs explicitly in the query."
            )

        for uuid_part in matches:
            # Extract UUID (remove sub-paths like /Submodel)
            dpp_uuid = uuid_part.split("/")[0]
            
            # Check DB
            result = await db.execute(select(DPP).where(DPP.dpp_uuid == dpp_uuid))
            dpp = result.scalar_one_or_none()
            
            if not dpp:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied to unknown graph: {dpp_uuid}"
                )
            
            # STRICT CHECK: Must be Published
            if not dpp.is_published:
                # Optional: Allow owner to see their own drafts?
                # For now, we implement "Only Publish" as requested.
                # If you want to allow owners, uncomment:
                # if dpp.owner_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied to unpublished graph: {dpp_uuid}"
                )

    # 3. Execution via the client
    try:
        # The execute_sparql_query sends the request to Fuseki
        raw_results = await execute_sparql_query(
            request.query, current_user
        )

        # Return the raw results from Fuseki
        return SPARQLQueryResponse(
            total_count=len(raw_results),
            limit=request.limit,
            offset=request.offset,
            results=raw_results,
        )

    except SPARQLException as e:
        logger.error(f"SPARQL Execution Error: {e}")
        # Handling connection/execution errors from Fuseki
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"SPARQL Query Execution Failed: {str(e)}"
        )
    except Exception as e:
        logger.exception("Unexpected error in SPARQL endpoint")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during SPARQL execution: {str(e)}"
        )

@router.get("/graph/{dpp_id}")
async def get_dpp_graph_visualization(
    dpp_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Returns the RDF graph for a specific DPP in a format suitable for visualization
    (Nodes and Edges JSON).
    """
    # 1. Get DPP UUID from DB
    dpp = await db.get(DPP, dpp_id)
    if not dpp:
        raise HTTPException(status_code=404, detail="DPP not found")
    
    # Access Control: Admin can see everything, others check ownership/published status
    if current_user.role != Role.ADMIN:
        if not dpp.is_published and dpp.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to view this unpublished DPP")

    # 2. Construct Graph URI using the stable Base URI
    graph_uri = f"{RDF_BASE_URI}/dpp/{dpp.dpp_uuid}"

    try:
        # 3. Fetch RDF data from Fuseki (Turtle format)
        rdf_data = await get_dpp_rdf_data(graph_uri, "turtle")
        
        if not rdf_data:
            return {"nodes": [], "edges": []}

        # 4. Parse RDF using rdflib
        g = Graph()
        g.parse(data=rdf_data, format="turtle")

        # 5. Convert to Nodes/Edges format
        nodes = []
        edges = []
        added_nodes = set()

        for s, p, o in g:
            # Add Subject Node
            s_str = str(s)
            if s_str not in added_nodes:
                nodes.append({
                    "id": s_str,
                    "label": s_str.split("/")[-1], # Simple label from URI
                    "type": "Resource"
                })
                added_nodes.add(s_str)

            # Add Object Node (if it's a URI, not a Literal)
            # If it's a Literal, we can treat it as a property of the subject, 
            # or a separate node depending on visualization preference.
            # For graph viz, usually Literals are leaf nodes.
            o_str = str(o)
            if o_str not in added_nodes:
                is_literal = not isinstance(o, (type(s))) # Check if it's not a URIRef/BNode
                nodes.append({
                    "id": o_str,
                    "label": o_str if len(o_str) < 30 else o_str[:30] + "...", # Truncate long literals
                    "type": "Literal" if is_literal else "Resource"
                })
                added_nodes.add(o_str)

            # Add Edge
            edges.append({
                "source": s_str,
                "target": o_str,
                "label": str(p).split("/")[-1].split("#")[-1] # Extract predicate name
            })

        return {"nodes": nodes, "edges": edges}

    except Exception as e:
        logger.error(f"Failed to generate graph visualization: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate graph: {str(e)}")
