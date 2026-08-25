"""LangGraph pipeline definition — wires the 5 agents into a StateGraph with
one conditional retry loop, checkpointed via SqliteSaver.

Extractor -> Role Strategist -> Scheduler -> Enabler -> Validator ->
  (pass -> END) / (fail, retry_count < settings.max_retries -> Extractor)

The retry cap itself lives in agent_validator.py (it owns retry_count and
decides validation_passed); this module only reads that decision to pick
the outgoing edge.
"""

import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, StateGraph

from agent_enabler import run_enabler
from agent_extractor import run_extractor
from agent_role_strategist import run_role_strategist
from agent_scheduler import run_scheduler
from agent_validator import run_validator
from config import settings
from schemas import AgentState


def _route_after_validator(state: AgentState) -> str:
    return "end" if state["validation_passed"] else "retry"


def build_graph():
    """Builds and compiles the pipeline graph. Call once per process (see
    the module-level `graph` below) — the checkpointer's sqlite connection
    is meant to live for the process's lifetime, not be reopened per call."""
    workflow = StateGraph(AgentState)

    workflow.add_node("extractor", run_extractor)
    workflow.add_node("role_strategist", run_role_strategist)
    workflow.add_node("scheduler", run_scheduler)
    workflow.add_node("enabler", run_enabler)
    workflow.add_node("validator", run_validator)

    workflow.set_entry_point("extractor")
    workflow.add_edge("extractor", "role_strategist")
    workflow.add_edge("role_strategist", "scheduler")
    workflow.add_edge("scheduler", "enabler")
    workflow.add_edge("enabler", "validator")
    workflow.add_conditional_edges(
        "validator",
        _route_after_validator,
        {"end": END, "retry": "extractor"},
    )

    conn = sqlite3.connect(settings.sqlite_path, check_same_thread=False)
    checkpointer = SqliteSaver(conn)

    return workflow.compile(checkpointer=checkpointer)


# Process-wide compiled graph — api.py imports and reuses this across requests.
graph = build_graph()
