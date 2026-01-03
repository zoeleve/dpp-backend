# app/schemas/dpp.py
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field, constr, field_validator, model_validator
from datetime import datetime


# --- 1. CORE DPP DATA SCHEMAS (AAS ALIGNED) ---

class AASSubmodel(BaseModel):
    """
    Represents an Asset Administration Shell (AAS) Submodel.
    Examples: DigitalNameplate, CarbonFootprint, TechnicalData.
    """
    idShort: str = Field(..., description="Short identifier for the submodel (e.g., 'DigitalNameplate')")
    semanticId: Optional[str] = Field(None, description="Reference to the semantic definition (e.g., ECLASS IRDI)")
    submodelElements: Dict[str, Any] = Field(default_factory=dict, description="Key-value pairs of data elements")


class DPPBase(BaseModel):
    # Core universally valid DPP identifiers (AAS AssetInformation)
    product_id: Optional[constr(min_length=3, max_length=200)] = Field(
        None, 
        description="GlobalAssetId (e.g., DID, GTIN, UUID)"
    )
    manufacturer: Optional[str] = None
    model_number: Optional[str] = None
    serial_number: Optional[str] = None
    production_date: Optional[str] = None

    # AAS Submodels: Structured data instead of flat attributes
    # We keep 'attributes' for backward compatibility but encourage 'submodels'
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Legacy flat attributes")
    
    submodels: List[AASSubmodel] = Field(
        default_factory=list, 
        description="List of AAS Submodels (e.g., CarbonFootprint, Circularity)"
    )

    @field_validator("product_id", mode="before")
    @classmethod
    def empty_to_none(cls, v):
        if not v or (isinstance(v, str) and not v.strip()):
            return None
        return v


class DPPCreate(DPPBase):
    """Schema for creating a new DPP."""
    title: constr(min_length=1)


class DPPUpdate(DPPBase):
    """Schema for updating an existing DPP."""
    title: Optional[constr(min_length=1)] = None


# --- 2. RESPONSE SCHEMAS ---

class DPPResponse(DPPBase):
    """Full DPP response schema including database metadata."""
    id: int
    dpp_uuid: str
    owner_id: int
    title: str
    is_published: bool
    created_at: datetime
    updated_at: datetime

    # We will use this field to return the full JSONB data in the response
    dpp_data: Dict[str, Any]

    class Config:
        from_attributes = True


class DPPStatus(BaseModel):
    """Schema for the response when changing DPP status (publish/unpublish)."""
    dpp_uuid: str
    is_published: bool
    message: str


class DPPStats(BaseModel):
    """Schema for global DPP statistics."""
    total_dpps: int
    published_dpps: int
    draft_dpps: int
    my_dpps: int  # Count of DPPs owned by the current user


# --- 3. SEARCH & SORTING SCHEMAS ---

class SearchMode(str, Enum):
    """Defines the supported search types."""
    SIMPLE = "simple"
    ADVANCED = "advanced"
    SPARQL = "sparql"


class SearchMatch(str, Enum):
    """Defines the matching logic for Advanced Search (Non-Numeric)."""
    EXACT = "exact"  # Exact match
    PARTIAL = "partial"  # Value contains the search term


class ComparisonOperator(str, Enum):
    """Defines the comparison operators for Advanced Search (Numeric)."""
    EQ = "="
    NE = "!="
    GT = ">"
    GTE = ">="
    LT = "<"
    LTE = "<="


class AdvancedCriteria(BaseModel):
    """Defines a single key-value search pair for Advanced Search."""

    # The field name (key) to search within the DPP data
    field_key: constr(min_length=1)

    # The value(s) to search for
    field_value: Any

    # Matching logic for non-numeric fields
    match_type: Optional[SearchMatch] = SearchMatch.EXACT

    # Operator for numeric fields
    comparison_operator: Optional[ComparisonOperator] = None

    # Logic for multiple values (e.g., in a list field): 'all' or 'any'
    multi_value_logic: Optional[constr(pattern=r"^(all|any)$")] = "any"


