import json
import os
from typing import Any, Dict, Optional

_RESOURCE_DIR = os.path.join(os.path.dirname(__file__), '..', 'resources')
_CACHE: Dict[str, Any] = {}

def _load_json(filename: str) -> Optional[Dict[str, Any]]:
    path = os.path.join(_RESOURCE_DIR, filename)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Warning: Could not load {filename}: {e}")
        return None

def get_format_data(key: str, default: Any = None) -> Any:
    if 'formats' not in _CACHE:
        _CACHE['formats'] = _load_json('formats.json') or {}
    return _CACHE['formats'].get(key, default)

def get_help_sections() -> list:
    if 'help' not in _CACHE:
        _CACHE['help'] = _load_json('help.json') or {}
    return _CACHE['help'].get('sections', [])

def get_strings() -> Dict[str, Any]:
    if 'strings' not in _CACHE:
        _CACHE['strings'] = _load_json('strings.json') or {}
    return _CACHE['strings']

def get_tool_descriptions() -> Dict[str, str]:
    if 'tool_descriptions' not in _CACHE:
        _CACHE['tool_descriptions'] = _load_json('tool_descriptions.json') or {}
    return _CACHE['tool_descriptions']