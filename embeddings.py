"""Local embedding-based skill canonicalization.

Builds a local vector index (Chroma or FAISS, per VECTOR_STORE) over
taxonomy.py's ~60 canonical skills and matches raw JD skill strings against it
via cosine similarity. Used by agent_extractor.py to canonicalize each
extracted skill; anything below CANONICALIZATION_THRESHOLD falls back to the
raw extracted string (see AgentExtractor's `canonical` flag on Skill).
"""

from __future__ import annotations

from functools import lru_cache

from config import settings
from taxonomy import all_embedding_texts


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


class _FaissIndex:
    def __init__(self, names: list[str], vectors) -> None:
        try:
            import faiss
        except ImportError as exc:
            raise EmbeddingError("faiss-cpu is not installed. Run: pip install faiss-cpu") from exc
        import numpy as np

        self._faiss = faiss
        self._np = np
        self._names = names
        vecs = np.array(vectors, dtype="float32")
        faiss.normalize_L2(vecs)
        self._index = faiss.IndexFlatIP(vecs.shape[1])
        self._index.add(vecs)

    def query(self, vector, top_k: int = 1) -> list[tuple[str, float]]:
        vec = self._np.array([vector], dtype="float32")
        self._faiss.normalize_L2(vec)
        scores, idxs = self._index.search(vec, top_k)
        return [
            (self._names[i], float(scores[0][rank]))
            for rank, i in enumerate(idxs[0])
            if i != -1
        ]


class _ChromaIndex:
    COLLECTION_NAME = "skill_taxonomy"

    def __init__(self, names: list[str], vectors) -> None:
        try:
            import chromadb
        except ImportError as exc:
            raise EmbeddingError("chromadb is not installed. Run: pip install chromadb") from exc

        client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        self._collection = client.get_or_create_collection(
            self.COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
        )
        if self._collection.count() != len(names):
            # fresh collection, or taxonomy.py changed size since last persisted run
            self._collection.upsert(
                ids=names,
                embeddings=[list(v) for v in vectors],
                metadatas=[{"name": n} for n in names],
            )

    def query(self, vector, top_k: int = 1) -> list[tuple[str, float]]:
        res = self._collection.query(query_embeddings=[list(vector)], n_results=top_k)
        ids = res["ids"][0]
        distances = res["distances"][0]  # cosine distance = 1 - cosine similarity
        return [(id_, 1.0 - dist) for id_, dist in zip(ids, distances)]


@lru_cache(maxsize=1)
def _get_index():
    model = _get_model()
    names_texts = all_embedding_texts()
    names = [n for n, _ in names_texts]
    texts = [t for _, t in names_texts]
    vectors = model.encode(texts, normalize_embeddings=False)

    if settings.vector_store == "faiss":
        return _FaissIndex(names, vectors)
    if settings.vector_store == "chroma":
        return _ChromaIndex(names, vectors)
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
    matches = index.query(vector, top_k=1)
    if not matches:
        return raw_name, False
    best_name, best_score = matches[0]
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
        matches = index.query(vector, top_k=1)
        if matches and matches[0][1] >= settings.canonicalization_threshold:
            results.append((matches[0][0], True))
        else:
            results.append((raw_name, False))
    return results
