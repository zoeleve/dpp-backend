import json
from typing import Any, Dict, Optional, List
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

def _clean_keys(data: Any) -> Any:
    """
    Recursively removes namespaces from keys in a dict (e.g., 'aas:idShort' -> 'idShort').
    """
    if isinstance(data, dict):
        return {k.split(':')[-1]: _clean_keys(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [_clean_keys(item) for item in data]
    return data

def _extract_submodels_list(data: Any) -> List[Dict[str, Any]]:
    """
    Extracts and cleans a list of submodels from the raw extracted data.
    Handles xmltodict quirks (dict vs list, nested keys).
    """
    cleaned = _clean_keys(data)
    
    if isinstance(cleaned, list):
        return cleaned
    
    if isinstance(cleaned, dict):
        # xmltodict often wraps the list in a tag name, e.g. {'submodel': [...]}
        for k, v in cleaned.items():
            if isinstance(v, list) and 'submodel' in k.lower():
                return v
            if isinstance(v, dict) and 'idShort' in v:
                 return [v] # Single item wrapped
        
        if 'idShort' in cleaned:
            return [cleaned]
            
    return []

def _extract_simple_value(val: Any) -> Any:
    """
    Attempts to extract a simple string representation from a complex value dict.
    Handles LangStrings, References, and generic text wrappers.
    """
    if not isinstance(val, dict):
        return val
    
    # 1. Handle LangString (e.g. {'langString': [{'@lang': 'en', '#text': 'value'}]})
    if "langString" in val:
        ls = val["langString"]
        if isinstance(ls, list):
            # Try to find English
            for item in ls:
                if isinstance(item, dict):
                    lang = item.get('@lang') or item.get('language')
                    text = item.get('#text') or item.get('text')
                    if lang and 'en' in lang.lower() and text:
                        return text
            # Fallback to first item
            if len(ls) > 0 and isinstance(ls[0], dict):
                return ls[0].get('#text') or ls[0].get('text')
        elif isinstance(ls, dict):
            return ls.get('#text') or ls.get('text')
            
    # 2. Handle generic text wrapper (xmltodict artifact)
    if "#text" in val:
        return val["#text"]
        
    return val

def _simplify_submodel_data(data: Any) -> Any:
    """
    Simplifies the nested AAS structure into a flat dictionary {idShort: value}.
    Recursively handles SubmodelElementCollections.
    """
    if not isinstance(data, dict):
        return data

    # Check if this is a container of elements (submodelElements or Collection value)
    if "submodelElement" in data:
        elements = data["submodelElement"]
        if isinstance(elements, dict): # Handle single element case
            elements = [elements]
        
        result = {}
        for el in elements:
            # Unwrap wrapper if present (e.g. {'property': {...}} -> {...})
            item = el
            if isinstance(el, dict) and len(el) == 1:
                first_val = list(el.values())[0]
                if isinstance(first_val, dict) and "idShort" in first_val:
                    item = first_val
            
            # Safety check: Ensure item is a dictionary before accessing keys
            if isinstance(item, dict) and "idShort" in item:
                key = item["idShort"]
                # Recursively simplify the value
                if "value" in item:
                    val = item["value"]
                    # If value is a container (Collection), recurse
                    if isinstance(val, dict) and "submodelElement" in val:
                        result[key] = _simplify_submodel_data(val)
                    else:
                        # Try to simplify complex values (LangString, etc.) to avoid [object Object]
                        result[key] = _extract_simple_value(val)
        return result

    return data

def _get_value_safely(element: Any) -> Any:
    """
    Extracts the actual value from an AAS element, ignoring namespaces.
    Handles LangStrings and simple values.
    """
    if not isinstance(element, dict):
        return element
    
    # 1. Find the 'value' key ignoring namespace (e.g. ns0:value, value)
    value_key = next((k for k in element.keys() if k.split(':')[-1] == 'value'), None)
    
    val = element.get(value_key) if value_key else None

    if val is None:
        return None

    # 2. Handle complex values (Dicts)
    if isinstance(val, dict):
        # Check for LangString (e.g. ns0:langString, langString)
        lang_keys = [k for k in val.keys() if k.split(':')[-1] == 'langString']
        if lang_keys:
            ls = val[lang_keys[0]]
            
            # XML parsing often results in a list or dict for langString
            if isinstance(ls, list):
                # Try to find English
                for item in ls:
                    if isinstance(item, dict):
                        lang = item.get('@lang') or item.get('language')
                        text = item.get('#text') or item.get('text')
                        if lang == 'en' and text:
                            return text
                # Fallback to first item's text
                first = ls[0]
                if isinstance(first, dict):
                    return first.get('#text') or first.get('text')
                return str(first)
            
            elif isinstance(ls, dict):
                return ls.get('#text') or ls.get('text')
            
            return ls

        # Check for #text (XML text content)
        if '#text' in val:
            return val['#text']
            
    return val


def auto_extract_fields(parsed_data: dict) -> dict:
    logger.debug(f"Start extraction from data keys: {list(parsed_data.keys())}")
    extracted = {}

    for field, possible_keys in FIELD_MAPPING.items():
        # 1. Try finding by idShort (Semantic search - e.g. 'ManufacturerName')
        value = _search(parsed_data, possible_keys)
        
        # 2. If not found, try finding by Key (Structural search - e.g. 'submodels')
        if value is None:
            value = _search_key(parsed_data, possible_keys)

        if value is not None:
            extracted[field] = value

    # ✅ Explicitly handle submodels to ensure correct list structure and clean keys
    raw_submodels = _search_key(parsed_data, ["submodels", "submodel"])
    if raw_submodels:
        submodels_list = _extract_submodels_list(raw_submodels)
        # Simplify the submodelElements for each submodel to make it Frontend-friendly
        for sm in submodels_list:
            if "submodelElements" in sm:
                simplified = _simplify_submodel_data(sm["submodelElements"])
                # Flatten nested collections to avoid [object Object] in frontend
                # e.g. "ContactInfo": {"City": "Lohr"} -> "ContactInfo.City": "Lohr"
                sm["submodelElements"] = flatten_dict(simplified, sep=".")
        
        extracted["submodels"] = submodels_list

    # Fill missing fields
    for field in DPPBase.model_fields.keys():
        extracted.setdefault(field, None)

    # Ensure submodels is a list (Pydantic requires List, not None)
    if extracted.get("submodels") is None:
        extracted["submodels"] = []

    # Post-processing: Convert complex types to strings for text fields, 
    # but keep attributes/submodels as objects.
    for k, v in extracted.items():
        if k in ["attributes", "submodels"]:
            continue
        
        if isinstance(v, (dict, list)):
            extracted[k] = json.dumps(v)
        elif v is not None:
            extracted[k] = str(v)

    logger.debug(f"✅ Final extracted dict: {extracted}")
    return extracted


def _search_key(data: Any, target_keys: list[str]) -> Any:
    """
    Recursively searches for a dictionary key matching one of the target_keys (ignoring namespace).
    Useful for finding structural elements like 'submodels' or 'assets'.
    """
    if isinstance(data, dict):
        # 1. Check current keys
        for k, v in data.items():
            # clean key: remove namespace (e.g. 'aas:submodels' -> 'submodels')
            clean_key = k.split(':')[-1].lower()
            for target in target_keys:
                if clean_key == target.lower():
                    return v
        
        # 2. Recursion
        for v in data.values():
            found = _search_key(v, target_keys)
            if found is not None:
                return found
    
    elif isinstance(data, list):
        for item in data:
            found = _search_key(item, target_keys)
            if found is not None:
                return found
    return None


def _search(data: Any, keys: list[str]) -> Any:
    """
    Recursively searches for a SubmodelElement where idShort matches one of the keys.
    Returns the value extracted safely.
    """
    # 1. Recursion for Lists
    if isinstance(data, list):
        for item in data:
            result = _search(item, keys)
            if result is not None:
                return result
    
    # 2. Check Dicts
    if isinstance(data, dict):
        # Check if this dict is the element we are looking for
        id_short_key = next((k for k in data.keys() if k.split(':')[-1].lower() == 'idshort'), None)
        
        if id_short_key:
            id_short_val = data[id_short_key]
            if isinstance(id_short_val, str):
                for key in keys:
                    if key.lower() in id_short_val.lower():
                        val = _get_value_safely(data)
                        if val is not None:
                            logger.debug(f"🧩 Matched field '{key}' from idShort '{id_short_val}' → {val}")
                            return val
        
        # Recursion for values
        for v in data.values():
            result = _search(v, keys)
            if result is not None:
                return result
                
    return None