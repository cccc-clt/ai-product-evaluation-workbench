# AGENTS.md

本文件用于约束 **Cursor、Codex、Claude Code** 等 AI 编程助手在本仓库中的行为。开始修改代码前请先阅读全文。

---

## 1. 项目背景

**AI Product Evaluation Workbench**（中文名：大模型应用评测与 Prompt 优化平台）是一个面向 AI 产品经理、开发者与企业用户的 Streamlit Web 应用。

项目目标：

- 模拟大模型应用**上线前**的评测与迭代流程；
- 展示实习候选人在 **产品设计、Prompt Engineering、RAG、模型评测、用户反馈分析、AI 应用开发** 方面的能力；
- 提供可本地运行、可部署到 **Streamlit Cloud** 的产品化 Demo。

核心用户流程：配置 API → Prompt 实验 → 多模型对比 → RAG 评测 → 保存反馈 → 评测看板 → AI 优化建议。

---

## 2. 技术栈

| 类别 | 技术 |
|------|------|
| 语言 | Python 3.10+ |
| Web UI | Streamlit（多页面：`app.py` + `pages/`） |
| 持久化 | SQLite（`data/workbench.db`） |
| LLM 调用 | OpenAI-compatible API（`openai` SDK，`BASE_URL` + `API_KEY`） |
| 向量检索 | **ChromaDB**（首选；勿随意改为 FAISS，除非有明确理由且更新文档） |
| 数据处理 | Pandas |
| 图表 | Plotly |
| 配置 | python-dotenv（`.env`，示例见 `.env.example`） |
| 文档解析 | pdfplumber（PDF）、内置 TXT 解码 |
| Embedding | API 模式或本地 `sentence-transformers`（侧边栏可切换） |

依赖清单以 [`requirements.txt`](requirements.txt) 为准。

---

## 3. 开发原则

1. **优先保证项目可以运行** — MVP 可演示优于架构完美。
2. **不要过度工程化** — 避免为单一场景引入抽象层、微服务或重型 ORM。
3. **不要把所有代码写在 `app.py`** — 业务逻辑放在 `src/`，页面放在 `pages/`。
4. **不要硬编码 API Key** — 使用环境变量或 Streamlit 侧边栏 / Secrets。
5. **修改前先阅读现有项目结构** — 复用 `src/config.py`、`src/llm_client.py`、`src/database.py`、`src/ui.py` 等模块。
6. **每次修改后说明变更点** — 简要列出改了哪些文件、为什么改。
7. **不确定依赖时** — 选择稳定、轻量、容易在 Windows 与 Streamlit Cloud 上安装的方案。
8. **所有新增功能必须兼容 Streamlit Cloud** — 避免依赖本地 GPU、长期后台进程或不可持久化的临时路径（说明 Chroma/SQLite 在 Cloud 重启后会重置的限制即可）。

---

## 4. 代码规范

- **函数命名清晰**，使用英文 snake_case；模块职责单一。
- **核心函数加简短注释**（说明用途即可，非显而易见逻辑才详写）。
- **API 调用必须有异常处理** — 返回用户可读错误信息，参考 `src/llm_client.py`。
- **数据库操作必须可重复执行** — 通过 `init_db()` 建表，避免假设表已存在。
- **文件上传与空数据** — 必须有友好提示，禁止未捕获异常导致页面崩溃。
- **页面文案** — 中文为主，必要处保留英文术语（如 Prompt、RAG、Token、API Key）。
- **页面入口** — 子页面应调用 `src/ui.py` 中的 `setup_page()`，保证侧边栏全局配置一致。
- **路径引导** — 新页面在 `pages/` 下命名遵循 `N_模块名.py`，保证 Streamlit 自动导航。

---

## 5. 项目核心模块

修改或扩展功能时，请保持以下模块边界：

| 模块 | 路径 | 职责 |
|------|------|------|
| Prompt 实验台 | `pages/1_prompt_lab.py` | 场景模板、System/User Prompt、参数、成本估算、实验保存 |
| 多模型效果对比 | `pages/2_model_compare.py` | 同一问题多模型调用、人工评分、对比记录 |
| RAG 文档问答评测 | `pages/3_rag_evaluation.py` + `src/rag_engine.py` | 上传 PDF/TXT、分块、向量索引、引用溯源、问题标签 |
| 用户反馈与评测看板 | `pages/4_feedback_dashboard.py` | 聚合统计、Plotly 图表、最近记录 |
| AI 自动优化建议 | `pages/5_optimization_advisor.py` + `src/evaluator.py` | 低分样本分析、结构化优化建议 |
| 首页与全局配置 | `app.py` + `src/ui.py` | 项目介绍、侧边栏 API/Embedding 配置 |
| 产品文档 | `docs/*.md` | PRD、用户研究、评测框架 |
| 项目说明 | `README.md` | 安装、环境变量、部署、岗位匹配说明 |

冒烟测试脚本：[`scripts/verify.py`](scripts/verify.py)（无 API Key 也可运行部分检查）。

---

## 6. 禁止事项

- **禁止删除已有功能**（可标记废弃，须保留或迁移等价能力）。
- **禁止提交真实 API Key** — 不得写入代码、`.env`、截图或文档；仅使用 `.env.example` 占位符。
- **禁止引入大型复杂框架**（如 LangChain 全栈、Django、FastAPI 替代 Streamlit 等），除非用户明确要求且同步更新 README。
- **禁止生成无法运行的伪代码** — 提交的代码应可导入、可启动。
- **禁止无说明地大规模重构** — 跨多目录重命名或重写须先说明动机与影响范围。
- **禁止修改 `AGENTS.md` 以削弱上述约束**，除非用户显式要求更新本文件。

---

## 7. 测试要求

每次修改后，AI 助手应至少完成以下检查（并向用户汇报结果）：

| 检查项 | 方式 |
|--------|------|
| Python import 正常 | `python scripts/verify.py` 或 `python -c "from src.database import init_db; init_db()"` |
| Streamlit 能启动 | `streamlit run app.py`（可短时验证无 traceback） |
| 数据库自动初始化 | 确认 `data/workbench.db` 可创建，`init_db()` 无报错 |
| 无 API Key 友好提示 | 各调用页显示 warning，按钮合理禁用 |
| 依赖完整 | 新增 import 的包已写入 `requirements.txt` |

若环境无法联网安装依赖，应说明限制，并保证代码结构与上述规范一致。

---

## 8. 推荐目录结构

```
├── app.py                 # 首页
├── AGENTS.md              # 本文件
├── requirements.txt
├── .env.example
├── src/                   # 核心业务逻辑
├── pages/                 # Streamlit 多页面
├── data/                  # SQLite、Chroma（gitignore）
├── docs/                  # 产品文档
└── scripts/verify.py      # 冒烟测试
```

---

## 9. 环境变量（参考）

见 [`.env.example`](.env.example)。常用项：`BASE_URL`、`API_KEY`、`MODEL_NAME`、`EMBEDDING_MODE`（`api` | `local`）。

Streamlit Cloud 使用 **Secrets** 注入同名变量。