class SortingWeight(BaseModel):
    """Defines a field and its weight for weighted ranking."""

    # The field name to use for sorting (must exist in DPP data)
    field_key: constr(min_length=1)

    # The weight (0.0 to 1.0) of this field in the total score
    weight: float = Field(..., ge=0, le=1)

    # Direction of partial utility (e.g., 'asc' for higher is better, 'desc' for lower is better)
    direction: constr(pattern=r"^(asc|desc)$") = "asc"


class SearchSchema(BaseModel):
    """
    Main schema for searching DPPs. Uses Pydantic's discriminator pattern
    to handle three mutually exclusive search types.
    """

    # --- Search Type Discriminator ---
    search_mode: SearchMode = Field(
        ...,
        description="Defines the type of search to perform: simple, advanced, or sparql."
    )

    # --- Simple Search Fields ---
    # Keywords for SIMPLE search (can be '+' or 'AND' separated)
    keywords: Optional[str] = None

    # --- Advanced Search Fields ---
    # List of key-value criteria for ADVANCED search
    advanced_criteria: Optional[List[AdvancedCriteria]] = None

    # --- SPARQL Search Fields ---
    # The raw SPARQL query string for SPARQL search
    sparql_query: Optional[str] = None

    # --- Optional Ranking/Sorting Fields ---

    # Optional field to specify sorting logic for SIMPLE and ADVANCED searches
    sorting_weights: Optional[List[SortingWeight]] = None

    # Pagination
    limit: int = Field(10, ge=1, le=100)
    offset: int = Field(0, ge=0)

    @field_validator("sorting_weights")
    @classmethod
    def validate_weights(cls, weights):
        """Ensures the sum of sorting weights equals 1.0, if provided."""
        if weights:
            total_weight = sum(w.weight for w in weights)
            if not 0.999 <= total_weight <= 1.001:
                # Allowing a small tolerance for floating point arithmetic
                raise ValueError("The sum of sorting_weights must equal 1.0.")
        return weights

    @model_validator(mode='before')
    def validate_search_fields_based_on_mode(cls, values):
        """Ensures only relevant fields are provided for the chosen search mode."""
        mode = values.get('search_mode')
        keywords = values.get('keywords')
        criteria = values.get('advanced_criteria')
        sparql = values.get('sparql_query')

        # Simple Search check
        # Allow empty keywords for "list all" functionality
        if mode == SearchMode.SIMPLE and keywords is None:
             # If keywords is None, we can default it to empty string or handle it in logic.
             # But the validator was raising error if not keywords.
             # We should allow it if it's present but empty string?
             # The frontend sends keywords="" which is truthy? No, empty string is falsy.
             # So 'not keywords' is True for "".
             
             # We change this to allow empty string for simple search (meaning "all")
             pass 

        if mode == SearchMode.SIMPLE and (criteria or sparql):
            raise ValueError("Advanced criteria or SPARQL query cannot be used in simple search mode.")

        # Advanced Search check
        if mode == SearchMode.ADVANCED and not criteria:
            raise ValueError("Advanced criteria must be provided for advanced search mode.")
        if mode == SearchMode.ADVANCED and (keywords or sparql):
            raise ValueError("Keywords or SPARQL query cannot be used in advanced search mode.")

        # SPARQL Search check
        if mode == SearchMode.SPARQL and not sparql:
            raise ValueError("SPARQL query must be provided for SPARQL search mode.")
        if mode == SearchMode.SPARQL and (keywords or criteria or values.get('sorting_weights')):
            # Sorting weights are excluded for SPARQL as sorting is done via the query
            raise ValueError("Keywords, advanced criteria, or sorting weights cannot be used in SPARQL search mode.")

        return values


class SearchResponse(BaseModel):
    total_count: int
    limit: int
    offset: int
    results: List[DPPResponse]
