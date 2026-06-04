"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "workbench.db"
CHROMA_PATH = DATA_DIR / "chroma"

load_dotenv(PROJECT_ROOT / ".env")


def _get_float_env(name: str, default: float) -> float:
    """Read a float env var, falling back when the value is invalid."""
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _get_int_env(name: str, default: int) -> int:
    """Read an int env var, falling back when the value is invalid."""
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


@dataclass
class Settings:
    """Runtime settings for API and model defaults."""

    base_url: str
    api_key: str
    model_name: str
    embedding_mode: str
    embedding_model: str
    local_embedding_model: str
    temperature: float
    max_tokens: int


def get_settings() -> Settings:
    """Load settings from environment with sensible defaults."""
    embedding_mode = os.getenv("EMBEDDING_MODE", "api").strip().lower()
    if embedding_mode not in {"api", "local"}:
        embedding_mode = "api"

    return Settings(
        base_url=os.getenv("BASE_URL", "https://api.openai.com/v1").strip(),
        api_key=os.getenv("API_KEY", "").strip(),
        model_name=os.getenv("MODEL_NAME", "gpt-4o-mini").strip(),
        embedding_mode=embedding_mode,
        embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small").strip(),
        local_embedding_model=os.getenv(
            "LOCAL_EMBEDDING_MODEL", "all-MiniLM-L6-v2"
        ).strip(),
        temperature=_get_float_env("DEFAULT_TEMPERATURE", 0.7),
        max_tokens=_get_int_env("DEFAULT_MAX_TOKENS", 1024),
    )


def get_session_settings() -> Settings:
    """Merge .env settings with Streamlit session overrides when present."""
    import streamlit as st

    base = get_settings()
    if not hasattr(st, "session_state"):
        return base

    ss = st.session_state
    return Settings(
        base_url=ss.get("base_url", base.base_url),
        api_key=ss.get("api_key", base.api_key),
        model_name=ss.get("model_name", base.model_name),
        embedding_mode=ss.get("embedding_mode", base.embedding_mode),
        embedding_model=ss.get("embedding_model", base.embedding_model),
        local_embedding_model=ss.get(
            "local_embedding_model", base.local_embedding_model
        ),
        temperature=ss.get("temperature", base.temperature),
        max_tokens=ss.get("max_tokens", base.max_tokens),
    )


def is_api_configured(settings: Settings | None = None) -> bool:
    """Return True when API key is set and not a placeholder."""
    s = settings or get_settings()
    key = (s.api_key or "").strip()
    if not key:
        return False
    placeholders = {"your_api_key_here", "sk-xxx", "changeme", "placeholder"}
    return key.lower() not in placeholders
