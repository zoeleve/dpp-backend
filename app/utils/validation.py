def filter_non_empty_fields(data: dict) -> dict:
    """
    Recursively remove keys with empty, null, or whitespace-only values.
    """
    clean = {}
    for k, v in data.items():
        if isinstance(v, dict):
            nested = filter_non_empty_fields(v)
            if nested:
                clean[k] = nested
        elif v not in (None, "", [], {}):
            clean[k] = v
    return clean
