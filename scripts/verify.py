"""Smoke tests for core modules (no API calls)."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main() -> None:
    """Run import and database initialization checks."""
    print("1. Testing imports...")
    from src.config import Settings, get_settings, is_api_configured
    import src.database as database
    from src.evaluator import build_advisor_prompt, collect_optimization_context
    from src.llm_client import chat_completion
    from src.prompt_templates import get_scene_names, get_system_prompt
    from src.rag_engine import chunk_text
    from src.utils import estimate_cost, parse_model_list

    print("   OK")

    print("2. Testing config...")
    s = get_settings()
    assert s.model_name
    print(f"   model={s.model_name}, api_configured={is_api_configured(s)}")

    print("3. Testing database init...")
    original_data_dir = database.DATA_DIR
    original_db_path = database.DB_PATH
    try:
        with tempfile.TemporaryDirectory() as tmp:
            database.DATA_DIR = Path(tmp)
            database.DB_PATH = Path(tmp) / "workbench.db"
            database.init_db()
            feedback_id = database.save_user_feedback(
                "verify", None, None, [], "smoke check"
            )
            assert feedback_id > 0
            assert database.seed_demo_data_if_empty() is True
            assert database.seed_demo_data_if_empty() is False
            stats = database.get_dashboard_stats()
    finally:
        database.DATA_DIR = original_data_dir
        database.DB_PATH = original_db_path
    print(f"   total_experiments={stats['total_experiments']}")

    print("4. Testing prompt templates...")
    scenes = get_scene_names()
    assert len(scenes) == 6
    assert get_system_prompt("客服问答")

    print("5. Testing utils...")
    assert parse_model_list("a, b, c") == ["a", "b", "c"]
    assert estimate_cost("gpt-4o-mini", 1000, 500) > 0

    print("6. Testing chunk_text...")
    chunks = chunk_text("word " * 200, chunk_size=100, overlap=10)
    assert len(chunks) >= 2

    print("7. Testing advisor context...")
    ctx = collect_optimization_context()
    prompt = build_advisor_prompt(ctx)
    assert "评测数据" in prompt

    print("8. Testing no-key chat handling...")
    no_key = Settings(
        base_url=s.base_url,
        api_key="your_api_key_here",
        model_name=s.model_name,
        embedding_mode=s.embedding_mode,
        embedding_model=s.embedding_model,
        local_embedding_model=s.local_embedding_model,
        default_temperature=s.default_temperature,
        default_max_tokens=s.default_max_tokens,
    )
    result = chat_completion("system", "hello", settings=no_key)
    assert result.error and "API Key" in result.error

    print("\nAll checks passed.")


if __name__ == "__main__":
    main()
