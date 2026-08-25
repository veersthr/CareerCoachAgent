"""Role Strategist agent — second node in the pipeline.

Role detection is deterministic keyword matching over the JD text (no LLM).
One LLM call then assigns importance_score (0-1) and a Foundation/
Intermediate/Expert phase bucket to each already-extracted skill. The
readiness_score is a deterministic formula in plain Python, not LLM-derived:
100 - (avg_difficulty_in_role_domain * role_weight * READINESS_ROLE_WEIGHT_MULTIPLIER),
capped at READINESS_SCORE_CAP (config.py).

Writes AgentState.detected_role, .skills_with_importance, .readiness_score.
"""

from dataclasses import dataclass

from config import settings
from llm_client import call_llm_json
from schemas import AgentState, Domain, RoleStrategistLLMOutput, Skill


@dataclass(frozen=True)
class RoleDefinition:
    name: str
    keywords: tuple[str, ...]
    primary_domains: tuple[str, ...]  # Domain values this role's core work concentrates in
    role_weight: float  # used in the readiness_score formula


# Order matters only as a tie-breaker (first definition wins ties); keyword
# score is what actually decides the match.
ROLE_DEFINITIONS: tuple[RoleDefinition, ...] = (
    RoleDefinition(
        name="Data Scientist / ML Engineer",
        keywords=(
            "machine learning engineer", "data scientist", "ml engineer",
            "deep learning", "nlp engineer", "computer vision",
        ),
        primary_domains=(Domain.ML_AI.value,),
        role_weight=1.3,
    ),
    RoleDefinition(
        name="Data Engineer",
        keywords=("data engineer", "etl", "data pipeline", "data warehouse", "data platform"),
        primary_domains=(Domain.DATA_ENGINEERING.value,),
        role_weight=1.15,
    ),
    RoleDefinition(
        name="DevOps / Cloud Engineer",
        keywords=(
            "devops", "site reliability", "sre engineer", "cloud engineer",
            "platform engineer", "infrastructure engineer",
        ),
        primary_domains=(Domain.CLOUD_DEVOPS.value,),
        role_weight=1.2,
    ),
    RoleDefinition(
        name="Security Engineer",
        keywords=(
            "security engineer", "application security", "appsec",
            "penetration tester", "cybersecurity",
        ),
        primary_domains=(Domain.SECURITY.value,),
        role_weight=1.25,
    ),
    RoleDefinition(
        name="QA / Test Engineer",
        keywords=(
            "qa engineer", "quality assurance", "test engineer", "sdet",
            "test automation engineer",
        ),
        primary_domains=(Domain.TESTING_QA.value,),
        role_weight=0.8,
    ),
    RoleDefinition(
        name="Full Stack Engineer",
        keywords=("full stack", "full-stack", "fullstack"),
        primary_domains=(Domain.BACKEND.value, Domain.FRONTEND.value),
        role_weight=1.1,
    ),
    RoleDefinition(
        name="Frontend Engineer",
        keywords=(
            "frontend engineer", "front-end engineer", "front end developer", "ui engineer",
        ),
        primary_domains=(Domain.FRONTEND.value,),
        role_weight=0.9,
    ),
    RoleDefinition(
        name="Backend Engineer",
        keywords=(
            "backend engineer", "back-end engineer", "back end developer",
            "server-side engineer", "api engineer",
        ),
        primary_domains=(Domain.BACKEND.value, Domain.DATABASE.value),
        role_weight=1.0,
    ),
    RoleDefinition(
        name="Software Engineer",
        keywords=("software engineer", "software developer", "swe"),
        primary_domains=(),  # generalist: readiness falls back to overall avg difficulty
        role_weight=1.0,
    ),
)

DEFAULT_ROLE = ROLE_DEFINITIONS[-1]  # Software Engineer — used when no keywords match at all


def _detect_role(jd_text: str) -> RoleDefinition:
    text = jd_text.lower()
    best_role = None
    best_score = 0
    for role in ROLE_DEFINITIONS:
        score = sum(text.count(kw) for kw in role.keywords)
        if score > best_score:
            best_score = score
            best_role = role
    return best_role or DEFAULT_ROLE


def _avg_difficulty_for_role(skills: list[Skill], role: RoleDefinition) -> float:
    relevant = [s["difficulty"] for s in skills if s["domain"] in role.primary_domains]
    if not relevant:
        relevant = [s["difficulty"] for s in skills] or [0.5]
    return sum(relevant) / len(relevant)


def _compute_readiness_score(skills: list[Skill], role: RoleDefinition) -> float:
    avg_difficulty = _avg_difficulty_for_role(skills, role)
    raw = 100 - (avg_difficulty * role.role_weight * settings.readiness_role_weight_multiplier)
    return max(0.0, min(raw, settings.readiness_score_cap))


ROLE_STRATEGIST_PROMPT_TEMPLATE = """You are a career coach prioritizing skills for a candidate \
targeting the role: {role_name}.

Here are the skills extracted from the job description (name, domain, difficulty 0-1, mention frequency):
{skills_listing}

For EVERY skill listed above (use the exact same name string), assign:
- importance_score: how critical this skill is for the {role_name} role, from 0.0 (nice-to-have) \
to 1.0 (essential)
- phase: which learning phase this skill belongs in — "Foundation" (learn first, prerequisite-level), \
"Intermediate" (core role skills), or "Expert" (advanced/differentiating skills)

Return an entry for every single skill listed, with the name spelled exactly as given.
"""


def _build_skills_listing(skills: list[Skill]) -> str:
    return "\n".join(
        f"- {s['name']} (domain: {s['domain']}, difficulty: {s['difficulty']:.2f}, "
        f"frequency: {s['frequency']})"
        for s in skills
    )


def run_role_strategist(state: AgentState) -> dict:
    extracted_skills = state["extracted_skills"]
    jd_text = state["raw_jd_text"]

    role = _detect_role(jd_text)
    readiness_score = _compute_readiness_score(extracted_skills, role)

    result = call_llm_json(
        ROLE_STRATEGIST_PROMPT_TEMPLATE.format(
            role_name=role.name, skills_listing=_build_skills_listing(extracted_skills)
        ),
        RoleStrategistLLMOutput,
    )

    llm_by_name = {entry["name"].strip().lower(): entry for entry in result["skills"]}

    skills_with_importance: list[Skill] = []
    unmatched = 0
    for skill in extracted_skills:
        entry = llm_by_name.get(skill["name"].strip().lower())
        updated: Skill = dict(skill)  # type: ignore[assignment]
        if entry is not None:
            updated["importance_score"] = entry["importance_score"]
            updated["phase"] = entry["phase"]
        else:
            # LLM dropped/misspelled a skill name — default rather than fail the run
            unmatched += 1
            updated["importance_score"] = 0.5
            updated["phase"] = "Intermediate"
        skills_with_importance.append(updated)

    log_line = (
        f"[Role Strategist] detected role='{role.name}', readiness_score={readiness_score:.1f}, "
        f"{len(skills_with_importance)} skills scored"
        + (f" ({unmatched} defaulted due to LLM name mismatch)" if unmatched else "")
    )

    return {
        "detected_role": role.name,
        "skills_with_importance": skills_with_importance,
        "readiness_score": readiness_score,
        "agent_logs": state.get("agent_logs", []) + [log_line],
    }
