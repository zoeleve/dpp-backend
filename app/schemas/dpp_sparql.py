from pydantic import BaseModel, Field, constr
from typing import List, Dict, Any, Optional

class SPARQLQueryRequest(BaseModel):
    query: constr(min_length=1) = Field(..., description="The raw SPARQL SELECT query to execute.")
    limit: int = Field(100, ge=1)
    offset: int = Field(0, ge=0)


class SPARQLQueryResponse(BaseModel):
    total_count: Optional[int] = None
    limit: int
    offset: int
    results: List[Dict[str, Any]]
