"""MedStruct Studio product server."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .core import ExtractionEngine
from .core.models import ExtractionOptions, SchemaDefinition
from .store import list_examples, list_schemas, load_schema, load_schema_dict

WEB_DIR = Path(__file__).resolve().parent / "web"

app = FastAPI(
    title="MedStruct Studio",
    description="中文病历结构化抽取工具：schema 配置、规则/正则/本地模型、证据句与置信度复核。",
    version="0.1.0",
)
app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")
engine = ExtractionEngine()


class ExtractRequest(BaseModel):
    document: str = Field(..., min_length=1)
    schema_id: Optional[str] = None
    schema: Optional[Dict[str, Any]] = None
    options: Dict[str, Any] = Field(default_factory=dict)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/api/health")
def health() -> Dict[str, str]:
    return {"status": "healthy"}


@app.get("/api/schemas")
def schemas() -> Dict[str, Any]:
    return {"schemas": list_schemas()}


@app.get("/api/schemas/{schema_id}")
def schema_detail(schema_id: str) -> Dict[str, Any]:
    try:
        return load_schema_dict(schema_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/examples")
def examples() -> Dict[str, Any]:
    return {"examples": list_examples()}


@app.post("/api/extract")
def extract(request: ExtractRequest) -> Dict[str, Any]:
    try:
        schema = SchemaDefinition.from_dict(request.schema) if request.schema else load_schema(request.schema_id or "stroke_registry_v1")
        options = ExtractionOptions.from_dict(request.options)
        response = engine.extract(schema, request.document, options)
        return response.to_dict()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("medstruct.server:app", host="127.0.0.1", port=8765, reload=True)
