"""Enabler agent — fourth node in the pipeline. Two LLM calls:

  1. For every skill: pick a resource_type (fixed enum) and a concrete topic
     (e.g. a specific doc/course/project idea). The `week` field is NOT
     trusted from the LLM — it's overridden deterministically from
     AgentState.weekly_plan (already decided by the Scheduler), same
     trust-but-verify pattern used elsewhere in the pipeline.
  2. Exactly 3 mock-interview milestones, one per phase, 5 questions each.
     pass_threshold is NOT asked of the LLM — it's hardcoded per phase
     (config.settings.milestone_pass_thresholds: 30/50/65%).

Writes AgentState.resources, .milestones.
"""

from config import settings
from llm_client import call_llm_json
from schemas import AgentState, EnablerMilestoneLLMOutput, EnablerResourceLLMOutput, ResourceType, Skill

PHASE_ORDER = ("Foundation", "Intermediate", "Expert")
PHASE_PASS_THRESHOLD = dict(zip(PHASE_ORDER, settings.milestone_pass_thresholds))

RESOURCE_TYPES_LIST = ", ".join(rt.value for rt in ResourceType)

RESOURCE_PROMPT_TEMPLATE = """You are picking a learning resource for each skill a candidate targeting \
the role "{role_name}" needs to learn.

Skills (name, domain, phase):
{skills_listing}

For EVERY skill listed above (use the exact same name string), pick:
- resource_type: exactly one of: {resource_types}
- topic: a specific, concrete resource pointer or focus area for this skill and resource_type \
(e.g. "Official asyncio documentation", "freeCodeCamp: Python for Everybody", \
"Build a REST API rate limiter" for a project_idea) — not a generic restatement of the skill name.
- week: your best guess for which week (1-6) this fits, though the final week is decided elsewhere.

Return an entry for every single skill listed, with the name spelled exactly as given.
"""

MILESTONE_PROMPT_TEMPLATE = """You are designing 3 mock-interview milestones for a candidate targeting \
the role "{role_name}", one milestone per learning phase.

Foundation-phase skills: {foundation_listing}
Intermediate-phase skills: {intermediate_listing}
Expert-phase skills: {expert_listing}

For each of the 3 phases (Foundation, Intermediate, Expert), write exactly 5 mock interview \
questions that test the skills listed for that phase, increasing in difficulty from Foundation \
to Expert. Return exactly 3 milestones, one per phase, each with exactly 5 questions.
"""


def _skills_listing(skills: list[Skill]) -> str:
    return "\n".join(f"- {s['name']} (domain: {s['domain']}, phase: {s['phase']})" for s in skills)


def _names_by_phase(skills: list[Skill], phase: str) -> str:
    names = [s["name"] for s in skills if s["phase"] == phase]
    return ", ".join(names) if names else "(none)"


def _build_skill_to_week(weekly_plan: dict) -> dict[str, int]:
    skill_to_week: dict[str, int] = {}
    for week, names in weekly_plan.items():
        for name in names:
            skill_to_week[name] = int(week)
    return skill_to_week


def _run_resource_call(role_name: str, skills: list[Skill], skill_to_week: dict[str, int]) -> list[dict]:
    result = call_llm_json(
        RESOURCE_PROMPT_TEMPLATE.format(
            role_name=role_name,
            skills_listing=_skills_listing(skills),
            resource_types=RESOURCE_TYPES_LIST,
        ),
        EnablerResourceLLMOutput,
    )

    valid_names = {s["name"] for s in skills}
    resources: list[dict] = []
    seen: set[str] = set()

    for entry in result["resources"]:
        name = entry["skill"]
        if name not in valid_names or name in seen:
            continue  # ignore hallucinated/duplicate skill names
        seen.add(name)
        resources.append(
            {
                "skill": name,
                "resource_type": entry["resource_type"].value,
                "topic": entry["topic"],
                "week": skill_to_week.get(name, 1),  # trust our own schedule, not the LLM's guess
            }
        )

    # any skill the LLM dropped still needs a resource — default rather than fail the run
    for skill in skills:
        if skill["name"] not in seen:
            resources.append(
                {
                    "skill": skill["name"],
                    "resource_type": ResourceType.OFFICIAL_DOCS.value,
                    "topic": f"Official documentation for {skill['name']}",
                    "week": skill_to_week.get(skill["name"], 1),
                }
            )

    return resources


def _run_milestone_call(role_name: str, skills: list[Skill]) -> list[dict]:
    result = call_llm_json(
        MILESTONE_PROMPT_TEMPLATE.format(
            role_name=role_name,
            foundation_listing=_names_by_phase(skills, "Foundation"),
            intermediate_listing=_names_by_phase(skills, "Intermediate"),
            expert_listing=_names_by_phase(skills, "Expert"),
        ),
        EnablerMilestoneLLMOutput,
    )

    milestones: list[dict] = []
    for entry in result["milestones"]:
        phase = entry["phase"].value
        milestones.append(
            {
                "phase": phase,
                "questions": entry["questions"],
                "pass_threshold": PHASE_PASS_THRESHOLD[phase],
            }
        )
    return milestones


def run_enabler(state: AgentState) -> dict:
    role_name = state["detected_role"]
    skills = state["skills_with_importance"]
    skill_to_week = _build_skill_to_week(state["weekly_plan"])

    resources = _run_resource_call(role_name, skills, skill_to_week)
    milestones = _run_milestone_call(role_name, skills)

    threshold_summary = ", ".join(f"{m['phase']}={m['pass_threshold']:.0%}" for m in milestones)
    log_line = (
        f"[Enabler] {len(resources)} resources assigned, "
        f"{len(milestones)} milestones built (thresholds: {threshold_summary})"
    )

    return {
        "resources": resources,
        "milestones": milestones,
        "agent_logs": state.get("agent_logs", []) + [log_line],
    }
