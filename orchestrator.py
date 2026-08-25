"""Orchestrator — not a graph node. Runs after graph.invoke() returns: builds
the final Markdown report from AgentState and persists the whole session
(state + report) to outputs/{session_id}.json. api.py's GET /session/{id}
reads sessions back via load_session().
"""

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import quote_plus

from config import settings
from schemas import AgentState

_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _generate_session_id() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{timestamp}_{uuid.uuid4().hex[:8]}"


def _session_path(session_id: str) -> Optional[Path]:
    """Returns the on-disk path for a session id, or None if the id isn't a
    safe filename (guards load_session against path traversal since
    session_id can come from a user-supplied API path parameter)."""
    if not _SESSION_ID_RE.fullmatch(session_id):
        return None
    return settings.outputs_dir / f"{session_id}.json"


PHASE_ORDER = ("Foundation", "Intermediate", "Expert")
PHASE_WEEK_LABEL = {"Foundation": "Weeks 1-2", "Intermediate": "Weeks 3-4", "Expert": "Weeks 5-6"}

# Resource topics/URLs are never asked of the LLM (it would hallucinate dead links) — a
# search-engine link is built deterministically from resource_type + topic instead, so
# it's always valid even if it isn't a single canonical source.
RESOURCE_TYPE_LABEL = {
    "official_docs": "Official Docs",
    "video_course": "Video Course",
    "practice_platform": "Practice Platform",
    "book_chapter": "Book Chapter",
    "project_idea": "Project Idea",
}


def _escape_md_cell(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ").strip()


def _resource_link(resource_type: str, topic: str) -> str | None:
    query = quote_plus(topic)
    if resource_type == "video_course":
        return f"https://www.youtube.com/results?search_query={query}"
    if resource_type == "project_idea":
        return None  # nothing to link to — it's a build-it-yourself prompt
    if resource_type == "book_chapter":
        return f"https://www.google.com/search?q={query}&tbm=bks"
    # official_docs, practice_platform, and any future type
    return f"https://www.google.com/search?q={query}"


def _group_skills_by_phase(skills: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {p: [] for p in PHASE_ORDER}
    for skill in skills:
        phase = skill.get("phase")
        if phase in grouped:
            grouped[phase].append(skill)
    return grouped


def _format_skills_section(skills: list[dict]) -> str:
    grouped = _group_skills_by_phase(skills)
    lines = ["## Skills by Phase", ""]
    for phase in PHASE_ORDER:
        lines.append(f"### {phase} ({PHASE_WEEK_LABEL[phase]})")
        lines.append("")
        phase_skills = sorted(grouped[phase], key=lambda s: s.get("importance_score") or 0, reverse=True)
        if not phase_skills:
            lines.append("_(none)_")
            lines.append("")
            continue
        lines.append("| Skill | Importance | Difficulty | Domain |")
        lines.append("|---|---|---|---|")
        for s in phase_skills:
            importance = s.get("importance_score")
            importance_str = f"{importance:.0%}" if importance is not None else "n/a"
            lines.append(
                f"| {_escape_md_cell(s['name'])} | {importance_str} | "
                f"{s['difficulty']:.0%} | {_escape_md_cell(s['domain'])} |"
            )
        lines.append("")
    return "\n".join(lines)


def _format_weekly_plan_section(weekly_plan: dict) -> str:
    lines = ["## Weekly Plan", ""]
    for week in range(1, 7):
        skills = weekly_plan.get(week) or weekly_plan.get(str(week)) or []
        skills_str = ", ".join(skills) if skills else "_(none)_"
        lines.append(f"- **Week {week}:** {skills_str}")
    lines.append("")
    return "\n".join(lines)


def _format_resources_section(resources: list[dict]) -> str:
    lines = ["## Learning Resources", "", "| Week | Skill | Type | Topic | Link |", "|---|---|---|---|---|"]
    for r in sorted(resources, key=lambda r: r["week"]):
        type_label = RESOURCE_TYPE_LABEL.get(r["resource_type"], r["resource_type"])
        link = _resource_link(r["resource_type"], r["topic"])
        link_cell = f"[Search]({link})" if link else "_(n/a)_"
        lines.append(
            f"| {r['week']} | {_escape_md_cell(r['skill'])} | {type_label} | "
            f"{_escape_md_cell(r['topic'])} | {link_cell} |"
        )
    lines.append("")
    return "\n".join(lines)


def _format_gantt_section(gantt_mermaid: str) -> str:
    return "\n".join(["## Gantt Chart", "", "```mermaid", gantt_mermaid.rstrip(), "```", ""])


def _format_milestones_section(milestones: list[dict]) -> str:
    lines = ["## Mock Interview Milestones", ""]
    by_phase = {m["phase"]: m for m in milestones}
    for phase in PHASE_ORDER:
        m = by_phase.get(phase)
        if not m:
            continue
        lines.append(f"### {phase} Milestone (pass threshold: {m['pass_threshold']:.0%})")
        for i, q in enumerate(m["questions"], start=1):
            lines.append(f"{i}. {q}")
        lines.append("")
    return "\n".join(lines)


def _format_agent_log_section(agent_logs: list[str]) -> str:
    lines = ["## Agent Execution Log", ""]
    lines.extend(f"- {line}" for line in agent_logs)
    lines.append("")
    return "\n".join(lines)


def build_markdown_report(state: AgentState, session_id: str) -> str:
    role = state.get("detected_role", "Unknown Role")
    readiness = state.get("readiness_score")
    readiness_str = f"{readiness:.0f}/100" if readiness is not None else "n/a"

    sections = [f"# Career Roadmap Report — {role}", "", f"**Readiness Score:** {readiness_str}", ""]

    if state.get("partial_output"):
        errors = state.get("validation_errors") or []
        sections.append(
            "> **Note:** This report was generated with partial validation. Some checks "
            "failed after all retries were exhausted:\n>\n"
            + "\n".join(f"> - {e}" for e in errors)
        )
        sections.append("")

    sections.append(_format_skills_section(state.get("skills_with_importance") or []))
    sections.append(_format_weekly_plan_section(state.get("weekly_plan") or {}))
    sections.append(_format_resources_section(state.get("resources") or []))
    sections.append(_format_gantt_section(state.get("gantt_mermaid") or ""))
    sections.append(_format_milestones_section(state.get("milestones") or []))
    sections.append(_format_agent_log_section(state.get("agent_logs") or []))
    sections.append(f"---\n_Session ID: `{session_id}`_")

    return "\n".join(sections)


def _save_session(session_id: str, report_markdown: str, state: AgentState) -> None:
    path = settings.outputs_dir / f"{session_id}.json"
    payload = {
        "session_id": session_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "detected_role": state.get("detected_role"),
        "partial_output": state.get("partial_output", False),
        "report_markdown": report_markdown,
        "state": state,
    }
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def run_orchestrator(final_state: AgentState) -> dict:
    """Called by api.py right after graph.invoke() returns. Builds the
    Markdown report, persists the session to disk, and returns both plus
    the session_id."""
    session_id = _generate_session_id()
    report_markdown = build_markdown_report(final_state, session_id)
    _save_session(session_id, report_markdown, final_state)
    return {"session_id": session_id, "report_markdown": report_markdown, "state": final_state}


def load_session(session_id: str) -> Optional[dict]:
    """Reads a previously-saved session back from disk. Returns None if the
    session_id is invalid or no such session exists — api.py should map
    that to a 404."""
    path = _session_path(session_id)
    if path is None or not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
