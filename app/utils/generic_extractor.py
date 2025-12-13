import json
from typing import Any, Dict
from difflib import SequenceMatcher
from loguru import logger
from app.schemas.dpp import DPPBase
from app.constants import FIELD_MAPPING

def flatten_dict(data: Any, parent_key: str = "", sep: str = "_") -> Dict[str, Any]:
    """Recursively flattens nested dict/list structures."""
    items = []
    if isinstance(data, dict):
        for k, v in data.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            items.extend(flatten_dict(v, new_key, sep=sep).items())
    elif isinstance(data, list):
        for i, v in enumerate(data):
            new_key = f"{parent_key}{sep}{i}"
            items.extend(flatten_dict(v, new_key, sep=sep).items())
    else:
        items.append((parent_key, data))
    return dict(items)


def similarity(a: str, b: str) -> float:
    """Returns a fuzzy similarity ratio between two strings."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def auto_extract_fields(parsed_data: dict) -> dict:
    logger.debug(f"Start {parsed_data}")
    extracted = {}

    for field, possible_keys in FIELD_MAPPING.items():
        value = _search(parsed_data, possible_keys)
        if isinstance(value, dict):
            value = value.get("ns0:value") or value.get("@value") or str(value)
        if value is not None:
            extracted[field] = value

    # Fill missing fields with None
    for field in DPPBase.model_fields.keys():
        extracted.setdefault(field, None)

    # Convert dicts and None to safe strings for Pydantic
    for k, v in extracted.items():
        if v is None:
            extracted[k] = ""
        elif isinstance(v, dict):
            extracted[k] = json.dumps(v)

    logger.debug(f"✅ Final extracted dict: {extracted}")
    return extracted



def _search(data: Any, keys: list[str]) -> Any:
    """
    Αναδρομικά ψάχνει για idShort που περιέχει κάποιο από τα keys
    """
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, (dict, list)):
                found = _search(v, keys)
                if found is not None:
                    return found
            if "idshort" in k.lower() and isinstance(v, str):
                for key in keys:
                    if key.lower() in v.lower():
                        logger.debug(f"🧩 Matched field '{key}' from idShort '{v}' → {data.get('ns0:value')}")
                        return data.get("ns0:value")
    elif isinstance(data, list):
        for item in data:
            found = _search(item, keys)
            if found is not None:
                return found
    return None