# app/utils/dpp_search_engine.py
from typing import List, Any
from sqlalchemy import select, func, or_, and_, asc, desc, text, cast, String, Float, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import BinaryExpression, TextClause
from app.models.dpp import DPP
from app.schemas.dpp import SearchSchema, SearchMode, ComparisonOperator, SearchMatch, AdvancedCriteria, SortingWeight
from app.models.user import User  # Assuming User model import
from app.configs.roles import Role


# --- 1. JSONB Query Translation ---

def _build_advanced_jsonb_filter(criteria: AdvancedCriteria) -> BinaryExpression:
    """
    Translates a single AdvancedCriteria object into a SQLAlchemy JSONB filtering expression.
    """
    key = criteria.field_key
    value = criteria.field_value
    op = criteria.comparison_operator
    match = criteria.match_type

    # Access the dpp_data JSONB column
    dpp_data_column = DPP.dpp_data[key]

    # 1. Handle Numeric Comparisons (if operator is present)
    if op:
        # We assume numeric values are stored as text in JSONB and must be cast to numeric for comparison
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            raise ValueError(
                f"Value '{value}' for key '{key}' is not numeric, but a comparison operator '{op.value}' was provided.")

        # Cast the JSONB value to numeric type for comparison
        jsonb_value_numeric = cast(dpp_data_column, Float)

        if op == ComparisonOperator.EQ:
            return jsonb_value_numeric == numeric_value
        if op == ComparisonOperator.NE:
            return jsonb_value_numeric != numeric_value
        if op == ComparisonOperator.GT:
            return jsonb_value_numeric > numeric_value
        if op == ComparisonOperator.GTE:
            return jsonb_value_numeric >= numeric_value
        if op == ComparisonOperator.LT:
            return jsonb_value_numeric < numeric_value
        if op == ComparisonOperator.LTE:
            return jsonb_value_numeric <= numeric_value

    # 2. Handle Text/Exact/Partial Matching (Default behavior if no operator)

    if isinstance(value, str):
        search_term = str(value).strip()

        if match == SearchMatch.EXACT:
            # Exact text match within JSONB (using ->> operator)
            return cast(dpp_data_column, String) == search_term

        if match == SearchMatch.PARTIAL:
            # Partial text match (using ILIKE for case-insensitive LIKE)
            return cast(dpp_data_column, String).ilike(f"%{search_term}%")

    # 3. Handle Multi-Value Matching (e.g., searching for tags in a JSON array)
    if isinstance(value, list):
        # We need to construct a PostgreSQL query that checks if all/any values are contained in the JSONB array

        # A simpler approach using JSONB contains operator (@>) for array containment:
        jsonb_list_value = func.jsonb_build_array(*value)

        if criteria.multi_value_logic == 'all':
            # Check if JSONB array in DPP contains ALL elements in the search list
            return dpp_data_column.op('@>')(jsonb_list_value)

        if criteria.multi_value_logic == 'any':
            # Check if JSONB array in DPP contains ANY element in the search list.
            # The @> operator checks if the left JSON contains the right JSON.
            # To check "ANY", we need to check if the intersection is not empty, OR check each item individually.
            # Checking individually is safer with standard operators:
            
            or_conditions = []
            for item in value:
                # Build a single-item JSON array for containment check
                single_item_json = func.jsonb_build_array(item)
                or_conditions.append(dpp_data_column.op('@>')(single_item_json))
            
            return or_(*or_conditions)

    # Fallback for unexpected criteria type
    return cast(dpp_data_column, String) == value


# --- 2. DPP Search Core Function ---

