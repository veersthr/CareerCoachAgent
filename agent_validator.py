"""Validator agent — fifth and final node in the pipeline. No LLM call: 10
independent rule-based checks re-verify the final AgentState, regardless of
what upstream agents already claim to have guaranteed (defense in depth).

On failure: if retry_count < settings.max_retries, increments retry_count and
routes back to the Extractor (graph.py wires this edge). Once retries are
exhausted, force-passes with partial_output=True so the pipeline always
terminates with a report rather than looping forever.

Writes AgentState.validation_passed, .validation_errors, .retry_count,
.partial_output.
"""

from config import settings
from schemas import AgentState, Phase

MIN_SKILL_COUNT = 3
EXPECTED_WEEKS = set(range(1, 7))
VALID_PHASES = {p.value for p in Phase}


def _check_skill_count(state: AgentState) -> str | None:
    skills = state.get("skills_with_importance") or []
    if len(skills) < MIN_SKILL_COUNT:
        return f"skill count too low: {len(skills)} < minimum {MIN_SKILL_COUNT}"
    return None


def _check_role_detected(state: AgentState) -> str | None:
    role = state.get("detected_role")
    if not role or not str(role).strip():
        return "no role detected (detected_role is empty)"
    return None


def _check_phases_populated(state: AgentState) -> str | None:
    skills = state.get("skills_with_importance") or []
    present = {s.get("phase") for s in skills}
    missing = VALID_PHASES - present
    if missing:
        return f"phase(s) with zero skills: {sorted(missing)}"
    return None


def _check_all_weeks_present(state: AgentState) -> str | None:
    weekly_plan = state.get("weekly_plan") or {}
    weeks = {int(w) for w in weekly_plan.keys()}
    missing = EXPECTED_WEEKS - weeks
    if missing:
        return f"weekly_plan missing week(s): {sorted(missing)}"
    return None


def _check_resources_exist(state: AgentState) -> str | None:
    resources = state.get("resources") or []
    if not resources:
        return "no resources assigned"
    skills = state.get("skills_with_importance") or []
    skill_names = {s["name"] for s in skills}
    resourced_names = {r["skill"] for r in resources}
    missing = skill_names - resourced_names
    if missing:
        return f"skill(s) missing a resource: {sorted(missing)}"
    return None


def _check_exactly_three_milestones(state: AgentState) -> str | None:
    milestones = state.get("milestones") or []
    if len(milestones) != 3:
        return f"expected exactly 3 milestones, got {len(milestones)}"
    phases = [m.get("phase") for m in milestones]
    if set(phases) != VALID_PHASES:
        return f"milestones must cover all 3 phases exactly once, got {phases}"
    for m in milestones:
        n_questions = len(m.get("questions") or [])
        if n_questions != 5:
            return f"milestone for phase {m.get('phase')} must have exactly 5 questions, got {n_questions}"
    return None


def _check_gantt_sanity(state: AgentState) -> str | None:
    gantt = state.get("gantt_mermaid") or ""
    if not gantt.strip().startswith("gantt"):
        return "gantt_mermaid does not start with a valid mermaid 'gantt' directive"
    week_sections = gantt.count("section Week")
    if week_sections != 6:
        return f"gantt_mermaid should have 6 week sections, found {week_sections}"
    return None


def _check_readiness_range(state: AgentState) -> str | None:
    score = state.get("readiness_score")
    if score is None or not (0 <= score <= 100):
        return f"readiness_score out of [0,100] range: {score}"
    return None


def _check_no_duplicate_skills(state: AgentState) -> str | None:
    skills = state.get("skills_with_importance") or []
    names = [s["name"] for s in skills]
    dupes = sorted({n for n in names if names.count(n) > 1})
    if dupes:
        return f"duplicate skill name(s): {dupes}"
    return None


def _check_every_skill_has_importance_score(state: AgentState) -> str | None:
    skills = state.get("skills_with_importance") or []
    missing = [
        s["name"]
        for s in skills
        if s.get("importance_score") is None or not (0 <= s["importance_score"] <= 1)
    ]
    if missing:
        return f"skill(s) missing/invalid importance_score: {missing}"
    return None


_CHECKS = (
    ("skill_count", _check_skill_count),
    ("role_detected", _check_role_detected),
    ("phases_populated", _check_phases_populated),
    ("all_weeks_present", _check_all_weeks_present),
    ("resources_exist", _check_resources_exist),
    ("exactly_three_milestones", _check_exactly_three_milestones),
    ("gantt_sanity", _check_gantt_sanity),
    ("readiness_range", _check_readiness_range),
    ("no_duplicate_skills", _check_no_duplicate_skills),
    ("every_skill_has_importance_score", _check_every_skill_has_importance_score),
)


def _run_all_checks(state: AgentState) -> list[str]:
    errors = []
    for name, check_fn in _CHECKS:
        result = check_fn(state)
        if result:
            errors.append(f"[{name}] {result}")
    return errors


def run_validator(state: AgentState) -> dict:
    errors = _run_all_checks(state)
    retry_count = state.get("retry_count", 0)

    if not errors:
        log_line = f"[Validator] passed all {len(_CHECKS)} checks"
        return {
            "validation_passed": True,
            "validation_errors": [],
            "retry_count": retry_count,
            "partial_output": False,
            "agent_logs": state.get("agent_logs", []) + [log_line],
        }

    error_summary = "; ".join(errors)

    if retry_count < settings.max_retries:
        new_retry_count = retry_count + 1
        log_line = (
            f"[Validator] failed {len(errors)}/{len(_CHECKS)} checks "
            f"(retry {new_retry_count}/{settings.max_retries}): {error_summary}"
        )
        return {
            "validation_passed": False,
            "validation_errors": errors,
            "retry_count": new_retry_count,
            "partial_output": False,
            "agent_logs": state.get("agent_logs", []) + [log_line],
        }

    # retries exhausted — force-pass so the pipeline always terminates
    log_line = (
        f"[Validator] failed {len(errors)}/{len(_CHECKS)} checks after {retry_count} "
        f"retries — forcing pass with partial_output=True: {error_summary}"
    )
    return {
        "validation_passed": True,
        "validation_errors": errors,
        "retry_count": retry_count,
        "partial_output": True,
        "agent_logs": state.get("agent_logs", []) + [log_line],
    }
