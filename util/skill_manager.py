from datetime import datetime
import re
import shutil
import tempfile
import threading
import zipfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import numpy as np
import requests

SKILLS_DIR = Path("skills")
MAX_DOWNLOAD_SIZE = 20 * 1024 * 1024
_skill_embedding_cache: dict[str, tuple[float, np.ndarray]] = {}
_skill_embedding_lock = threading.Lock()


@dataclass
class SkillInfo:
    name: str
    directory: str
    skill_file: str
    title: str
    description: str
    updated_at: str | None


def ensure_skills_dir() -> Path:
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    return SKILLS_DIR


def list_installed_skills() -> list[SkillInfo]:
    skills_dir = ensure_skills_dir()
    skills: list[SkillInfo] = []

    for child in sorted(skills_dir.iterdir(), key=lambda item: item.name.lower()):
        if not child.is_dir():
            continue

        skill_file = child / "SKILL.md"
        if not skill_file.exists():
            continue

        title, description = _read_skill_summary(skill_file)
        skills.append(
            SkillInfo(
                name=child.name,
                directory=str(child.resolve()),
                skill_file=str(skill_file.resolve()),
                title=title,
                description=description,
                updated_at=_format_mtime(skill_file),
            )
        )

    return skills


def render_skill_catalog_prompt() -> str:
    skills = list_installed_skills()
    if not skills:
        return ""

    sections = [
        "## Available Skills",
        "Review this catalog first and decide whether the user's request matches any skill.",
        "Only rely on a skill's full instructions when a skill is clearly relevant to the current user request.",
    ]

    for skill in skills:
        sections.append(f"### Skill: {skill.name}")
        sections.append(f"Title: {skill.title}")
        sections.append(f"Description: {skill.description}")

    return "\n\n".join(sections)


def render_relevant_skills_prompt(user_input: str, max_skills: int = 3) -> str:
    matched_skills = select_relevant_skills(user_input=user_input, max_skills=max_skills)
    if not matched_skills:
        return ""

    sections = [
        "## Selected Skill Instructions",
        "The following skills were selected as relevant to the current user request.",
        "Follow them when they materially help with the task, while still obeying your core system instructions.",
    ]

    for skill in matched_skills:
        content = Path(skill.skill_file).read_text(encoding="utf-8").strip()
        sections.append(f"### Skill: {skill.name}")
        sections.append(f"Title: {skill.title}")
        sections.append(content)

    return "\n\n".join(sections)


def select_relevant_skills(user_input: str, max_skills: int = 3) -> list[SkillInfo]:
    query = user_input.strip()
    if not query:
        return []

    semantic_scores = _compute_skill_semantic_scores(query)
    ranked: list[tuple[float, int, SkillInfo]] = []
    for skill in list_installed_skills():
        lexical_score = _score_skill_relevance(skill, query)
        semantic_score = semantic_scores.get(skill.name, 0.0)
        combined_score = lexical_score + max(semantic_score, 0.0) * 100
        if lexical_score >= 10 or (lexical_score > 0 and semantic_score >= 0.28) or semantic_score >= 0.45:
            ranked.append((combined_score, lexical_score, skill))

    ranked.sort(key=lambda item: (-item[0], -item[1], item[2].name.lower()))
    if not ranked:
        return []

    top_score = ranked[0][0]
    min_score = max(18.0, top_score * 0.45)
    return [skill for score, _, skill in ranked if score >= min_score][:max_skills]


def install_skill_from_url(url: str, preferred_name: str | None = None) -> SkillInfo:
    normalized_url = url.strip()
    if not normalized_url:
        raise ValueError("下载链接不能为空")

    ensure_skills_dir()

    with requests.get(normalized_url, stream=True, timeout=30) as response:
        response.raise_for_status()
        content = _read_response_content(response)
        if _looks_like_zip(normalized_url, response.headers, content):
            return install_skill_from_zip_bytes(content, preferred_name or _infer_name_from_url(normalized_url))
        if _looks_like_markdown(normalized_url, response.headers):
            return _install_skill_content(
                content=content,
                preferred_name=preferred_name or _infer_name_from_url(normalized_url),
                content_kind="markdown",
            )

    raise ValueError("当前仅支持 ZIP 压缩包链接或直接指向 SKILL.md 的链接")


