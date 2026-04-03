from pathlib import Path

from langchain_core.tools import tool

from util.skill_manager import list_installed_skills


@tool
def get_skill_list() -> str:
    """查询当前可用的 Skills 列表。"""
    skills = list_installed_skills()
    if not skills:
        return "当前没有可用的 Skills。"

    lines = ["当前可用的 Skills 列表："]
    for item in skills:
        lines.append(f"- name={item.name}")
    return "\n".join(lines)


@tool
def get_skill_detail(skill_name: str) -> str:
    """查询指定 Skill 的描述与完整说明。在使用某个 Skill 前应先使用此工具。"""
    target = (skill_name or "").strip().lower()
    if not target:
        return "请提供 Skill 名称。"

    for item in list_installed_skills():
        if item.name.lower() != target:
            continue

        content = Path(item.skill_file).read_text(encoding="utf-8").strip()
        return "\n".join(
            [
                f"name: {item.name}",
                f"title: {item.title}",
                f"description: {item.description}",
                "content:",
                content,
            ]
        )

    return f"未找到 Skill {skill_name}。"
