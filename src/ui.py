"""Shared Streamlit UI components."""

from __future__ import annotations

import streamlit as st

from src.config import Settings, get_settings, is_api_configured
from src.utils import format_latency


def init_session_defaults() -> None:
    """Initialize session state from environment on first load."""
    env = get_settings()

    # Migrate legacy session keys from older versions.
    if "temperature" not in st.session_state and "default_temperature" in st.session_state:
        st.session_state["temperature"] = st.session_state["default_temperature"]
    if "max_tokens" not in st.session_state and "default_max_tokens" in st.session_state:
        st.session_state["max_tokens"] = st.session_state["default_max_tokens"]

    defaults = {
        "base_url": env.base_url,
        "api_key": env.api_key,
        "model_name": env.model_name,
        "embedding_mode": env.embedding_mode,
        "embedding_model": env.embedding_model,
        "local_embedding_model": env.local_embedding_model,
        "temperature": env.temperature,
        "max_tokens": env.max_tokens,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def render_generation_metadata(
    model: str,
    temperature: float,
    max_tokens: int,
    latency_ms: float,
    input_tokens: int,
    output_tokens: int,
) -> None:
    """Display generation parameters and usage metrics for a model call."""
    total_tokens = input_tokens + output_tokens
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("当前模型", model)
    c2.metric("Temperature", f"{temperature:.1f}")
    c3.metric("最大输出 Tokens", max_tokens)
    c4.metric("响应时间", format_latency(latency_ms))
    c5.metric("Token 估算", total_tokens)


def render_sidebar() -> None:
    """Render global API and model configuration in sidebar."""
    init_session_defaults()
    env = get_settings()

    st.sidebar.title("全局配置")
    st.session_state["base_url"] = st.sidebar.text_input(
        "Base URL",
        value=st.session_state.get("base_url", env.base_url),
    )
    st.session_state["api_key"] = st.sidebar.text_input(
        "API Key",
        value=st.session_state.get("api_key", ""),
        type="password",
        help="也可在 .env 中配置 API_KEY",
    )
    st.session_state["model_name"] = st.sidebar.text_input(
        "默认模型",
        value=st.session_state.get("model_name", env.model_name),
    )
    st.session_state["embedding_mode"] = st.sidebar.selectbox(
        "Embedding 模式",
        ["api", "local"],
        index=0 if st.session_state.get("embedding_mode", "api") == "api" else 1,
        format_func=lambda x: "API" if x == "api" else "本地",
    )
    st.session_state["embedding_model"] = st.sidebar.text_input(
        "Embedding 模型 (API)",
        value=st.session_state.get("embedding_model", env.embedding_model),
    )
    st.session_state["local_embedding_model"] = st.sidebar.text_input(
        "本地 Embedding 模型",
        value=st.session_state.get("local_embedding_model", env.local_embedding_model),
    )

    st.sidebar.divider()
    st.sidebar.subheader("生成参数")
    st.session_state["temperature"] = st.sidebar.slider(
        "Temperature",
        min_value=0.0,
        max_value=2.0,
        value=float(st.session_state.get("temperature", env.temperature)),
        step=0.1,
        help="数值越低越稳定，越高越发散",
    )
    st.session_state["max_tokens"] = st.sidebar.number_input(
        "最大输出 Tokens",
        min_value=256,
        max_value=4096,
        value=int(st.session_state.get("max_tokens", env.max_tokens)),
        step=128,
        help="控制模型单次回答的最大长度",
    )

    current = Settings(
        base_url=st.session_state["base_url"],
        api_key=st.session_state["api_key"],
        model_name=st.session_state["model_name"],
        embedding_mode=st.session_state["embedding_mode"],
        embedding_model=st.session_state["embedding_model"],
        local_embedding_model=st.session_state["local_embedding_model"],
        temperature=st.session_state.get("temperature", env.temperature),
        max_tokens=st.session_state.get("max_tokens", env.max_tokens),
    )
    if is_api_configured(current):
        st.sidebar.success("API 已配置")
    else:
        st.sidebar.warning("API 未配置")


def setup_page(title: str, icon: str = "🧪") -> None:
    """Standard page setup: config, sidebar, db init."""
    from src.database import init_db

    st.set_page_config(page_title=title, page_icon=icon, layout="wide")
    init_session_defaults()
    render_sidebar()
    init_db()
