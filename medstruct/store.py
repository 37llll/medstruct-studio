"""Schema and example storage for the product shell."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from .core.models import SchemaDefinition

PACKAGE_DIR = Path(__file__).resolve().parent
SCHEMA_DIR = PACKAGE_DIR / "schemas"
EXAMPLE_DIR = PACKAGE_DIR / "examples"


def list_schemas() -> List[Dict[str, object]]:
    schemas = []
    for path in sorted(SCHEMA_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        schemas.append(
            {
                "id": data["id"],
                "name": data["name"],
                "version": data.get("version", ""),
                "description": data.get("description", ""),
                "domain": data.get("domain", ""),
                "tags": data.get("tags", []),
                "field_count": len(data.get("fields", [])),
            }
        )
    return schemas


def load_schema(schema_id: str) -> SchemaDefinition:
    for path in SCHEMA_DIR.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("id") == schema_id:
            return SchemaDefinition.from_dict(data)
    raise KeyError(f"Schema 不存在: {schema_id}")


def load_schema_dict(schema_id: str) -> Dict[str, object]:
    for path in SCHEMA_DIR.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("id") == schema_id:
            return data
    raise KeyError(f"Schema 不存在: {schema_id}")


def list_examples() -> List[Dict[str, str]]:
    result = []
    for path in sorted(EXAMPLE_DIR.glob("*.txt")):
        result.append({"id": path.stem, "name": path.stem.replace("_", " "), "content": path.read_text(encoding="utf-8")})
    return result
