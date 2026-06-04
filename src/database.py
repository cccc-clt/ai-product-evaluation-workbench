"""SQLite persistence for experiments, comparisons, and RAG evaluations."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from src.config import DATA_DIR, DB_PATH
from src.utils import tags_from_json, tags_to_json


def ensure_data_dir() -> None:
    """Create data directory if missing."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_connection():
    """Yield a SQLite connection with row factory."""
    ensure_data_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Create all tables if they do not exist."""
    ensure_data_dir()
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS prompt_experiments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scene TEXT NOT NULL,
                system_prompt TEXT,
                user_prompt TEXT,
                model TEXT,
                temperature REAL,
                max_tokens INTEGER,
                response TEXT,
                latency_ms REAL,
                input_tokens INTEGER,
                output_tokens INTEGER,
                cost REAL,
                version TEXT,
                human_score INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS model_comparisons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                temperature REAL,
                max_tokens INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS model_comparison_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                comparison_id INTEGER NOT NULL,
                model TEXT NOT NULL,
                response TEXT,
                latency_ms REAL,
                input_tokens INTEGER,
                output_tokens INTEGER,
                cost REAL,
                human_score INTEGER,
                notes TEXT,
                FOREIGN KEY (comparison_id) REFERENCES model_comparisons(id)
            );

            CREATE TABLE IF NOT EXISTS rag_evaluations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_name TEXT,
                question TEXT,
                answer TEXT,
                citations_json TEXT,
                tags TEXT,
                user_score INTEGER,
                latency_ms REAL,
                temperature REAL,
                max_tokens INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS user_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_type TEXT NOT NULL,
                source_id INTEGER,
                score INTEGER,
                tags TEXT,
                comment TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS optimization_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT,
                sample_count INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        _migrate_schema(conn)


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    """Return True if a column exists on the given table."""
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row[1] == column for row in rows)


def _migrate_schema(conn: sqlite3.Connection) -> None:
    """Add missing columns to existing databases without breaking data."""
    migrations = [
        ("model_comparisons", "temperature", "REAL"),
        ("model_comparisons", "max_tokens", "INTEGER"),
        ("rag_evaluations", "temperature", "REAL"),
        ("rag_evaluations", "max_tokens", "INTEGER"),
    ]
    for table, column, col_type in migrations:
        if not _column_exists(conn, table, column):
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")


def _now_version() -> str:
    """Generate prompt version string from timestamp."""
    return datetime.now().strftime("v%Y%m%d.%H%M%S")


def save_prompt_experiment(
    scene: str,
    system_prompt: str,
    user_prompt: str,
    model: str,
    temperature: float,
    max_tokens: int,
    response: str,
    latency_ms: float,
    input_tokens: int,
    output_tokens: int,
    cost: float,
    version: str | None = None,
    human_score: int | None = None,
) -> int:
    """Insert a prompt experiment record."""
    init_db()
    ver = version or _now_version()
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO prompt_experiments (
                scene, system_prompt, user_prompt, model, temperature, max_tokens,
                response, latency_ms, input_tokens, output_tokens, cost, version, human_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                scene,
                system_prompt,
                user_prompt,
                model,
                temperature,
                max_tokens,
                response,
                latency_ms,
                input_tokens,
                output_tokens,
                cost,
                ver,
                human_score,
            ),
        )
        return cur.lastrowid or 0


def save_model_comparison(
    question: str,
    items: list[dict[str, Any]],
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> int:
    """Save comparison header and per-model items."""
    init_db()
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO model_comparisons (question, temperature, max_tokens)
            VALUES (?, ?, ?)
            """,
            (question, temperature, max_tokens),
        )
        comp_id = cur.lastrowid or 0
        for item in items:
            conn.execute(
                """
                INSERT INTO model_comparison_items (
                    comparison_id, model, response, latency_ms,
                    input_tokens, output_tokens, cost, human_score, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    comp_id,
                    item.get("model", ""),
                    item.get("response", ""),
                    item.get("latency_ms", 0),
                    item.get("input_tokens", 0),
                    item.get("output_tokens", 0),
                    item.get("cost", 0),
                    item.get("human_score"),
                    item.get("notes", ""),
                ),
            )
        return comp_id


def save_rag_evaluation(
    doc_name: str,
    question: str,
    answer: str,
    citations: list[dict[str, Any]],
    tags: list[str],
    user_score: int | None,
    latency_ms: float = 0,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> int:
    """Insert RAG evaluation record."""
    init_db()
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO rag_evaluations (
                doc_name, question, answer, citations_json, tags, user_score,
                latency_ms, temperature, max_tokens
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                doc_name,
                question,
                answer,
                json.dumps(citations, ensure_ascii=False),
                tags_to_json(tags),
                user_score,
                latency_ms,
                temperature,
                max_tokens,
            ),
        )
        return cur.lastrowid or 0


def save_user_feedback(
    source_type: str,
    source_id: int | None = None,
    score: int | None = None,
    tags: list[str] | None = None,
    comment: str = "",
) -> int:
    """Insert a normalized user feedback record."""
    init_db()
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO user_feedback (source_type, source_id, score, tags, comment)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                source_type,
                source_id,
                score,
                tags_to_json(tags or []),
                comment,
            ),
        )
        return cur.lastrowid or 0


def save_optimization_report(content: str, sample_count: int) -> int:
    """Save generated optimization report."""
    init_db()
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO optimization_reports (content, sample_count) VALUES (?, ?)",
            (content, sample_count),
        )
        return cur.lastrowid or 0


def seed_demo_data_if_empty() -> bool:
    """Create a small demo dataset when the database has no experiments."""
    init_db()
    stats = get_dashboard_stats()
    if stats["total_experiments"] > 0:
        return False

    prompt_id = save_prompt_experiment(
        scene="客服问答",
        system_prompt="你是专业、耐心的客服助手，请给出准确、简洁、友好的回答。",
        user_prompt="用户询问会员退款规则，请说明处理流程。",
        model="gpt-4o-mini",
        temperature=0.7,
        max_tokens=512,
        response="建议先确认订单状态、会员权益使用情况和退款窗口，再引导用户提交退款申请。",
        latency_ms=820,
        input_tokens=96,
        output_tokens=138,
        cost=0.00012,
        version="demo-v1",
        human_score=4,
    )
    save_user_feedback(
        source_type="prompt",
        source_id=prompt_id,
        score=4,
        tags=["回答清晰"],
        comment="适合作为客服 Prompt 基线。",
    )

    compare_id = save_model_comparison(
        question="请为上海三日游生成一个面向年轻用户的行程建议。",
        temperature=0.7,
        max_tokens=1024,
        items=[
            {
                "model": "gpt-4o-mini",
                "response": "给出了外滩、武康路、博物馆和美食路线，结构清晰。",
                "latency_ms": 940,
                "input_tokens": 88,
                "output_tokens": 220,
                "cost": 0.00018,
                "human_score": 4,
                "notes": "节奏合理，但预算信息偏少。",
            },
            {
                "model": "demo-fast-model",
                "response": "回答较短，缺少交通和时间安排。",
                "latency_ms": 510,
                "input_tokens": 88,
                "output_tokens": 92,
                "cost": 0.00008,
                "human_score": 2,
                "notes": "信息密度不足。",
            },
        ],
    )
    save_user_feedback(
        source_type="compare",
        source_id=compare_id,
        score=2,
        tags=["回答太短"],
        comment="低分样本可用于优化模型选择和输出格式。",
    )

    rag_id = save_rag_evaluation(
        doc_name="demo_policy.txt",
        question="企业知识库答案是否准确引用退款规则？",
        answer="答案引用了退款规则，但缺少具体条款编号，需要补充来源说明。",
        citations=[
            {
                "text": "会员服务在开通后 7 天内且未使用权益时可申请退款。",
                "source": "demo_policy.txt",
                "score": 0.86,
            }
        ],
        tags=["引用错误", "回答太泛"],
        user_score=2,
        latency_ms=760,
        temperature=0.7,
        max_tokens=1024,
    )
    save_user_feedback(
        source_type="rag",
        source_id=rag_id,
        score=2,
        tags=["引用错误", "回答太泛"],
        comment="需要加强引用溯源和答案约束。",
    )

    save_optimization_report(
        content=(
            "## Prompt 优化建议\n增加输出格式和引用要求。\n\n"
            "## 模型选择建议\n保留质量较高模型作为基线，对低分模型增加验证。\n\n"
            "## 参数调整建议\n降低温度以提升政策类回答稳定性。\n\n"
            "## RAG 检索优化建议\n提高 top_k 并展示引用片段编号。\n\n"
            "## 产品体验优化建议\n在看板突出低分标签和最近失败样本。"
        ),
        sample_count=2,
    )
    return True


def get_prompt_version_count() -> int:
    """Count distinct prompt versions."""
    init_db()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(DISTINCT version) AS c FROM prompt_experiments"
        ).fetchone()
        return int(row["c"]) if row else 0


def get_low_score_samples(threshold: int = 3) -> list[dict[str, Any]]:
    """Collect samples with human score below threshold."""
    init_db()
    samples: list[dict[str, Any]] = []

    with get_connection() as conn:
        for row in conn.execute(
            """
            SELECT 'prompt' AS source_type, id, scene AS label, response, human_score, version
            FROM prompt_experiments
            WHERE human_score IS NOT NULL AND human_score < ?
            ORDER BY created_at DESC LIMIT 20
            """,
            (threshold,),
        ):
            samples.append(dict(row))

        for row in conn.execute(
            """
            SELECT 'compare' AS source_type, id, model AS label, response, human_score, notes
            FROM model_comparison_items
            WHERE human_score IS NOT NULL AND human_score < ?
            ORDER BY id DESC LIMIT 20
            """,
            (threshold,),
        ):
            samples.append(dict(row))

        for row in conn.execute(
            """
            SELECT 'rag' AS source_type, id, doc_name AS label, answer AS response,
                   user_score AS human_score, tags
            FROM rag_evaluations
            WHERE user_score IS NOT NULL AND user_score < ?
            ORDER BY created_at DESC LIMIT 20
            """,
            (threshold,),
        ):
            d = dict(row)
            d["tags"] = tags_from_json(d.get("tags"))
            samples.append(d)

    return samples


def get_dashboard_stats() -> dict[str, Any]:
    """Aggregate statistics for the feedback dashboard."""
    init_db()
    stats: dict[str, Any] = {
        "avg_score": None,
        "total_experiments": 0,
        "prompt_count": 0,
        "compare_count": 0,
        "rag_count": 0,
        "version_count": 0,
        "last_test_at": None,
        "model_scores": [],
        "scene_counts": [],
        "tag_counts": [],
        "recent_records": [],
    }

    with get_connection() as conn:
        stats["prompt_count"] = conn.execute(
            "SELECT COUNT(*) AS c FROM prompt_experiments"
        ).fetchone()["c"]
        stats["compare_count"] = conn.execute(
            "SELECT COUNT(*) AS c FROM model_comparisons"
        ).fetchone()["c"]
        stats["rag_count"] = conn.execute(
            "SELECT COUNT(*) AS c FROM rag_evaluations"
        ).fetchone()["c"]
        stats["total_experiments"] = (
            stats["prompt_count"] + stats["compare_count"] + stats["rag_count"]
        )
        stats["version_count"] = get_prompt_version_count()

        scores = []
        for row in conn.execute(
            "SELECT human_score FROM prompt_experiments WHERE human_score IS NOT NULL"
        ):
            scores.append(row["human_score"])
        for row in conn.execute(
            "SELECT human_score FROM model_comparison_items WHERE human_score IS NOT NULL"
        ):
            scores.append(row["human_score"])
        for row in conn.execute(
            "SELECT user_score FROM rag_evaluations WHERE user_score IS NOT NULL"
        ):
            scores.append(row["user_score"])
        if scores:
            stats["avg_score"] = round(sum(scores) / len(scores), 2)

        stats["model_scores"] = [
            dict(r)
            for r in conn.execute(
                """
                SELECT model AS name, ROUND(AVG(human_score), 2) AS avg_score, COUNT(*) AS cnt
                FROM model_comparison_items
                WHERE human_score IS NOT NULL
                GROUP BY model
                ORDER BY avg_score DESC
                """
            )
        ]

        stats["scene_counts"] = [
            dict(r)
            for r in conn.execute(
                """
                SELECT scene AS name, COUNT(*) AS count
                FROM prompt_experiments
                GROUP BY scene
                ORDER BY count DESC
                """
            )
        ]

        tag_map: dict[str, int] = {}
        for row in conn.execute("SELECT tags FROM rag_evaluations WHERE tags IS NOT NULL"):
            for tag in tags_from_json(row["tags"]):
                tag_map[tag] = tag_map.get(tag, 0) + 1
        for row in conn.execute("SELECT tags FROM user_feedback WHERE tags IS NOT NULL"):
            for tag in tags_from_json(row["tags"]):
                tag_map[tag] = tag_map.get(tag, 0) + 1
        stats["tag_counts"] = [
            {"name": k, "count": v}
            for k, v in sorted(tag_map.items(), key=lambda x: -x[1])
        ]

        recent = []
        for row in conn.execute(
            """
            SELECT 'Prompt 实验' AS type, scene AS detail, model, created_at
            FROM prompt_experiments ORDER BY created_at DESC LIMIT 10
            """
        ):
            recent.append(dict(row))
        for row in conn.execute(
            """
            SELECT '多模型对比' AS type, question AS detail, '' AS model, created_at
            FROM model_comparisons ORDER BY created_at DESC LIMIT 5
            """
        ):
            recent.append(dict(row))
        for row in conn.execute(
            """
            SELECT 'RAG 评测' AS type, doc_name AS detail, question AS model, created_at
            FROM rag_evaluations ORDER BY created_at DESC LIMIT 5
            """
        ):
            recent.append(dict(row))
        for row in conn.execute(
            """
            SELECT '用户反馈' AS type, source_type AS detail, comment AS model, created_at
            FROM user_feedback ORDER BY created_at DESC LIMIT 5
            """
        ):
            recent.append(dict(row))
        recent.sort(key=lambda x: x.get("created_at") or "", reverse=True)
        stats["recent_records"] = recent[:20]

        last_rows = []
        for tbl in ("prompt_experiments", "model_comparisons", "rag_evaluations"):
            r = conn.execute(f"SELECT MAX(created_at) AS t FROM {tbl}").fetchone()
            if r and r["t"]:
                last_rows.append(r["t"])
        if last_rows:
            stats["last_test_at"] = max(last_rows)

    return stats
