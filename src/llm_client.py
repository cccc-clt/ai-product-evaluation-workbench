"""OpenAI-compatible LLM client with chat and embedding support."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from openai import OpenAI

from src.config import Settings, get_session_settings, is_api_configured
from src.utils import count_tokens, estimate_tokens_fallback


@dataclass
class ChatResult:
    """Result of a chat completion call."""

    content: str
    latency_ms: float
    input_tokens: int
    output_tokens: int
    model: str
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.error is None


def _build_client(settings: Settings) -> OpenAI | None:
    """Create OpenAI client if API is configured."""
    if not is_api_configured(settings):
        return None
    return OpenAI(base_url=settings.base_url, api_key=settings.api_key)


def chat_completion(
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    settings: Settings | None = None,
) -> ChatResult:
    """Call chat completions API and return structured result."""
    s = settings or get_session_settings()
    model_name = model or s.model_name
    temp = s.temperature if temperature is None else temperature
    max_tok = s.max_tokens if max_tokens is None else max_tokens

    if not is_api_configured(s):
        return ChatResult(
            content="",
            latency_ms=0,
            input_tokens=0,
            output_tokens=0,
            model=model_name,
            error="API Key 未配置，请在侧边栏或 .env 中设置 API_KEY。",
        )

    client = _build_client(s)
    messages = [
        {"role": "system", "content": system_prompt or "You are a helpful assistant."},
        {"role": "user", "content": user_prompt},
    ]
    inp_est = count_tokens(system_prompt + user_prompt, model_name)

    try:
        start = time.perf_counter()
        if client is None:
            return ChatResult(
                content="",
                latency_ms=0,
                input_tokens=inp_est,
                output_tokens=0,
                model=model_name,
                error="API Key 未配置，请在侧边栏或 .env 中设置 API_KEY。",
            )

        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=temp,
            max_tokens=max_tok,
        )
        latency_ms = (time.perf_counter() - start) * 1000
        choices = getattr(response, "choices", None) or []
        if not choices:
            return ChatResult(
                content="",
                latency_ms=latency_ms,
                input_tokens=inp_est,
                output_tokens=0,
                model=model_name,
                error="API 返回为空，未生成可用回答。",
            )
        message = getattr(choices[0], "message", None)
        content = (getattr(message, "content", "") or "").strip()
        if not content:
            return ChatResult(
                content="",
                latency_ms=latency_ms,
                input_tokens=inp_est,
                output_tokens=0,
                model=model_name,
                error="API 返回内容为空，请检查模型名称或提示词。",
            )
        usage = getattr(response, "usage", None)
        if usage:
            inp = usage.prompt_tokens or inp_est
            out = usage.completion_tokens or count_tokens(content, model_name)
        else:
            inp = inp_est
            out = count_tokens(content, model_name)
        return ChatResult(
            content=content,
            latency_ms=latency_ms,
            input_tokens=inp,
            output_tokens=out,
            model=model_name,
        )
    except Exception as exc:
        return ChatResult(
            content="",
            latency_ms=0,
            input_tokens=inp_est,
            output_tokens=0,
            model=model_name,
            error=f"API 调用失败: {exc}",
        )


def chat(
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    settings: Settings | None = None,
) -> ChatResult:
    """Backward-compatible alias for chat_completion."""
    return chat_completion(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        settings=settings,
    )


def embed_texts(
    texts: list[str],
    settings: Settings | None = None,
) -> tuple[list[list[float]], str | None]:
    """Embed texts via API or local sentence-transformers."""
    s = settings or get_session_settings()
    if not texts:
        return [], None

    mode = (s.embedding_mode or "api").lower()

    if mode == "local":
        try:
            from sentence_transformers import SentenceTransformer

            model = SentenceTransformer(s.local_embedding_model)
            vectors = model.encode(texts, show_progress_bar=False)
            return [v.tolist() for v in vectors], None
        except Exception as exc:
            return [], f"本地 Embedding 失败: {exc}"

    if not is_api_configured(s):
        return [], "API Key 未配置，无法使用 API Embedding。"

    try:
        client = _build_client(s)
        response = client.embeddings.create(
            model=s.embedding_model,
            input=texts,
        )
        ordered = sorted(response.data, key=lambda x: x.index)
        return [item.embedding for item in ordered], None
    except Exception as exc:
        return [], f"Embedding API 失败: {exc}"


def generate_optimization_advice(
    context: str,
    settings: Settings | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> tuple[str, str | None, ChatResult | None]:
    """Generate structured optimization advice from evaluation context."""
    s = settings or get_session_settings()
    system = """你是一名资深 AI 产品经理与技术顾问。
根据用户提供的评测数据与反馈，输出结构化的优化建议。
请使用 Markdown，并严格包含以下五个二级标题（##）：
## Prompt 优化建议
## 模型选择建议
## 参数调整建议
## RAG 检索优化建议
## 产品体验优化建议
每条建议要具体、可执行，结合数据中的实际问题。"""
    result = chat(
        system_prompt=system,
        user_prompt=context,
        model=s.model_name,
        temperature=temperature,
        max_tokens=max_tokens,
        settings=s,
    )
    if result.error:
        return "", result.error, result
    return result.content, None, result
