"""Feedback dashboard with charts and recent records."""

import src.bootstrap  # noqa: F401

import streamlit as st
import pandas as pd
import plotly.express as px

from src.database import get_dashboard_stats, seed_demo_data_if_empty
from src.ui import setup_page
from src.utils import safe_metric_columns

setup_page("评测看板", "📈")

st.title("用户反馈与评测看板")
st.caption("汇总历史实验数据，洞察模型表现与常见问题。")

stats = get_dashboard_stats()

if stats["total_experiments"] == 0:
    st.info("暂无实验数据。请先在 Prompt 实验台、多模型对比或 RAG 评测中运行并保存记录。")
    if st.button("生成 Demo 数据", type="primary"):
        if seed_demo_data_if_empty():
            st.success("Demo 数据已生成")
        else:
            st.info("数据库已有数据，无需重复生成")
        st.rerun()
    st.stop()

safe_metric_columns(
    [
        ("平均评分", stats["avg_score"] if stats["avg_score"] is not None else "—"),
        ("总实验次数", stats["total_experiments"]),
        ("Prompt 版本数", stats["version_count"]),
        ("最近测试", stats["last_test_at"] or "—"),
    ]
)

st.divider()
c1, c2 = st.columns(2)

with c1:
    st.subheader("模型平均得分")
    if stats["model_scores"]:
        df_model = pd.DataFrame(stats["model_scores"])
        fig = px.bar(
            df_model,
            x="name",
            y="avg_score",
            text="avg_score",
            labels={"name": "模型", "avg_score": "平均得分"},
            color="avg_score",
            color_continuous_scale="Blues",
        )
        fig.update_layout(showlegend=False, height=360)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("暂无模型评分数据（请在多模型对比中保存人工评分）")

with c2:
    st.subheader("RAG 问题标签分布")
    if stats["tag_counts"]:
        df_tags = pd.DataFrame(stats["tag_counts"])
        fig2 = px.pie(
            df_tags,
            names="name",
            values="count",
            hole=0.35,
        )
        fig2.update_layout(height=360)
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.caption("暂无 RAG 问题标签（请在 RAG 评测中保存反馈）")

st.subheader("场景测试次数")
if stats["scene_counts"]:
    df_scene = pd.DataFrame(stats["scene_counts"])
    fig3 = px.bar(
        df_scene,
        x="name",
        y="count",
        labels={"name": "场景", "count": "测试次数"},
        color="count",
        color_continuous_scale="Teal",
    )
    fig3.update_layout(showlegend=False, height=320)
    st.plotly_chart(fig3, use_container_width=True)
else:
    st.caption("暂无 Prompt 场景数据")

st.subheader("最近实验记录")
if stats["recent_records"]:
    df_recent = pd.DataFrame(stats["recent_records"])
    df_recent = df_recent.rename(
        columns={
            "type": "类型",
            "detail": "详情",
            "model": "模型/问题",
            "created_at": "时间",
        }
    )
    st.dataframe(df_recent, use_container_width=True, hide_index=True)
else:
    st.caption("暂无记录")
