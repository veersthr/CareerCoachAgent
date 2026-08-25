"""Extractor agent — first node in the pipeline.

Single LLM call: extracts skills (name/domain/frequency/difficulty) from the
JD text. Each extracted skill name is then canonicalized against taxonomy.py
via embeddings.py (cosine >= CANONICALIZATION_THRESHOLD -> canonical name,
else raw string fallback) — this canonicalization step is deterministic
Python, not part of the LLM call. Writes only AgentState.extracted_skills;
no importance_score/phase here — those belong to Role Strategist.
"""

from embeddings import canonicalize_skill
from llm_client import call_llm_json
from schemas import AgentState, Domain, ExtractorLLMOutput, Skill

_DOMAIN_LIST = ", ".join(d.value for d in Domain)

EXTRACTOR_PROMPT_TEMPLATE = """You are analyzing a job description to extract the technical and \
professional skills it requires.

Job Description:
\"\"\"
{jd_text}
\"\"\"

For each distinct skill mentioned or clearly implied, extract:
- name: the skill as written/implied in the JD (do not invent skills that aren't present)
- domain: exactly one of: {domain_list}
- frequency: how many times this skill (or a close synonym) is mentioned/implied in the JD (integer >= 1)
- difficulty: your estimate of how hard this skill is to learn from scratch, from 0.0 (trivial) to 1.0 (expert-level)

Extract every skill you can identify — typically 8 to 20 skills for a normal JD. Do not \
duplicate the same skill under two different names.
"""


def _merge_duplicate_skills(skills: list[Skill]) -> list[Skill]:
    """Merges entries that canonicalized to the same name (e.g. 'Python' and
    'python programming' both -> 'Python'): sums frequency, averages
    difficulty, keeps canonical=True if any duplicate matched. Preserves
    first-seen order."""
    merged: dict[str, Skill] = {}
    order: list[str] = []

    for skill in skills:
        key = skill["name"]
        if key not in merged:
            merged[key] = dict(skill)  # type: ignore[assignment]
            order.append(key)
            continue

        existing = merged[key]
        prev_count = existing.pop("_dup_count", 1)  # type: ignore[misc]
        existing["frequency"] += skill["frequency"]
        existing["difficulty"] = (
            existing["difficulty"] * prev_count + skill["difficulty"]
        ) / (prev_count + 1)
        existing["canonical"] = existing["canonical"] or skill["canonical"]
        existing["_dup_count"] = prev_count + 1  # type: ignore[typeddict-item]

    result = []
    for key in order:
        s = merged[key]
        s.pop("_dup_count", None)  # type: ignore[misc]
        result.append(s)
    return result


def run_extractor(state: AgentState) -> dict:
    jd_text = state["raw_jd_text"]

    result = call_llm_json(
        EXTRACTOR_PROMPT_TEMPLATE.format(jd_text=jd_text, domain_list=_DOMAIN_LIST),
        ExtractorLLMOutput,
    )

    canonicalized_skills: list[Skill] = []
    for raw_skill in result["skills"]:
        canonical_name, is_canonical = canonicalize_skill(raw_skill["name"])
        canonicalized_skills.append(
            Skill(
                name=canonical_name,
                domain=raw_skill["domain"],
                frequency=raw_skill["frequency"],
                difficulty=raw_skill["difficulty"],
                canonical=is_canonical,
                importance_score=None,
                phase=None,
            )
        )

    extracted_skills = _merge_duplicate_skills(canonicalized_skills)
    canon_count = sum(1 for s in extracted_skills if s["canonical"])
    log_line = (
        f"[Extractor] extracted {len(extracted_skills)} skills "
        f"({canon_count} canonicalized, {len(extracted_skills) - canon_count} raw fallback)"
    )

    return {
        "extracted_skills": extracted_skills,
        "agent_logs": state.get("agent_logs", []) + [log_line],
    }
