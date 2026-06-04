"""RAG pipeline: document parsing, chunking, indexing, and Q&A."""

from __future__ import annotations

import hashlib
import io
import re
import uuid
from dataclasses import dataclass, field
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from src.config import CHROMA_PATH, get_session_settings
from src.llm_client import chat, embed_texts


@dataclass
class Citation:
    """A retrieved document chunk used as context."""

    text: str
    source: str
    score: float = 0.0


@dataclass
class RAGResult:
    """Result of a RAG query."""

    answer: str
    citations: list[Citation] = field(default_factory=list)
    latency_ms: float = 0
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.error is None


def load_document(uploaded_file) -> tuple[str, str | None]:
    """Extract text from uploaded PDF or TXT file."""
    if uploaded_file is None:
        return "", "未选择文件"

    name = (uploaded_file.name or "").lower()
    try:
        if hasattr(uploaded_file, "seek"):
            uploaded_file.seek(0)
        raw = uploaded_file.read()
        if not raw:
            return "", "文件为空，请上传有效文档"

        if name.endswith(".txt"):
            for enc in ("utf-8", "gbk", "latin-1"):
                try:
                    return raw.decode(enc), None
                except UnicodeDecodeError:
                    continue
            return "", "无法解码文本文件"

        if name.endswith(".pdf"):
            import pdfplumber

            text_parts = []
            with pdfplumber.open(io.BytesIO(raw)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            text = "\n\n".join(text_parts).strip()
            if not text:
                return "", "PDF 中未提取到文本，可能是扫描件或图片 PDF"
            return text, None

        return "", "仅支持 PDF 或 TXT 格式"
    except Exception as exc:
        return "", f"文档解析失败: {exc}"


def chunk_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[str]:
    """Split text into overlapping chunks by character count."""
    text = re.sub(r"\s+", " ", (text or "").strip())
    if not text:
        return []
    chunk_size = max(1, int(chunk_size or 500))
    overlap = max(0, int(overlap or 0))
    if overlap >= chunk_size:
        overlap = max(0, chunk_size - 1)
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = end - overlap
    return chunks


def _doc_collection_name(doc_id: str) -> str:
    """Sanitize collection name for Chroma."""
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", doc_id)[:60]
    return f"doc_{safe}"


def _get_chroma_client():
    """Return persistent Chroma client."""
    CHROMA_PATH.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(
        path=str(CHROMA_PATH),
        settings=ChromaSettings(anonymized_telemetry=False),
    )


def build_index(
    doc_name: str,
    chunks: list[str],
    doc_id: str | None = None,
) -> tuple[str, str | None]:
    """Embed chunks and store in ChromaDB. Returns doc_id."""
    if not chunks:
        return "", "文档切分后无有效片段"

    doc_id = doc_id or hashlib.md5(doc_name.encode()).hexdigest()[:12]
    settings = get_session_settings()
    vectors, err = embed_texts(chunks, settings)
    if err:
        return "", err
    if len(vectors) != len(chunks):
        return "", "Embedding 数量与文本块不匹配"

    try:
        client = _get_chroma_client()
        coll_name = _doc_collection_name(doc_id)
        try:
            client.delete_collection(coll_name)
        except Exception:
            pass
        collection = client.create_collection(name=coll_name)
        ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
        collection.add(
            ids=ids,
            embeddings=vectors,
            documents=chunks,
            metadatas=[{"source": doc_name, "index": i} for i in range(len(chunks))],
        )
        return doc_id, None
    except Exception as exc:
        return "", f"向量索引构建失败: {exc}"


def retrieve(
    doc_id: str,
    question: str,
    top_k: int = 3,
) -> tuple[list[Citation], str | None]:
    """Retrieve top-k similar chunks for a question."""
    settings = get_session_settings()
    q_vectors, err = embed_texts([question], settings)
    if err:
        return [], err

    try:
        client = _get_chroma_client()
        coll_name = _doc_collection_name(doc_id)
        collection = client.get_collection(coll_name)
        results = collection.query(
            query_embeddings=q_vectors,
            n_results=min(top_k, 10),
        )
        citations = []
        docs = results.get("documents") or [[]]
        metas = results.get("metadatas") or [[]]
        dists = results.get("distances") or [[]]
        for i, doc in enumerate(docs[0] if docs else []):
            meta = metas[0][i] if metas and metas[0] else {}
            dist = dists[0][i] if dists and dists[0] else 0
            score = 1.0 / (1.0 + float(dist)) if dist is not None else 0.0
            citations.append(
                Citation(
                    text=doc,
                    source=meta.get("source", doc_id),
                    score=score,
                )
            )
        return citations, None
    except Exception as exc:
        return [], f"检索失败: {exc}（请先上传文档并建立索引）"


RAG_SYSTEM = """你是基于给定文档片段回答问题的助手。
规则：
1. 仅根据提供的引用片段回答，不要编造文档中不存在的信息。
2. 若片段不足以回答，请明确说明。
3. 回答末尾用【引用】列出使用到的片段编号。"""


def query_rag(
    doc_id: str,
    question: str,
    model: str | None = None,
    top_k: int = 3,
) -> RAGResult:
    """Retrieve context and generate an answer with citations."""
    import time

    citations, err = retrieve(doc_id, question, top_k)
    if err:
        return RAGResult(answer="", error=err)

    if not citations:
        return RAGResult(answer="", error="未检索到相关文档片段")

    context_blocks = []
    for i, c in enumerate(citations, 1):
        context_blocks.append(f"[片段{i}] ({c.source})\n{c.text}")
    context = "\n\n".join(context_blocks)
    user_msg = f"引用片段：\n{context}\n\n用户问题：{question}"

    start = time.perf_counter()
    result = chat(
        system_prompt=RAG_SYSTEM,
        user_prompt=user_msg,
        model=model,
        temperature=0.3,
        max_tokens=1024,
    )
    latency = (time.perf_counter() - start) * 1000

    if result.error:
        return RAGResult(answer="", citations=citations, error=result.error)

    return RAGResult(
        answer=result.content,
        citations=citations,
        latency_ms=latency,
    )


def new_doc_id() -> str:
    """Generate a unique document session id."""
    return uuid.uuid4().hex[:12]
