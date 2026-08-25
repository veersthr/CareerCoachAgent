"""Scheduler agent — third node in the pipeline.

One LLM call distributes each already-phased skill (Foundation/Intermediate/
Expert, set by Role Strategist) across specific weeks within its phase's
2-week window (Foundation -> weeks 1-2, Intermediate -> weeks 3-4,
Expert -> weeks 5-6). Any skill the LLM misassigns outside its phase's window
is deterministically corrected in plain Python.

The Gantt chart (Mermaid syntax) is then built entirely deterministically:
start date aligned to the next Monday, one 5-weekday (Mon-Fri) bar per skill
per week — never touching a weekend.

Writes AgentState.weekly_plan, .gantt_mermaid.
"""

from datetime import date, timedelta

from llm_client import call_llm_json
from schemas import AgentState, SchedulerLLMOutput, Skill

PHASE_WEEK_RANGE = {
    "Foundation": (1, 2),
    "Intermediate": (3, 4),
    "Expert": (5, 6),
}

WEEK_PHASE = {
    1: "Foundation", 2: "Foundation",
    3: "Intermediate", 4: "Intermediate",
    5: "Expert", 6: "Expert",
}

SCHEDULER_PROMPT_TEMPLATE = """You are building a 6-week learning schedule for a candidate targeting \
the role: {role_name}.

Skills by phase (already bucketed):

Foundation (must be scheduled in week 1 or week 2 only):
{foundation_listing}

Intermediate (must be scheduled in week 3 or week 4 only):
{intermediate_listing}

Expert (must be scheduled in week 5 or week 6 only):
{expert_listing}

Distribute every skill listed above into its correct week, balancing the workload \
reasonably across the two weeks available in each phase (e.g. don't put everything in \
week 1 and leave week 2 empty). Return a "weekly_plan" covering all 6 weeks (weeks with \
no skills should still appear with an empty skills list). Use the exact skill name \
strings given above.
"""


def _listing(names: list[str]) -> str:
    return "\n".join(f"- {n}" for n in names) if names else "(none)"


def _reconcile_weekly_plan(
    llm_weekly_plan: list[dict], skills_with_importance: list[Skill]
) -> dict[int, list[str]]:
    """Ensures every skill appears exactly once, in a week within its phase's
    allowed range. Skills the LLM dropped or misassigned outside their
    phase's window are deterministically placed, alternating between the
    phase's two weeks to balance load."""
    phase_of = {s["name"]: s["phase"] for s in skills_with_importance}

    llm_week_by_name: dict[str, int] = {}
    for week_entry in llm_weekly_plan:
        for name in week_entry["skills"]:
            if name in phase_of:  # ignore hallucinated names not in our skill set
                llm_week_by_name[name] = week_entry["week"]

    final: dict[int, list[str]] = {w: [] for w in range(1, 7)}
    phase_counters: dict[str, int] = {"Foundation": 0, "Intermediate": 0, "Expert": 0}

    for skill in skills_with_importance:
        name = skill["name"]
        phase = skill["phase"]
        w_start, w_end = PHASE_WEEK_RANGE[phase]

        candidate_week = llm_week_by_name.get(name)
        if candidate_week is not None and w_start <= candidate_week <= w_end:
            week = candidate_week
        else:
            # LLM dropped this skill or put it outside its phase's window —
            # deterministically alternate between the phase's two weeks
            idx = phase_counters[phase]
            week = w_start if idx % 2 == 0 else w_end
            phase_counters[phase] += 1

        final[week].append(name)

    return final


def _next_monday(today: date) -> date:
    offset = (7 - today.weekday()) % 7  # Monday=0 ... Sunday=6
    return today + timedelta(days=offset)


def _sanitize_label(name: str) -> str:
    return name.replace(":", "-").replace(",", " ").replace(";", " ")


def build_gantt_mermaid(weekly_plan: dict[int, list[str]], role_name: str) -> str:
    """Deterministically builds a Mermaid gantt chart: one 5-weekday
    (Mon-Fri) bar per skill, week N starting on the Nth Monday from the next
    upcoming Monday. Never spans a weekend."""
    start_monday = _next_monday(date.today())

    lines = [
        "gantt",
        f"    title 6-Week Learning Roadmap - {role_name}",
        "    dateFormat  YYYY-MM-DD",
        "    excludes    weekends",
        "",
    ]

    task_counter = 0
    for week in range(1, 7):
        week_start = start_monday + timedelta(weeks=week - 1)
        phase = WEEK_PHASE[week]
        lines.append(f"    section Week {week} ({phase})")
        skills = weekly_plan.get(week, [])
        if not skills:
            lines.append(f"    (no skills scheduled)  :milestone, m{week}, {week_start.isoformat()}, 0d")
        for skill_name in skills:
            task_counter += 1
            task_id = f"t{task_counter}"
            label = _sanitize_label(skill_name)
            lines.append(f"    {label}           :{task_id}, {week_start.isoformat()}, 5d")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def run_scheduler(state: AgentState) -> dict:
    role_name = state["detected_role"]
    skills = state["skills_with_importance"]

    foundation = [s["name"] for s in skills if s["phase"] == "Foundation"]
    intermediate = [s["name"] for s in skills if s["phase"] == "Intermediate"]
    expert = [s["name"] for s in skills if s["phase"] == "Expert"]

    result = call_llm_json(
        SCHEDULER_PROMPT_TEMPLATE.format(
            role_name=role_name,
            foundation_listing=_listing(foundation),
            intermediate_listing=_listing(intermediate),
            expert_listing=_listing(expert),
        ),
        SchedulerLLMOutput,
    )

    weekly_plan = _reconcile_weekly_plan(result["weekly_plan"], skills)
    gantt_mermaid = build_gantt_mermaid(weekly_plan, role_name)

    log_line = (
        f"[Scheduler] weekly_plan built for weeks 1-6 "
        f"({sum(len(v) for v in weekly_plan.values())} skills scheduled), "
        f"gantt starts {_next_monday(date.today()).isoformat()}"
    )

    return {
        "weekly_plan": weekly_plan,
        "gantt_mermaid": gantt_mermaid,
        "agent_logs": state.get("agent_logs", []) + [log_line],
    }
