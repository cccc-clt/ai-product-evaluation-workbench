"""AI Product Evaluation Workbench — home page and global settings."""

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.database import init_db
from src.ui import init_session_defaults, render_sidebar

st.set_page_config(
    page_title="AI Product Evaluation Workbench",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()
init_session_defaults()
render_sidebar()

st.title("AI Product Evaluation Workbench")
st.subheader("大模型应用评测与 Prompt 优化平台")

st.markdown(
    """
面向 **AI 产品经理、开发者与企业用户**，提供大模型应用上线前的完整评测与迭代闭环：

| 模块 | 能力 |
|------|------|
| **Prompt 实验台** | 多业务场景 Prompt 调试、版本记录、成本估算 |
| **多模型对比** | 同一问题横向评测多个模型，人工打分 |
| **RAG 文档问答评测** | PDF/TXT 上传、向量检索、引用溯源、问题标签 |
| **评测看板** | 聚合实验数据、图表洞察、最近记录 |
| **AI 优化建议** | 基于低分样本自动生成结构化优化方案 |

---
**使用方式：** 请从左侧导航栏进入各功能页面。首次使用请在侧边栏配置 API Key 与 Base URL。
"""
)

col1, col2, col3 = st.columns(3)
with col1:
    st.info("**Step 1** — 在 Prompt 实验台调试 Prompt")
with col2:
    st.info("**Step 2** — 多模型对比选出最优模型")
with col3:
    st.info("**Step 3** — RAG 评测 + 看板分析 + AI 优化建议")

st.markdown("---")
st.caption(
    "Built for AI Product Internship Demo · Compatible with OpenAI-compatible APIs (e.g. 火山方舟)"
)
