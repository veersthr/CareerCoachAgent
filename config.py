"""Central config. Loads env vars once; every other file imports `settings` from here."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent


def _get_bool(key: str, default: bool) -> bool:
    val = os.getenv(key)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    # --- LLM provider ---
    llm_provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "groq").lower())

    groq_api_key: str = field(default_factory=lambda: os.getenv("GROQ_API_KEY", ""))
    groq_model: str = field(default_factory=lambda: os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"))

    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    gemini_model: str = field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-1.5-flash"))

    ollama_base_url: str = field(default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    ollama_model: str = field(default_factory=lambda: os.getenv("OLLAMA_MODEL", "llama3.1"))

    llm_temperature: float = field(default_factory=lambda: float(os.getenv("LLM_TEMPERATURE", "0.2")))
    llm_max_retries: int = field(default_factory=lambda: int(os.getenv("LLM_MAX_RETRIES", "3")))

    # --- Embeddings / vector search ---
    embedding_model: str = field(
        default_factory=lambda: os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    )
    vector_store: str = field(default_factory=lambda: os.getenv("VECTOR_STORE", "chroma").lower())  # chroma|faiss
    canonicalization_threshold: float = field(
        default_factory=lambda: float(os.getenv("CANONICALIZATION_THRESHOLD", "0.75"))
    )

    # --- PDF / OCR ---
    tesseract_cmd: str = field(default_factory=lambda: os.getenv("TESSERACT_CMD", ""))  # empty = use system PATH

    # --- Pipeline behavior (deterministic constants) ---
    max_retries: int = field(default_factory=lambda: int(os.getenv("MAX_RETRIES", "2")))
    readiness_score_cap: float = field(
        default_factory=lambda: float(os.getenv("READINESS_SCORE_CAP", "65"))
    )
    readiness_role_weight_multiplier: float = field(
        default_factory=lambda: float(os.getenv("READINESS_ROLE_WEIGHT_MULTIPLIER", "12"))
    )
    milestone_pass_thresholds: tuple = (0.30, 0.50, 0.65)  # Foundation, Intermediate, Expert

    # --- Storage paths ---
    data_dir: Path = field(default_factory=lambda: BASE_DIR / "data")
    cache_dir: Path = field(default_factory=lambda: BASE_DIR / "data" / "cache")
    sqlite_path: str = field(
        default_factory=lambda: os.getenv("SQLITE_PATH") or str(BASE_DIR / "data" / "checkpoints.sqlite")
    )
    chroma_persist_dir: str = field(
        default_factory=lambda: os.getenv("CHROMA_PERSIST_DIR") or str(BASE_DIR / "data" / "chroma")
    )
    outputs_dir: Path = field(default_factory=lambda: BASE_DIR / "outputs")

    # --- API ---
    api_host: str = field(default_factory=lambda: os.getenv("API_HOST", "0.0.0.0"))
    api_port: int = field(default_factory=lambda: int(os.getenv("API_PORT", "8000")))

    debug: bool = field(default_factory=lambda: _get_bool("DEBUG", False))

    def ensure_dirs(self) -> None:
        for d in (self.data_dir, self.cache_dir, self.outputs_dir, Path(self.chroma_persist_dir)):
            d.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()
