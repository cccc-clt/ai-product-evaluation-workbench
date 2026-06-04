"""RAG document Q&A evaluation page."""

import src.bootstrap  # noqa: F401

import streamlit as st

from src.config import get_session_settings
from src.database import save_rag_evaluation, save_user_feedback
from src.rag_engine import build_index, chunk_text, load_document, query_rag
from src.ui import render_generation_metadata, setup_page
from src.utils import RAG_ISSUE_TAGS, render_api_warning

setup_page("RAG 文档问答评测", "📄")

st.title("RAG 文档问答评测")
st.caption("上传 PDF/TXT，建立向量索引，评测检索增强问答效果。Embedding 模式请在侧边栏配置。")

api_ok = render_api_warning()
settings = get_session_settings()
temperature = settings.temperature
max_tokens = settings.max_tokens

uploaded = st.file_uploader("上传文档 (PDF / TXT)", type=["pdf", "txt"])

if uploaded:
    text, err = load_document(uploaded)
    if err:
        st.error(err)
    else:
        st.success(f"已解析文档「{uploaded.name}」，共 {len(text)} 字符")
        if st.button("建立向量索引", type="primary"):
            with st.spinner("切分文档并建立索引..."):
                chunks = chunk_text(text)
                doc_id, idx_err = build_index(uploaded.name, chunks)
            if idx_err:
                st.error(idx_err)
            else:
                st.session_state["rag_doc_id"] = doc_id
                st.session_state["rag_doc_name"] = uploaded.name
                st.session_state["rag_chunk_count"] = len(chunks)
                st.success(f"索引已建立，共 {len(chunks)} 个片段 (doc_id: {doc_id})")

if st.session_state.get("rag_doc_id"):
    st.info(
        f"当前文档: **{st.session_state.get('rag_doc_name')}** | "
        f"片段数: {st.session_state.get('rag_chunk_count', '—')}"
    )

    question = st.text_input("输入问题")
    model = st.text_input("回答模型", value=settings.model_name)

    if st.button("提问", type="primary", disabled=not api_ok):
        if not question.strip():
            st.error("请输入问题")
        else:
            with st.spinner("检索并生成回答..."):
                result = query_rag(
                    st.session_state["rag_doc_id"],
                    question,
                    model=model,
                    settings=settings,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            if result.error:
                st.error(result.error)
            else:
                st.session_state["last_rag"] = {
                    "doc_name": st.session_state.get("rag_doc_name", ""),
                    "question": question,
                    "model": result.model or model,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "answer": result.answer,
                    "citations": [
                        {"text": c.text, "source": c.source, "score": c.score}
                        for c in result.citations
                    ],
                    "latency_ms": result.latency_ms,
                    "input_tokens": result.input_tokens,
                    "output_tokens": result.output_tokens,
                }
                st.success("回答已生成")

if "last_rag" in st.session_state:
    rag = st.session_state["last_rag"]
    st.divider()
    st.subheader("回答结果")
    render_generation_metadata(
        model=rag.get("model", settings.model_name),
        temperature=rag.get("temperature", temperature),
        max_tokens=rag.get("max_tokens", max_tokens),
        latency_ms=rag["latency_ms"],
        input_tokens=rag.get("input_tokens", 0),
        output_tokens=rag.get("output_tokens", 0),
    )
    st.markdown(rag["answer"])

    st.subheader("引用片段")
    for i, c in enumerate(rag["citations"], 1):
        with st.expander(f"片段 {i} — {c['source']} (相关度 {c['score']:.3f})"):
            st.text(c["text"])

    st.subheader("评测反馈")
    user_score = st.slider("用户评分 (1-5)", 1, 5, 3, key="rag_score")
    selected_tags = []
    tag_cols = st.columns(4)
    for i, tag in enumerate(RAG_ISSUE_TAGS):
        with tag_cols[i % 4]:
            if st.checkbox(tag, key=f"rag_tag_{tag}"):
                selected_tags.append(tag)

    if st.button("保存 RAG 评测记录"):
        row_id = save_rag_evaluation(
            doc_name=rag["doc_name"],
            question=rag["question"],
            answer=rag["answer"],
            citations=rag["citations"],
            tags=selected_tags,
            user_score=user_score,
            latency_ms=rag["latency_ms"],
            temperature=rag.get("temperature"),
            max_tokens=rag.get("max_tokens"),
        )
        save_user_feedback(
            source_type="rag",
            source_id=row_id,
            score=user_score,
            tags=selected_tags,
            comment=rag["question"],
        )
        st.success(f"评测记录已保存 (#{row_id})")