async def search_dpps(
        db: AsyncSession,
        search_data: SearchSchema,
        current_user: User
) -> tuple[List[DPP], int]:
    """
    Executes the DPP search based on the provided SearchSchema.
    Returns the list of DPPs and the total count (before pagination).
    """

    # Base query for DPPs
    query = select(DPP)
    filters = []

    # 1. Ownership and Publication Filter (Access Control)

    # Users (non-owners) can only see published DPPs
    # Owners can see their own, published or not.
    # Admins can see everything.

    if current_user.role != Role.ADMIN:
        # All results must either be published OR belong to the current user
        ownership_filter = or_(
            DPP.is_published == True,
            DPP.owner_id == current_user.id
        )
        filters.append(ownership_filter)
    # If Admin, no ownership filter is applied (they see all)

    # 2. Search Mode Specific Filters

    if search_data.search_mode == SearchMode.SIMPLE:
        # Simple Search (Full-Text Search approximation)
        keywords = search_data.keywords
        
        # CHANGE: Check if there are actual terms after stripping
        if keywords and keywords.strip():
            # Determine logic: AND (if '+' or 'AND' present) vs OR (default)
            if '+' in keywords:
                terms = [t.strip() for t in keywords.split('+') if t.strip()]
                logic = 'AND'
            elif ' AND ' in keywords: # Case sensitive check for ' AND '
                 terms = [t.strip() for t in keywords.split(' AND ') if t.strip()]
                 logic = 'AND'
            else:
                # Default OR logic, split by space
                terms = [t.strip() for t in keywords.split() if t.strip()]
                logic = 'OR'

            # ONLY apply filters if terms list is not empty
            if terms:
                term_filters = []
                for term in terms:
                    # Search in title OR in the JSONB data
                    term_filter = or_(
                        DPP.title.ilike(f"%{term}%"),
                        cast(DPP.dpp_data, String).ilike(f"%{term}%")
                    )
                    term_filters.append(term_filter)

                if logic == 'AND':
                    # All terms must match
                    filters.append(and_(*term_filters))
                else:
                    # At least one term must match
                    filters.append(or_(*term_filters))

    elif search_data.search_mode == SearchMode.ADVANCED:
        # Advanced Search (JSONB operators)

        advanced_filters = []
        for criteria in search_data.advanced_criteria:
            advanced_filters.append(_build_advanced_jsonb_filter(criteria))

        # By default, all advanced criteria must match (AND logic)
        filters.append(and_(*advanced_filters))

    elif search_data.search_mode == SearchMode.SPARQL:
        # SPARQL Search is handled entirely outside of this function
        # (by contacting Apache Jena Fuseki directly from the router).
        # We can raise an error if this function is mistakenly called for SPARQL mode.
        raise ValueError("SPARQL search mode must be handled by the dedicated SPARQL client.")

    # Apply all collected filters
    if filters:
        query = query.filter(and_(*filters))

    # --- 3. Sorting / Ranking ---

    ordering = []

    if search_data.sorting_weights and search_data.search_mode != SearchMode.SPARQL:
        # Weighted Ranking is requested (Optional requirement)

        # Calculate the Total Utility Score for each DPP
        score_clauses = []

        for item in search_data.sorting_weights:
            # Utility function for a field (linear for simplicity)
            # We assume the value can be converted to a number for linear utility calculation.

            # Use PostgreSQL to extract and cast the value
            field_value_num = cast(DPP.dpp_data[item.field_key], Float)

            if item.normalize:
                # Min-Max Normalization: (X - Min) / (Max - Min)
                # We use window functions over the current result set to get Min/Max dynamically
                f_min = func.min(field_value_num).over()
                f_max = func.max(field_value_num).over()
                denominator = f_max - f_min

                # Avoid division by zero if all values are the same
                normalized_val = case(
                    (denominator == 0, 0.0),
                    else_=(field_value_num - f_min) / denominator
                )

                if item.direction == 'desc':
                    # Lower is better (e.g., CO2): Score = Weight * (1 - Normalized)
                    utility = item.weight * (1.0 - normalized_val)
                else:
                    # Higher is better (e.g., Efficiency): Score = Weight * Normalized
                    utility = item.weight * normalized_val
            else:
                # Raw value usage (Legacy/Simple)
                if item.direction == 'desc':
                    # Inverse relationship: 1 / value (Handle div by zero)
                    utility = item.weight * (1.0 / func.nullif(field_value_num, 0))
                else:
                    utility = item.weight * field_value_num

            score_clauses.append(utility)

        # Total Score is the sum of weighted utilities
        # Use Python's sum() to add up the SQLAlchemy expressions
        total_score = sum(score_clauses).label("total_score")

        # Add the score to the selection and order by it (DESC)
        query = query.add_columns(total_score)
        ordering.append(desc(total_score))

    elif search_data.search_mode == SearchMode.SIMPLE and search_data.keywords:
        # Default sorting for Simple Search: relevance (based on FTS score, if implemented)
        # Since we approximated FTS, we can't use a true FTS rank.
        # We default to sorting by creation date for now.
        ordering.append(desc(DPP.created_at))

    # Default order (if no ranking/relevance provided)
    if not ordering:
        ordering.append(desc(DPP.created_at))

    query = query.order_by(*ordering)

    # --- 4. Pagination (Count and Limit/Offset) ---

    # Get total count before applying limit/offset
    count_query = select(func.count()).select_from(query.subquery())
    total_count_result = await db.execute(count_query)
    total_count = total_count_result.scalar_one()

    # Apply limit and offset
    query = query.offset(search_data.offset).limit(search_data.limit)

    # Execute the final query
    result = await db.execute(query)

    # Handle the case where the query selected columns + score
    if search_data.sorting_weights:
        # We get (DPP, score) tuples
        dpps = [r[0] for r in result.all()]
    else:
        # We get only DPP objects
        dpps = result.scalars().all()

    return dpps, total_count
