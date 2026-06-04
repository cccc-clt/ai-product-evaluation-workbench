"""Collect evaluation context and build advisor prompts."""

from __future__ import annotations

import json
from typing import Any

from src.database import get_dashboard_stats, get_low_score_samples
from src.utils import count_tokens, estimate_cost, tags_from_json


def estimate_token_usage(text: str, model: str = "gpt-4o-mini") -> int:
    """Estimate token usage for evaluator workflows."""
    return count_tokens(text, model)


def estimate_api_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate API cost for evaluator workflows."""
    return estimate_cost(model, input_tokens, output_tokens)


def collect_optimization_context() -> dict[str, Any]:
    """Gather stats and low-score samples for the optimization advisor."""
    stats = get_dashboard_stats()
    low_samples = get_low_score_samples(threshold=3)
    return {
        "stats": stats,
        "low_samples": low_samples,
        "sample_count": len(low_samples),
    }


def build_advisor_prompt(context: dict[str, Any]) -> str:
    """Build user prompt for LLM optimization advice generation."""
    stats = context.get("stats", {})
    samples = context.get("low_samples", [])

    lines = [
        "# 评测数据摘要",
        f"- 总实验次数: {stats.get('total_experiments', 0)}",
        f"- 平均评分: {stats.get('avg_score', '暂无')}",
        f"- Prompt 版本数: {stats.get('version_count', 0)}",
        "",
        "## 各模型平均得分",
    ]
    for m in stats.get("model_scores", []):
        lines.append(f"- {m.get('name')}: {m.get('avg_score')} ({m.get('cnt')} 条)")

    lines.append("\n## 场景测试次数")
    for s in stats.get("scene_counts", []):
        lines.append(f"- {s.get('name')}: {s.get('count')}")

    lines.append("\n## RAG 问题标签分布")
    for t in stats.get("tag_counts", []):
        lines.append(f"- {t.get('name')}: {t.get('count')}")

    lines.append("\n## 低分样本（评分 < 3）")
    if not samples:
        lines.append("暂无低分样本，请基于整体统计给出预防性优化建议。")
    else:
        for i, s in enumerate(samples[:15], 1):
            tags = s.get("tags")
            if isinstance(tags, str):
                tags = tags_from_json(tags)
            tag_str = ", ".join(tags) if tags else "无"
            lines.append(
                f"\n### 样本 {i} [{s.get('source_type')}]"
                f"\n- 标签/场景: {s.get('label', '')}"
                f"\n- 评分: {s.get('human_score', s.get('user_score', ''))}"
                f"\n- 问题标签: {tag_str}"
                f"\n- 备注: {s.get('notes', '')}"
                f"\n- 内容摘要: {(s.get('response') or '')[:300]}"
            )

    lines.append(
        "\n请根据以上数据，输出五类可执行的优化建议（Prompt、模型、参数、RAG、产品体验）。"
    )
    return "\n".join(lines)


def parse_advice_sections(content: str) -> dict[str, str]:
    """Split markdown advice into five sections by heading."""
    sections = {
        "prompt": "",
        "model": "",
        "params": "",
        "rag": "",
        "product": "",
    }
    keys = [
        ("prompt", "Prompt 优化"),
        ("model", "模型选择"),
        ("params", "参数调整"),
        ("rag", "RAG 检索"),
        ("product", "产品体验"),
    ]
    current = None
    buffer: list[str] = []

    for line in (content or "").splitlines():
        matched = False
        for key, title in keys:
            if title in line and line.strip().startswith("#"):
                if current:
                    sections[current] = "\n".join(buffer).strip()
                current = key
                buffer = []
                matched = True
                break
        if not matched and current:
            buffer.append(line)

    if current:
        sections[current] = "\n".join(buffer).strip()

    if not any(sections.values()):
        sections["prompt"] = content

    return sections
