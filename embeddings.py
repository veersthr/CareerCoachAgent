"""Local skill canonicalization — no ML deps, stdlib only.

Matches raw JD skill strings against taxonomy.py's ~60 canonical skills in two
passes:
  1. Exact match (case-insensitive) against each skill's name/aliases via
     taxonomy.ALIAS_TO_CANONICAL — covers the common case where the JD uses a
     known alias verbatim ("k8s", "Postgres", "GCP").
  2. Fuzzy match (difflib.SequenceMatcher ratio) against every name/alias
     surface form, for typos/case/punctuation variance the alias list doesn't
     cover verbatim.

This previously ran on sentence-transformers + chromadb/faiss for semantic
(not just lexical) matching, at the cost of ~1GB of ML dependencies and RAM
that don't fit a small hosting instance. Aliases in taxonomy.py already
absorb most of the semantic-gap cases (abbreviations, common rephrasings);
what's left is lexical variance, which fuzzy string matching handles well
enough at a fraction of the footprint.
"""

from __future__ import annotations

from difflib import SequenceMatcher
from functools import lru_cache

from config import settings
from taxonomy import ALIAS_TO_CANONICAL, all_name_variants


@lru_cache(maxsize=1)
def _variants() -> list[tuple[str, str]]:
    """[(canonical_name, lowercased surface_form), ...]"""
    return [(name, surface.lower()) for name, surface in all_name_variants()]


def _fuzzy_best_match(raw_lower: str) -> tuple[str, float] | None:
    best_name: str | None = None
    best_score = -1.0
    for canonical_name, surface in _variants():
        score = SequenceMatcher(None, raw_lower, surface).ratio()
        if score > best_score:
            best_name, best_score = canonical_name, score
    if best_name is None:
        return None
    return best_name, best_score


def canonicalize_skill(raw_name: str) -> tuple[str, bool]:
    """Matches `raw_name` against the skill taxonomy.

    Returns (name, is_canonical):
      - (canonical taxonomy name, True) on an exact alias match, or a fuzzy
        match scoring >= settings.canonicalization_threshold
      - (raw_name, False) otherwise — the Extractor keeps the raw string
    """
    raw_lower = raw_name.strip().lower()
    exact = ALIAS_TO_CANONICAL.get(raw_lower)
    if exact is not None:
        return exact, True

    match = _fuzzy_best_match(raw_lower)
    if match is not None and match[1] >= settings.canonicalization_threshold:
        return match[0], True
    return raw_name, False


def canonicalize_skills(raw_names: list[str]) -> list[tuple[str, bool]]:
    """Batch version of canonicalize_skill."""
    return [canonicalize_skill(name) for name in raw_names]
