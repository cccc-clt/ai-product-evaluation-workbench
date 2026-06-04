"""Shared utilities for UI, parsing, and cost estimation."""

from __future__ import annotations

import re
from typing import Any

# USD per 1K tokens (input, output). More specific keys must come before general ones.
# 火山方舟 Doubao 价格以人民币计，此处按 ~7.2 CNY/USD 折算为 USD 估算值。
# 火山方舟 Endpoint ID（ep-xxx）不含模型名，将 fallback 到 "ark-endpoint"。
PRICING: dict[str, tuple[float, float]] = {
    # OpenAI
    "gpt-4o-mini": (0.00015, 0.0006),
    "gpt-4o": (0.0025, 0.01),
    "gpt-4-turbo": (0.01, 0.03),
    "gpt-3.5-turbo": (0.0005, 0.0015),
    # 火山方舟 Doubao（¥/1K → USD/1K，汇率约 7.2）
    "doubao-pro-256k": (0.00069, 0.00125),   # ¥0.005 / ¥0.009
    "doubao-pro-128k": (0.00069, 0.00125),   # ¥0.005 / ¥0.009
    "doubao-pro": (0.00011, 0.00011),        # ¥0.0008 / ¥0.0008
    "doubao-lite": (0.000042, 0.000083),     # ¥0.0003 / ¥0.0006
    "doubao": (0.00011, 0.00011),            # 通用 doubao fallback
    # DeepSeek
    "deepseek-r1": (0.00055, 0.00219),
    "deepseek": (0.00027, 0.0011),           # v3 / chat fallback
    # 火山方舟 Endpoint ID（ep-xxx）fallback
    "ark-endpoint": (0.00011, 0.00011),
    "default": (0.001, 0.002),
}

RAG_ISSUE_TAGS = [
    "幻觉",
    "引用错误",
    "回答太泛",
    "没有按照格式输出",
    "理解错问题",
    "答案太短",
    "速度太慢",
    "成本太高",
]


def render_api_warning() -> bool:
    """Show warning if API is not configured. Returns True if configured."""
    import streamlit as st

    from src.config import get_session_settings, is_api_configured

    settings = get_session_settings()
    if is_api_configured(settings):
        return True
    st.warning(
        "请在侧边栏或 `.env` 中配置 **API Key** 和 **Base URL** 后再运行模型调用。"
    )
    return False


def parse_model_list(text: str) -> list[str]:
    """Parse comma-separated model names into a clean list."""
    if not text or not text.strip():
        return []
    parts = re.split(r"[,，\n]+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def format_latency(ms: float | int | None) -> str:
    """Format latency in milliseconds for display."""
    if ms is None:
        return "—"
    if ms < 1000:
        return f"{ms:.0f} ms"
    return f"{ms / 1000:.2f} s"


def estimate_cost(
    model: str, input_tokens: int, output_tokens: int
) -> float:
    """Estimate API cost using simplified per-model pricing."""
    model_lower = (model or "").lower()
    # 火山方舟 Endpoint ID 格式：ep-xxxxxxxx-xxxxx，不含模型名，用专项 fallback
    if re.match(r"^ep-[a-z0-9]+-[a-z0-9]+$", model_lower):
        model_lower = "ark-endpoint"
    rates = PRICING["default"]
    for key, price in PRICING.items():
        if key not in {"default", "ark-endpoint"} and key in model_lower:
            rates = price
            break
        if key == "ark-endpoint" and model_lower == "ark-endpoint":
            rates = price
            break
    inp_cost = (input_tokens / 1000.0) * rates[0]
    out_cost = (output_tokens / 1000.0) * rates[1]
    return round(inp_cost + out_cost, 6)


def is_ark_endpoint(model: str) -> bool:
    """Return True when the model string looks like a Volces Ark endpoint ID."""
    return bool(re.match(r"^ep-[a-z0-9]+-[a-z0-9]+$", (model or "").lower()))


def estimate_tokens_fallback(text: str) -> int:
    """Rough token estimate when tiktoken is unavailable (~4 chars per token)."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def count_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    """Count tokens with tiktoken, falling back to char heuristic."""
    try:
        import tiktoken

        try:
            enc = tiktoken.encoding_for_model(model)
        except KeyError:
            enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text or ""))
    except Exception:
        return estimate_tokens_fallback(text)


def tags_to_json(tags: list[str]) -> str:
    """Serialize tag list for database storage."""
    import json

    return json.dumps(tags, ensure_ascii=False)


def tags_from_json(raw: str | None) -> list[str]:
    """Deserialize tags from database."""
    import json

    if not raw:
        return []
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def safe_metric_columns(metrics: list[tuple[str, Any]]) -> None:
    """Render a row of metric cards."""
    import streamlit as st

    cols = st.columns(len(metrics))
    for col, (label, value) in zip(cols, metrics):
        col.metric(label, value)
