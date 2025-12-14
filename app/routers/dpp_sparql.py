from fastapi import APIRouter, HTTPException, Depends, status
from app.utils.jwt_handler import get_current_active_user
from app.models.user import User
from app.utils.sparql_client import execute_sparql_query, SPARQLException
from app.schemas.dpp_sparql import SPARQLQueryRequest, SPARQLQueryResponse
from loguru import logger

router = APIRouter(prefix="/dpp/sparql", tags=["DPP SPARQL"])


@router.post("/query", response_model=SPARQLQueryResponse)
async def sparql_query_execution(
        request: SPARQLQueryRequest,
        current_user: User = Depends(get_current_active_user)
):
    """
    Executes a raw SPARQL SELECT query against the semantic store (Fuseki).
    Only SELECT queries are permitted.
    """

    # 1. Basic Query Validation
    if not request.query.upper().strip().startswith("SELECT"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only SPARQL SELECT queries are allowed for this endpoint."
        )

    # 2. Execution via the client
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
