"""Local embedding-based skill canonicalization.

Builds a local vector index (Chroma or FAISS, per VECTOR_STORE) over
taxonomy.py's ~60 canonical skills — indexing each skill's name AND each of
its aliases as its own embedding point (not one combined "name (aliases)"
string; see taxonomy.all_name_variants for why) — and matches raw JD skill
strings against it via cosine similarity. Used by agent_extractor.py to
canonicalize each extracted skill; anything below CANONICALIZATION_THRESHOLD
falls back to the raw extracted string (see AgentExtractor's `canonical`
flag on Skill).
"""

from __future__ import annotations

from functools import lru_cache

from config import settings
from taxonomy import all_name_variants


class EmbeddingError(Exception):
    """Raised when the embedding model or vector backend fails to load/query."""


@lru_cache(maxsize=1)
def _get_model():
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise EmbeddingError(
            "sentence-transformers is not installed. Run: pip install sentence-transformers"
        ) from exc
    return SentenceTransformer(settings.embedding_model)


def _best_per_canonical_name(matches: list[tuple[str, float]]) -> tuple[str, float] | None:
    """Multiple index rows (name + aliases) map to the same canonical name;
    collapse raw top-k matches down to the single best score per name."""
    best: dict[str, float] = {}
    for name, score in matches:
        if score > best.get(name, -1.0):
            best[name] = score
    if not best:
        return None
    return max(best.items(), key=lambda kv: kv[1])


class _FaissIndex:
    def __init__(self, canonical_names: list[str], vectors) -> None:
        try:
            import faiss
        except ImportError as exc:
            raise EmbeddingError("faiss-cpu is not installed. Run: pip install faiss-cpu") from exc
        import numpy as np

        self._faiss = faiss
        self._np = np
        self._canonical_names = canonical_names  # index i -> canonical name (may repeat)
        vecs = np.array(vectors, dtype="float32")
        faiss.normalize_L2(vecs)
        self._index = faiss.IndexFlatIP(vecs.shape[1])
        self._index.add(vecs)

    def best_match(self, vector, candidate_pool: int = 10) -> tuple[str, float] | None:
        vec = self._np.array([vector], dtype="float32")
        self._faiss.normalize_L2(vec)
        k = min(candidate_pool, self._index.ntotal)
        scores, idxs = self._index.search(vec, k)
        raw_matches = [
            (self._canonical_names[i], float(scores[0][rank]))
            for rank, i in enumerate(idxs[0])
            if i != -1
        ]
        return _best_per_canonical_name(raw_matches)


class _ChromaIndex:
    COLLECTION_NAME = "skill_taxonomy"

    def __init__(self, canonical_names: list[str], variant_texts: list[str], vectors) -> None:
        try:
            import chromadb
        except ImportError as exc:
            raise EmbeddingError("chromadb is not installed. Run: pip install chromadb") from exc

        client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        self._collection = client.get_or_create_collection(
            self.COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
        )
        if self._collection.count() != len(canonical_names):
            # fresh collection, or taxonomy.py's variant count changed since last persisted run
            ids = [f"{name}::{i}" for i, name in enumerate(canonical_names)]
            self._collection.upsert(
                ids=ids,
                embeddings=[[float(x) for x in v] for v in vectors],
                metadatas=[
                    {"name": name, "surface_form": text}
                    for name, text in zip(canonical_names, variant_texts)
                ],
                documents=variant_texts,
            )

    def best_match(self, vector, candidate_pool: int = 10) -> tuple[str, float] | None:
        res = self._collection.query(
            query_embeddings=[[float(x) for x in vector]], n_results=candidate_pool
        )
        metadatas = res["metadatas"][0]
        distances = res["distances"][0]  # cosine distance = 1 - cosine similarity
        raw_matches = [(meta["name"], 1.0 - dist) for meta, dist in zip(metadatas, distances)]
        return _best_per_canonical_name(raw_matches)


@lru_cache(maxsize=1)
def _get_index():
    model = _get_model()
    variant_pairs = all_name_variants()  # [(canonical_name, surface_form), ...]
    canonical_names = [n for n, _ in variant_pairs]
    surface_forms = [t for _, t in variant_pairs]
    vectors = model.encode(surface_forms, normalize_embeddings=False)

    if settings.vector_store == "faiss":
        return _FaissIndex(canonical_names, vectors)
    if settings.vector_store == "chroma":
        return _ChromaIndex(canonical_names, surface_forms, vectors)
    raise EmbeddingError(f"Unknown VECTOR_STORE '{settings.vector_store}'. Must be 'chroma' or 'faiss'.")


def canonicalize_skill(raw_name: str) -> tuple[str, bool]:
    """Matches `raw_name` against the skill taxonomy.

    Returns (name, is_canonical):
      - (canonical taxonomy name, True) if the best match's cosine similarity
        is >= settings.canonicalization_threshold
      - (raw_name, False) otherwise — the Extractor keeps the raw string
    """
    model = _get_model()
    index = _get_index()
    vector = model.encode([raw_name], normalize_embeddings=False)[0]
    match = index.best_match(vector)
    if match is None:
        return raw_name, False
    best_name, best_score = match
    if best_score >= settings.canonicalization_threshold:
        return best_name, True
    return raw_name, False


def canonicalize_skills(raw_names: list[str]) -> list[tuple[str, bool]]:
    """Batch version of canonicalize_skill — embeds all raw names in one call."""
    if not raw_names:
        return []
    model = _get_model()
    index = _get_index()
    vectors = model.encode(raw_names, normalize_embeddings=False)
    results = []
    for raw_name, vector in zip(raw_names, vectors):
        match = index.best_match(vector)
        if match is not None and match[1] >= settings.canonicalization_threshold:
            results.append((match[0], True))
        else:
            results.append((raw_name, False))
    return results
