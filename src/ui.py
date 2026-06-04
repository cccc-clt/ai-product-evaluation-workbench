"""Shared Streamlit UI components."""

from __future__ import annotations

import streamlit as st

from src.config import Settings, get_settings, is_api_configured


def init_session_defaults() -> None:
    """Initialize session state from environment on first load."""
    env = get_settings()
    defaults = {
        "base_url": env.base_url,
        "api_key": env.api_key,
        "model_name": env.model_name,
        "embedding_mode": env.embedding_mode,
        "embedding_model": env.embedding_model,
        "local_embedding_model": env.local_embedding_model,
        "default_temperature": env.default_temperature,
        "default_max_tokens": env.default_max_tokens,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


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

    current = Settings(
        base_url=st.session_state["base_url"],
        api_key=st.session_state["api_key"],
        model_name=st.session_state["model_name"],
        embedding_mode=st.session_state["embedding_mode"],
        embedding_model=st.session_state["embedding_model"],
        local_embedding_model=st.session_state["local_embedding_model"],
        default_temperature=st.session_state.get(
            "default_temperature", env.default_temperature
        ),
        default_max_tokens=st.session_state.get(
            "default_max_tokens", env.default_max_tokens
        ),
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
