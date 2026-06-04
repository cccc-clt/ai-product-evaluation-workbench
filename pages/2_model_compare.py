"""Multi-model comparison page."""

import src.bootstrap  # noqa: F401

import streamlit as st
import pandas as pd

from src.config import get_session_settings
from src.database import save_model_comparison, save_user_feedback
from src.llm_client import chat
from src.ui import setup_page
from src.utils import estimate_cost, format_latency, is_ark_endpoint, parse_model_list, render_api_warning

setup_page("多模型对比", "📊")

st.title("多模型效果对比")
st.caption("同一问题横向对比多个模型的回答质量、速度与成本。")

api_ok = render_api_warning()
settings = get_session_settings()

question = st.text_area("测试问题", height=120, placeholder="输入要测试的问题...")
models_text = st.text_input(
    "模型列表（英文逗号分隔）",
    value=settings.model_name,
    help="例如: gpt-4o-mini, gpt-4o, deepseek-chat",
)
system_prompt = st.text_area(
    "System Prompt（可选）",
    value="你是一名 helpful assistant，请准确、简洁地回答问题。",
    height=100,
)

run = st.button("开始对比", type="primary", disabled=not api_ok)

if run:
    models = parse_model_list(models_text)
    if not question.strip():
        st.error("请输入测试问题")
    elif not models:
        st.error("请至少填写一个模型名称")
    else:
        results = []
        progress = st.progress(0, text="正在调用模型...")
        for i, model_name in enumerate(models):
            progress.progress((i) / len(models), text=f"调用 {model_name}...")
            result = chat(
                system_prompt=system_prompt,
                user_prompt=question,
                model=model_name,
                temperature=settings.default_temperature,
                max_tokens=settings.default_max_tokens,
                settings=settings,
            )
            cost = estimate_cost(
                model_name, result.input_tokens, result.output_tokens
            )
            results.append(
                {
                    "model": model_name,
                    "response": result.content if not result.error else f"[错误] {result.error}",
                    "latency_ms": result.latency_ms,
                    "input_tokens": result.input_tokens,
                    "output_tokens": result.output_tokens,
                    "cost": cost,
                    "error": result.error,
                }
            )
        progress.progress(1.0, text="完成")
        st.session_state["compare_results"] = {
            "question": question,
            "system_prompt": system_prompt,
            "items": results,
        }

if "compare_results" in st.session_state:
    data = st.session_state["compare_results"]
    items = data["items"]
    st.divider()
    st.subheader("对比汇总")

    df = pd.DataFrame(
        [
            {
                "模型": it["model"],
                "响应时间": format_latency(it["latency_ms"]),
                "Input Tokens": it["input_tokens"],
                "Output Tokens": it["output_tokens"],
                "成本 (USD)": f"${it['cost']:.6f}" + (" *" if is_ark_endpoint(it["model"]) else ""),
            }
            for it in items
        ]
    )
    st.dataframe(df, use_container_width=True)
    if any(is_ark_endpoint(it["model"]) for it in items):
        st.caption("* 火山方舟 Endpoint ID 不含模型名，成本按 Doubao-Pro 估算（¥0.0008/1K），仅供参考。")

    st.subheader("各模型回答详情")
    for idx, it in enumerate(items):
        with st.expander(f"{it['model']} — {format_latency(it['latency_ms'])}"):
            st.markdown(it["response"])
            c1, c2 = st.columns([1, 3])
            with c1:
                st.slider(
                    "人工评分 (1-5)",
                    1,
                    5,
                    3,
                    key=f"compare_score_{idx}",
                )
            with c2:
                st.text_area(
                    "优缺点备注",
                    placeholder="记录该模型的优势与不足...",
                    key=f"compare_notes_{idx}",
                )

    if st.button("保存对比记录", type="primary"):
        save_items = []
        for idx, it in enumerate(items):
            save_items.append(
                {
                    **it,
                    "human_score": st.session_state.get(f"compare_score_{idx}", 3),
                    "notes": st.session_state.get(f"compare_notes_{idx}", ""),
                }
            )
        comp_id = save_model_comparison(data["question"], save_items)
        for item in save_items:
            save_user_feedback(
                source_type="compare",
                source_id=comp_id,
                score=item.get("human_score"),
                tags=[],
                comment=f"{item.get('model', '')}: {item.get('notes', '')}",
            )
        st.success(f"对比记录已保存 (#{comp_id})")
