"""Single shared contract for the whole pipeline.

Every agent file imports from here. Field ownership (see plan.md) is enforced by
convention, not by the type system: each agent node writes only the fields listed
as "owned" by it below.
"""

from enum import Enum
from typing import Optional, TypedDict

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Domain(str, Enum):
    PROGRAMMING_LANGUAGE = "programming_language"
    FRONTEND = "frontend"
    BACKEND = "backend"
    DATABASE = "database"
    CLOUD_DEVOPS = "cloud_devops"
    ML_AI = "ml_ai"
    DATA_ENGINEERING = "data_engineering"
    TESTING_QA = "testing_qa"
    SECURITY = "security"
    TOOLS_OTHER = "tools_other"
    SOFT_SKILL = "soft_skill"


class Phase(str, Enum):
    FOUNDATION = "Foundation"
    INTERMEDIATE = "Intermediate"
    EXPERT = "Expert"


class ResourceType(str, Enum):
    OFFICIAL_DOCS = "official_docs"
    VIDEO_COURSE = "video_course"
    PRACTICE_PLATFORM = "practice_platform"
    BOOK_CHAPTER = "book_chapter"
    PROJECT_IDEA = "project_idea"


# ---------------------------------------------------------------------------
# Core data records (shared shapes used inside AgentState)
# ---------------------------------------------------------------------------

class Skill(TypedDict):
    name: str                       # canonicalized name, or raw string if below threshold
    domain: str                     # Domain value
    frequency: int                  # mentions in JD
    difficulty: float               # 0-1, set by Extractor
    canonical: bool                 # True if matched taxonomy at >=0.75 cosine sim
    importance_score: Optional[float]   # 0-1 — ONLY Role Strategist writes this
    phase: Optional[str]                # Phase value — ONLY Role Strategist writes this


class Resource(TypedDict):
    skill: str
    resource_type: str              # ResourceType value
    topic: str
    week: int                       # 1-6


class Milestone(TypedDict):
    phase: str                      # Phase value
    questions: list                 # list[str], exactly 5
    pass_threshold: float           # hardcoded per phase: 0.30 / 0.50 / 0.65


# ---------------------------------------------------------------------------
# AgentState — the LangGraph shared state
# ---------------------------------------------------------------------------

class AgentState(TypedDict, total=False):
    # input
    raw_jd_text: str

    # Extractor-owned
    extracted_skills: list          # list[Skill]

    # Role Strategist-owned
    detected_role: str
    skills_with_importance: list    # list[Skill], supersedes extracted_skills downstream
    readiness_score: float          # 0-100

    # Scheduler-owned
    weekly_plan: dict               # dict[int, list[str]] -> week number to skill names
    gantt_mermaid: str

    # Enabler-owned
    resources: list                 # list[Resource]
    milestones: list                # list[Milestone], exactly 3

    # Validator-owned
    validation_passed: bool
    validation_errors: list         # list[str]
    retry_count: int
    partial_output: bool

    # cross-cutting: every agent appends one line here
    agent_logs: list                # list[str]


# ---------------------------------------------------------------------------
# Per-LLM-call I/O schemas — used to validate json.loads() output before it is
# written into AgentState. One schema per LLM call in the pipeline.
# ---------------------------------------------------------------------------

class ExtractedSkillLLM(BaseModel):
    name: str
    domain: str
    frequency: int = Field(ge=1)
    difficulty: float = Field(ge=0, le=1)


class ExtractorLLMOutput(BaseModel):
    """Output of Extractor's single LLM call. No importance_score here."""
    skills: list[ExtractedSkillLLM]


class RoleStrategistSkillLLM(BaseModel):
    name: str                       # must match a name from ExtractorLLMOutput
    importance_score: float = Field(ge=0, le=1)
    phase: Phase


class RoleStrategistLLMOutput(BaseModel):
    """Output of Role Strategist's single LLM call. Role detection itself is
    deterministic Python, not part of this schema."""
    skills: list[RoleStrategistSkillLLM]


class WeekPlanLLM(BaseModel):
    week: int = Field(ge=1, le=6)
    skills: list[str]


class SchedulerLLMOutput(BaseModel):
    """Output of Scheduler's single LLM call. Gantt chart itself is built
    deterministically in Python, not by the LLM."""
    weekly_plan: list[WeekPlanLLM]

    @field_validator("weekly_plan")
    @classmethod
    def all_six_weeks_present(cls, v: list[WeekPlanLLM]) -> list[WeekPlanLLM]:
        weeks = {w.week for w in v}
        if weeks != set(range(1, 7)):
            raise ValueError(f"weekly_plan must cover weeks 1-6, got {sorted(weeks)}")
        return v


class EnablerResourceLLM(BaseModel):
    skill: str
    resource_type: ResourceType
    topic: str
    week: int = Field(ge=1, le=6)


class EnablerResourceLLMOutput(BaseModel):
    """Output of Enabler's first LLM call (resource assignment)."""
    resources: list[EnablerResourceLLM]


class EnablerMilestoneLLM(BaseModel):
    phase: Phase
    questions: list[str]

    @field_validator("questions")
    @classmethod
    def exactly_five_questions(cls, v: list[str]) -> list[str]:
        if len(v) != 5:
            raise ValueError(f"each milestone must have exactly 5 questions, got {len(v)}")
        return v


class EnablerMilestoneLLMOutput(BaseModel):
    """Output of Enabler's second LLM call (mock interview milestones).
    pass_threshold is NOT part of this schema — it's hardcoded per phase in code."""
    milestones: list[EnablerMilestoneLLM]

    @field_validator("milestones")
    @classmethod
    def exactly_three_milestones_one_per_phase(
        cls, v: list[EnablerMilestoneLLM]
    ) -> list[EnablerMilestoneLLM]:
        if len(v) != 3:
            raise ValueError(f"must have exactly 3 milestones, got {len(v)}")
        phases = {m.phase for m in v}
        if phases != {Phase.FOUNDATION, Phase.INTERMEDIATE, Phase.EXPERT}:
            raise ValueError(f"milestones must cover all 3 phases exactly once, got {phases}")
        return v
