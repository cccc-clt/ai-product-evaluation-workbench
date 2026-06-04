"""AI-powered optimization advisor page."""

import src.bootstrap  # noqa: F401

import streamlit as st

from src.config import get_session_settings
from src.database import save_optimization_report
from src.evaluator import (
    build_advisor_prompt,
    collect_optimization_context,
    parse_advice_sections,
)
from src.llm_client import generate_optimization_advice
from src.ui import setup_page
from src.utils import render_api_warning

setup_page("AI 优化建议", "💡")

st.title("AI 自动优化建议")
st.caption("基于低分样本与用户反馈，自动生成 Prompt、模型、RAG 与产品体验优化建议。")

api_ok = render_api_warning()
settings = get_session_settings()

context = collect_optimization_context()
stats = context["stats"]

st.subheader("数据摘要")
m1, m2, m3 = st.columns(3)
m1.metric("总实验次数", stats.get("total_experiments", 0))
m2.metric("低分样本数", context["sample_count"])
m3.metric("平均评分", stats.get("avg_score") or "—")

if stats.get("tag_counts"):
    st.markdown(
        "**高频问题标签:** "
        + ", ".join(f"{t['name']}({t['count']})" for t in stats["tag_counts"][:5])
    )

if st.button("生成优化建议", type="primary", disabled=not api_ok):
    with st.spinner("分析评测数据并生成建议..."):
        prompt = build_advisor_prompt(context)
        content, err = generate_optimization_advice(prompt, settings)
    if err:
        st.error(err)
    else:
        st.session_state["advisor_content"] = content
        st.session_state["advisor_sample_count"] = context["sample_count"]
        st.success("优化建议已生成")

if "advisor_content" in st.session_state:
    content = st.session_state["advisor_content"]
    sections = parse_advice_sections(content)

    st.divider()
    tabs = st.tabs(
        [
            "Prompt 优化",
            "模型选择",
            "参数调整",
            "RAG 检索",
            "产品体验",
            "完整报告",
        ]
    )
    labels = [
        ("prompt", "Prompt 优化建议"),
        ("model", "模型选择建议"),
        ("params", "参数调整建议"),
        ("rag", "RAG 检索优化建议"),
        ("product", "产品体验优化建议"),
    ]
    for tab, (key, title) in zip(tabs[:5], labels):
        with tab:
            body = sections.get(key, "")
            if body:
                st.markdown(body)
            else:
                st.caption(f"未解析到「{title}」章节，请查看完整报告。")

    with tabs[5]:
        st.markdown(content)

    if st.button("保存优化报告"):
        rid = save_optimization_report(
            content,
            st.session_state.get("advisor_sample_count", 0),
        )
        st.success(f"报告已保存 (#{rid})")
