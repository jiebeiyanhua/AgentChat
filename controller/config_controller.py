from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from util.config import get_config_path, load_config, reload_config, save_config
from util.knowledge_base import (
    list_knowledge_sources,
    store_uploaded_knowledge,
    sync_definition_source,
)
from util.mcp_manager import mcp_manager
from util.skill_manager import (
    ensure_skills_dir,
    install_skill_from_url,
    install_skill_from_zip_bytes,
    list_installed_skills,
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


class McpConfigPayload(BaseModel):
    config: dict


class SkillInstallPayload(BaseModel):
    url: str
    name: str | None = None


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
                "description": item.description,
                "chunk_count": item.chunk_count,
                "updated_at": item.updated_at,
            }
            for item in list_knowledge_sources()
        ]
    }


@router.post("/knowledge-sources/upload")
async def upload_knowledge_file(file: UploadFile = File(...), description: str | None = Form(default=None)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    content = await file.read()
    try:
        result = store_uploaded_knowledge(file.filename, content, description=description)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return result


@router.get("/mcp/servers")
async def get_mcp_servers():
    return {"servers": mcp_manager.get_server_statuses()}


@router.get("/mcp/config")
async def get_mcp_config():
    return {
        "config_path": str(get_config_path()),
        "config": load_config().get("mcp", {"fail_fast": False, "servers": []}),
    }


@router.put("/mcp/config")
async def save_mcp_config(payload: McpConfigPayload):
    try:
        mcp_manager.parse_server_configs(payload.config.get("servers", []))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    current_config = load_config()
    next_config = dict(current_config)
    next_config["mcp"] = payload.config

    try:
        save_config(next_config)
        mcp_manager.reload()
    except Exception as exc:
        save_config(current_config)
        reload_config()
        mcp_manager.reload()
        raise HTTPException(status_code=500, detail=f"MCP 配置保存失败：{exc}") from exc

    return {
        "saved": True,
        "config_path": str(get_config_path()),
        "config": payload.config,
        "servers": mcp_manager.get_server_statuses(),
    }


@router.get("/skills")
async def get_skills():
    ensure_skills_dir()
    return {
        "skills_dir": str(ensure_skills_dir().resolve()),
        "skills": [
            {
                "name": item.name,
                "directory": item.directory,
                "skill_file": item.skill_file,
                "title": item.title,
                "description": item.description,
                "updated_at": item.updated_at,
            }
            for item in list_installed_skills()
        ],
    }


@router.post("/skills/install")
async def install_skill(payload: SkillInstallPayload):
    try:
        skill = install_skill_from_url(payload.url, payload.name)
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"技能下载失败：{exc}") from exc

    return {
        "installed": True,
        "skill": {
            "name": skill.name,
            "directory": skill.directory,
            "skill_file": skill.skill_file,
            "title": skill.title,
            "description": skill.description,
            "updated_at": skill.updated_at,
        },
    }


@router.post("/skills/upload")
async def upload_skill_zip(file: UploadFile = File(...), name: str | None = Form(default=None)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    if not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="当前仅支持上传 ZIP 压缩包")

    content = await file.read()
    try:
        skill = install_skill_from_zip_bytes(content, name or Path(file.filename).stem)
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"技能上传失败：{exc}") from exc

    return {
        "installed": True,
        "skill": {
            "name": skill.name,
            "directory": skill.directory,
            "skill_file": skill.skill_file,
            "title": skill.title,
            "description": skill.description,
            "updated_at": skill.updated_at,
        },
    }