def install_skill_from_zip_bytes(content: bytes, preferred_name: str | None = None) -> SkillInfo:
    return _install_skill_content(
        content=content,
        preferred_name=preferred_name or "skill",
        content_kind="zip",
    )


def _install_skill_content(content: bytes, preferred_name: str, content_kind: str) -> SkillInfo:
    target_name = _build_skill_name(preferred_name)
    target_dir = ensure_skills_dir() / target_name
    if target_dir.exists():
        raise FileExistsError(f"技能目录已存在：{target_dir}")

    if content_kind == "zip":
        _install_from_zip_bytes(content, target_dir)
    elif content_kind == "markdown":
        target_dir.mkdir(parents=True, exist_ok=False)
        (target_dir / "SKILL.md").write_bytes(content)
    else:
        raise ValueError("不支持的 skill 内容类型")

    skill_file = target_dir / "SKILL.md"
    if not skill_file.exists():
        shutil.rmtree(target_dir, ignore_errors=True)
        raise ValueError("内容中未找到 SKILL.md，无法识别为有效 skill")

    title, description = _read_skill_summary(skill_file)
    return SkillInfo(
        name=target_dir.name,
        directory=str(target_dir.resolve()),
        skill_file=str(skill_file.resolve()),
        title=title,
        description=description,
        updated_at=_format_mtime(skill_file),
    )


def _read_response_content(response: requests.Response) -> bytes:
    total = 0
    chunks: list[bytes] = []
    for chunk in response.iter_content(chunk_size=8192):
        if not chunk:
            continue
        total += len(chunk)
        if total > MAX_DOWNLOAD_SIZE:
            raise ValueError("下载文件过大，当前限制为 20MB")
        chunks.append(chunk)
    return b"".join(chunks)


def _looks_like_zip(url: str, headers: requests.structures.CaseInsensitiveDict[str], content: bytes) -> bool:
    content_type = headers.get("content-type", "").lower()
    return url.lower().endswith(".zip") or "zip" in content_type or content.startswith(b"PK")


def _looks_like_markdown(url: str, headers: requests.structures.CaseInsensitiveDict[str]) -> bool:
    content_type = headers.get("content-type", "").lower()
    lowered_url = url.lower()
    return lowered_url.endswith((".md", ".markdown", ".txt")) or "text/markdown" in content_type or "text/plain" in content_type


def _install_from_zip_bytes(content: bytes, target_dir: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="skill-download-") as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        archive_path = temp_dir / "skill.zip"
        archive_path.write_bytes(content)

        with zipfile.ZipFile(archive_path) as archive:
            _extract_zip_safely(archive, temp_dir / "extracted")

        extracted_root = temp_dir / "extracted"
        source_dir = _resolve_skill_source_dir(extracted_root)
        shutil.copytree(source_dir, target_dir)


