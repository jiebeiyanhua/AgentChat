from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from util.knowledge_base import (
    list_knowledge_sources,
    store_uploaded_knowledge,
    sync_definition_source,
)

router = APIRouter()
definition_dir = Path("definition")
definition_files = {
    "IDENTITY": definition_dir / "IDENTITY.md",
    "SOUL": definition_dir / "SOUL.md",
    "USER": definition_dir / "USER.md",
}
knowledge_backed_definitions = {"SOUL", "USER"}


class DefinitionPayload(BaseModel):
    content: str


@router.get("/definitions")
async def get_definitions():
    result = {}
    for key, path in definition_files.items():
        result[key] = path.read_text(encoding="utf-8") if path.exists() else ""
    return result


@router.put("/definitions/{definition_name}")
async def save_definition(definition_name: str, payload: DefinitionPayload):
    definition_key = definition_name.upper()
    target_file = definition_files.get(definition_key)
    if target_file is None:
        raise HTTPException(status_code=404, detail="Definition file not found")

    target_file.write_text(payload.content, encoding="utf-8")

    knowledge_sync = None
    if definition_key in knowledge_backed_definitions:
        knowledge_sync = sync_definition_source(definition_key, target_file)

    return {
        "name": definition_key,
        "saved": True,
        "knowledge_sync": knowledge_sync,
    }


@router.get("/knowledge-sources")
async def get_knowledge_sources():
    return {
        "sources": [
            {
                "source_key": item.source_key,
                "source_name": item.source_name,
                "source_type": item.source_type,
                "file_path": item.file_path,
                "chunk_count": item.chunk_count,
                "updated_at": item.updated_at,
            }
            for item in list_knowledge_sources()
        ]
    }


@router.post("/knowledge-sources/upload")
async def upload_knowledge_file(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    content = await file.read()
    try:
        result = store_uploaded_knowledge(file.filename, content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return result
