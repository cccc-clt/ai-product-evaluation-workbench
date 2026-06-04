"""Prompt experiment lab page."""

import src.bootstrap  # noqa: F401

import streamlit as st

from src.config import get_session_settings
from src.database import save_prompt_experiment, save_user_feedback
from src.llm_client import chat
from src.prompt_templates import get_scene_names, get_system_prompt
from src.ui import render_generation_metadata, setup_page
from src.utils import estimate_cost, is_ark_endpoint, render_api_warning

setup_page("Prompt 实验台", "🧪")

st.title("Prompt 实验台")
st.caption("选择业务场景，调试 System / User Prompt，记录实验结果与版本。")

api_ok = render_api_warning()
settings = get_session_settings()
temperature = settings.temperature
max_tokens = settings.max_tokens

scenes = get_scene_names()
col1, col2 = st.columns([1, 2])

with col1:
    scene = st.selectbox("业务场景", scenes, key="prompt_scene")
    model = st.text_input("模型名称", value=settings.model_name, key="prompt_model")

with col2:
    default_system = get_system_prompt(scene)
    if st.session_state.get("_last_scene") != scene:
        st.session_state["prompt_system"] = default_system
        st.session_state["_last_scene"] = scene
    system_prompt = st.text_area(
        "System Prompt",
        value=st.session_state.get("prompt_system", default_system),
        height=160,
        key="prompt_system",
    )
    user_prompt = st.text_area("User Prompt", height=160, key="prompt_user")

run = st.button("运行实验", type="primary", disabled=not api_ok)

if run:
    if not user_prompt.strip():
        st.error("请输入 User Prompt")
    else:
        with st.spinner("调用模型中..."):
            result = chat(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                settings=settings,
            )
        if result.error:
            st.error(result.error)
        else:
            cost = estimate_cost(model, result.input_tokens, result.output_tokens)
            from datetime import datetime

            version = datetime.now().strftime("v%Y%m%d.%H%M%S")
            st.session_state["last_experiment"] = {
                "scene": scene,
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "model": model,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "response": result.content,
                "latency_ms": result.latency_ms,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "cost": cost,
                "version": version,
            }
            st.success("实验完成")

if "last_experiment" in st.session_state:
    exp = st.session_state["last_experiment"]
    st.divider()
    st.subheader("实验结果")
    render_generation_metadata(
        model=exp["model"],
        temperature=exp["temperature"],
        max_tokens=exp["max_tokens"],
        latency_ms=exp["latency_ms"],
        input_tokens=exp["input_tokens"],
        output_tokens=exp["output_tokens"],
    )
    m1, m2, m3 = st.columns(3)
    m1.metric("Input Tokens", exp["input_tokens"])
    m2.metric("Output Tokens", exp["output_tokens"])
    cost_label = "估算成本 (USD，¥参考)" if is_ark_endpoint(exp["model"]) else "估算成本 (USD)"
    m3.metric(cost_label, f"${exp['cost']:.6f}")
    st.markdown(f"**Prompt 版本:** `{exp['version']}`")
    st.markdown("**模型回答**")
    st.markdown(exp["response"])

    human_score = st.slider("人工评分 (1-5，可选)", 1, 5, 3, key="prompt_human_score")
    if st.button("保存实验记录"):
        row_id = save_prompt_experiment(
            scene=exp["scene"],
            system_prompt=exp["system_prompt"],
            user_prompt=exp["user_prompt"],
            model=exp["model"],
            temperature=exp["temperature"],
            max_tokens=exp["max_tokens"],
            response=exp["response"],
            latency_ms=exp["latency_ms"],
            input_tokens=exp["input_tokens"],
            output_tokens=exp["output_tokens"],
            cost=exp["cost"],
            version=exp["version"],
            human_score=human_score,
        )
        save_user_feedback(
            source_type="prompt",
            source_id=row_id,
            score=human_score,
            tags=[],
            comment=f"{exp['scene']} | {exp['version']}",
        )
        st.success(f"已保存实验记录 (#{row_id})")