def _extract_zip_safely(archive: zipfile.ZipFile, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    destination_resolved = destination.resolve()

    for member in archive.infolist():
        member_path = destination / member.filename
        resolved_path = member_path.resolve()
        if destination_resolved not in resolved_path.parents and resolved_path != destination_resolved:
            raise ValueError("压缩包包含非法路径，已拒绝安装")

        if member.is_dir():
            resolved_path.mkdir(parents=True, exist_ok=True)
            continue

        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(member) as source, resolved_path.open("wb") as target:
            shutil.copyfileobj(source, target)


def _resolve_skill_source_dir(extracted_root: Path) -> Path:
    direct_skill = extracted_root / "SKILL.md"
    if direct_skill.exists():
        return extracted_root

    direct_children = [child for child in extracted_root.iterdir() if child.is_dir()]
    if len(direct_children) == 1 and (direct_children[0] / "SKILL.md").exists():
        return direct_children[0]

    matches = list(extracted_root.rglob("SKILL.md"))
    if len(matches) != 1:
        raise ValueError("压缩包中需要包含且仅包含一个 SKILL.md")

    return matches[0].parent


def _infer_name_from_url(url: str) -> str:
    parsed = urlparse(url)
    candidate = Path(parsed.path).name
    if candidate.lower().endswith(".zip"):
        candidate = candidate[:-4]
    elif "." in candidate:
        candidate = candidate.rsplit(".", 1)[0]
    return candidate or "skill"


def _build_skill_name(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip()).strip("-_").lower()
    return cleaned or "skill"


def _read_skill_summary(skill_file: Path) -> tuple[str, str]:
    content = skill_file.read_text(encoding="utf-8")
    title = skill_file.parent.name
    description = "暂无描述"

    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            title = stripped[2:].strip() or title
            continue
        if stripped:
            description = stripped[:180]
            break

    return title, description


def _score_skill_relevance(skill: SkillInfo, user_input: str) -> int:
    query_tokens = _extract_query_tokens(user_input)
    if not query_tokens:
        return 0

    skill_content = Path(skill.skill_file).read_text(encoding="utf-8").lower()
    name_text = f"{skill.name} {skill.name.replace('-', ' ').replace('_', ' ')}".lower()
    title_text = skill.title.lower()
    description_text = skill.description.lower()

    score = 0
    for token in query_tokens:
        token_score = 0

        if token in name_text:
            token_score += 12 + min(len(token), 8)
        if token in title_text:
            token_score += 9 + min(len(token), 6)
        if token in description_text:
            token_score += 6 + min(len(token), 6)
        if token in skill_content:
            token_score += 3 + min(len(token), 5)

        score += token_score

    lowered_query = user_input.lower()
    if skill.name.lower() in lowered_query:
        score += 24
    if skill.title and skill.title.lower() in lowered_query:
        score += 20

    return score


def _extract_query_tokens(text: str) -> list[str]:
    normalized = text.lower()
    raw_tokens = re.findall(r"[a-z0-9_-]{2,}|[\u4e00-\u9fff]{2,}", normalized)
    tokens: list[str] = []
    seen: set[str] = set()

    for raw in raw_tokens:
        for token in _expand_token(raw):
            if len(token) < 2:
                continue
            if token in seen:
                continue
            seen.add(token)
            tokens.append(token)

    return tokens


def _expand_token(token: str) -> list[str]:
    expanded = [token]
    if "-" in token or "_" in token:
        expanded.extend(part for part in re.split(r"[-_]+", token) if len(part) >= 2)
    return expanded


def _compute_skill_semantic_scores(query: str) -> dict[str, float]:
    try:
        from util.embeddings_models import get_embeddings
    except Exception:
        return {}

    try:
        embeddings = get_embeddings()
        query_vector = np.array(embeddings.embed_query(query), dtype=float)
        if query_vector.size == 0:
            return {}
    except Exception:
        return {}

    scores: dict[str, float] = {}
    for skill in list_installed_skills():
        skill_vector = _get_skill_embedding(skill, embeddings)
        if skill_vector is None or skill_vector.shape != query_vector.shape:
            continue
        scores[skill.name] = float(np.dot(query_vector, skill_vector))
    return scores


def _get_skill_embedding(skill: SkillInfo, embeddings) -> np.ndarray | None:
    skill_path = Path(skill.skill_file)
    cache_key = str(skill_path.resolve())
    mtime = skill_path.stat().st_mtime

    with _skill_embedding_lock:
        cached = _skill_embedding_cache.get(cache_key)
        if cached and cached[0] == mtime:
            return cached[1]

    try:
        text = _build_skill_embedding_text(skill)
        vector = np.array(embeddings.embed_query(text), dtype=float)
    except Exception:
        return None

    with _skill_embedding_lock:
        _skill_embedding_cache[cache_key] = (mtime, vector)
    return vector


def _build_skill_embedding_text(skill: SkillInfo) -> str:
    content = Path(skill.skill_file).read_text(encoding="utf-8").strip()
    return "\n".join(
        [
            f"Skill Name: {skill.name}",
            f"Skill Title: {skill.title}",
            f"Skill Description: {skill.description}",
            content[:4000],
        ]
    )


def _format_mtime(path: Path) -> str | None:
    if not path.exists():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime).isoformat(sep=" ", timespec="seconds")
