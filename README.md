# compliance-agent-mcp

基于 **LangGraph + MCP + RAG** 的合规审查 Agent 系统。

用户提交待审查文本 → 检索法规知识库 → LLM 审查风险 → 高风险触发 HITL 人工复核 → 生成 Markdown 审查报告。

---

## 📌 项目状态

| 模块 | 状态 | 备注 |
|------|------|------|
| MCP Server（工具层） | ✅ 完成 | SSE 常驻，4 个工具全部可用 |
| MCP Client（通信层） | ✅ 完成 | SSE 传输，重试/超时/日志完整 |
| LangGraph 编排（4 节点流水线） | ✅ 完成 | 检索 → 审查 → HITL → 报告 |
| HITL 原生 interrupt / resume | ✅ 完成 | 高风险挂起、通过/驳回分支均已验证 |
| FastAPI Gateway | ✅ 完成 | 上传/提交/查询/resume 四个接口 |
| **RAGAS 量化评估** | ✅ 完成 | 20 条测试集，3B/7B judge 对比 |
| 一键启动脚本 | ✅ 完成 | `scripts/start_all.ps1` |
| 向量库初始化脚本 | ✅ 完成 | `scripts/init_vector_db.py` |
| 前端 | ⬜ 未做 | 用 Swagger 演示 |

**端到端已跑通**：`上传文档 → 提交审查 → 高风险中断 → resume 恢复 → 生成报告`。

---

## 🎯 项目亮点

- **多 Agent 编排**：LangGraph 4 节点流水线，原生 `interrupt()` 实现 HITL 中断恢复
- **协议解耦**：MCP 协议分离工具层与编排层，工具服务独立进程部署
- **混合检索**：BGE-small-zh 向量检索 + BM25，RRF 融合排序
- **量化评估**：20 条税务合规测试集，RAGAS 四指标评估 + 多轮调优
- **工程实践**：Windows SSE 传输 3 类边界问题解决方案

---

## 📊 RAGAS 评估结果

**测试集**：20 条税务合规场景，覆盖高风险（9 条）、中风险（5 条）、无风险（4 条）、边界案例（2 条）。

### 迭代路径

| 轮次 | 改动 | faithfulness | context_precision | context_recall |
|:---:|------|:---:|:---:|:---:|
| v1 | baseline：all-MiniLM-L6-v2 + chunk 800 | 0.23 | 0.39 | 0.65 |
| v2 | chunk 800→300（过调，章节标题污染） | 0.20 | 0.22 | 0.53 |
| v3 | 换 BGE-small-zh + chunk 500 + 过滤短 chunk | 0.58 | 0.46 | 0.78 |
| v4 | 按"第X条"切分 + 双路检索 + report prompt 硬约束（20 条数据） | 0.44 | 0.55 | 0.63 |
| **v5** | **3B judge → 7B judge** | **0.69** | 0.48 | 0.28 |

**最终指标**（7B judge）：`faithfulness 0.69` / `answer_relevancy 0.47` / `context_precision 0.48` / `context_recall 0.28`

### 关键结论

1. **chunk 粒度是 context_precision 的决定因素**：800→按条切分，从 0.39 提升至 0.55
2. **embedding 必须匹配语言**：英文模型 all-MiniLM-L6-v2 → 中文模型 BGE-small-zh，中文语义匹配能力质变
3. **prompt 硬约束降低幻觉**：`report_prompt` 加"禁止编造法条编号"后，faithfulness 显著改善
4. **judge 模型影响评估绝对值**：3B judge 判定粗糙；7B judge 更严格，同一结果 context_recall 从 0.63 掉到 0.28
5. **评估器本身也要评估**：本地小模型做 judge 有固有局限，生产建议用 GPT-4o / Qwen-Max

**调优全过程**见 `rag_evaluation/analysis.ipynb`。

---

## 🏗️ 架构

```
┌─────────────┐
│  前端/客户端 │  ← Swagger / curl / Postman
└──────┬──────┘
       │ HTTP
┌──────▼──────────────┐
│  FastAPI Gateway    │  backend_gateway/
│  /upload /compliance│
│  /hitl              │
└──────┬──────────────┘
       │ 进程内调用
┌──────▼──────────────┐
│  Agent Orchestrator │  agent_orchestrator/
│  LangGraph 4节点    │
│  + MCP SSE Client   │
└──────┬──────────────┘
       │ MCP over SSE
┌──────▼──────────────┐
│  MCP Server         │  mcp_server/（独立进程）
│  4 tools + Chroma   │
└─────────────────────┘
```

**分层解耦原则**：Agent 层**禁止直接 import** `mcp_server` 内业务函数，全部走 MCP 协议。

---

## 📂 目录结构

```
compliance-agent-mcp/
├── mcp_server/                    # MCP 工具服务（独立进程）
│   ├── main.py                    # FastMCP 入口
│   ├── config.py                  # 路径、embedding、集合名配置
│   └── tools/
│       ├── doc_parser_tool.py     # 支持 .txt / .pdf
│       ├── compliance_retriever_tool.py   # 向量 + BM25 RRF
│       └── similarity_checker_tool.py
├── agent_orchestrator/            # LangGraph 编排层
│   ├── server.py
│   ├── llm_config.py              # Ollama HTTP 封装
│   ├── mcp_client/
│   │   └── mcp_tool_client.py
│   ├── prompts/
│   │   ├── retrieval_prompt.txt   # 关键词提取
│   │   ├── review_prompt.txt      # 风险审查
│   │   └── report_prompt.txt      # 报告生成（含编号约束）
│   └── graph/
│       ├── state.py
│       ├── build_graph.py
│       ├── edges.py
│       └── nodes/                 # retrieval / review / hitl / report
├── backend_gateway/               # FastAPI 网关
│   ├── main.py
│   ├── routes/                    # upload / compliance / hitl
│   ├── schemas/
│   └── clients/
│       └── langgraph_client.py
├── rag_evaluation/                # RAGAS 评估
│   ├── dataset/compliance_testset.json    # 20 条测试集
│   ├── run_ragas_eval.py
│   └── analysis.ipynb             # 调优分析
├── scripts/                       # 测试 & 工具脚本
├── data/
│   └── upload_docs/               # 法规文档（.txt/.pdf）
├── models/                        # 本地 embedding 模型（不入 git）
│   └── bge-small-zh-v1.5/
├── vector_db/                     # Chroma 持久化（不入 git）
├── .env
└── requirements.txt
```

---

## 🚀 快速开始

### 1. 环境准备

```bash
pip install uv
uv venv
.venv\Scripts\activate          # Windows
uv pip install -r requirements.txt
```

### 2. 下载 Embedding 模型（重要）

**不要依赖运行时下载**，用 ModelScope 预先拉取：

```bash
uv pip install modelscope
modelscope download --model BAAI/bge-small-zh-v1.5 --local-dir ./models/bge-small-zh-v1.5
```

**验证**：`models/bge-small-zh-v1.5/` 下应有 `model.safetensors`（~100MB）和 `tokenizer.json`。

`config.py` 会自动检测本地路径，找不到才回退 HF 在线。

### 3. 配置 `.env`

```ini
# ===== LLM（Ollama）=====
LLM_BASE_URL=http://127.0.0.1:11434/v1
LLM_MODEL_NAME=qwen2.5:7b          # 不要用 qwen3 系列推理模型

# ===== MCP =====
MCP_TRANSPORT=sse
MCP_HOST=127.0.0.1
MCP_PORT=8005                       # 与 mcp_server 启动参数一致
MCP_RETRY_TIMES=2
MCP_TIMEOUT=120                     # 首次检索会慢，30 秒容易超时

# ===== 向量库 =====
CHROMA_PERSIST_PATH=./vector_db
```

### 4. 启动系统

**方式 A：一键启动（推荐）**

```powershell
# Windows PowerShell
.\scripts\start_all.ps1
```

**方式 B：手动两个终端**

```bash
# 终端 A：MCP Server
uv run python mcp_server/main.py --transport sse --port 8005

# 终端 B：FastAPI Gateway
uv run python -m backend_gateway.main
```

**看到以下输出表示就绪**：
```
[MCP-Server] 模型预热完成
INFO:     Uvicorn running on http://127.0.0.1:8005
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 5. 初始化向量库

```bash
# 一键导入 data/upload_docs/ 下所有文档
uv run python scripts/init_vector_db.py
```

---

## 🎬 演示方式（无前端）

### 方式 1：Swagger UI（首选）

浏览器打开 `http://localhost:8000/docs`，依次点：

| 步骤 | 接口 | 输入 | 期望 |
|------|------|------|------|
| ① | `POST /upload/document` | 上传 `data/upload_docs/增值税法实施条例.txt` | `ok: true` |
| ② | `POST /compliance/submit` | `{"user_input": "企业虚开发票用于增值税进项抵扣"}` | 返回 `thread_id` |
| ③ | `GET /compliance/thread/{thread_id}/status` | 填 thread_id | `is_interrupt: true` |
| ④ | `POST /hitl/resume` | `{"thread_id": "...", "human_approval": true}` | `report_markdown` 非空 |
| ⑤ | 重复 ②，`human_approval: false` | — | `report_markdown: null`（被驳回） |

### 方式 2：命令行端到端

```bash
uv run python scripts/test_langgraph_sse_e2e.py
```

输出包含：中断 payload、检索条款、风险等级、最终报告。

---

## 🧪 测试脚本速查

| 脚本 | 用途 | 依赖 |
|------|------|------|
| `scripts/test_mcp_sse_client.py` | 裸测 MCP Server 4 个工具 | MCP Server |
| `scripts/test_agent_base_demo.py` | 验证 MCP Client 封装 + State 填充 | MCP Server |
| `scripts/test_langgraph_flow.py` | 图逻辑（HITL 通过，**mock MCP**） | 无 |
| `scripts/test_langgraph_reject.py` | 图逻辑（HITL 驳回，**mock MCP**） | 无 |
| `scripts/test_langgraph_sse_e2e.py` | 真实 SSE 端到端 | MCP Server |
| `scripts/test_ollama_speed.py` | 测 LLM 单次调用速度 | Ollama |
| `scripts/diag_embedding.py` | 诊断 embedding 模型中文语义 | 本地模型 |
| `scripts/validate_testset.py` | 校验测试集 reference_clauses | 无 |

---

## ⚠️ 已知限制 & 待办

### 文档格式支持

当前仅支持 `.txt` 和 `.pdf`。要加 `.docx` / `.md` / `.html`：
- 在 `doc_parser_tool.py` 里加对应 `Loader`
- `langchain_community.document_loaders` 提供 `Docx2txtLoader` / `UnstructuredMarkdownLoader`

### 重复上传问题（**待修**）

**症状**：同一文档上传两次，chunk 会重复入库，导致检索返回重复条款。

**根因**：`doc_parser_tool.py` 目前只做**文件内部 chunk 去重**（hash 级），没有跨文件去重。

**修复方案（三选一）**：

**方案 A（最简单）**：每次上传前清空集合
```python
# doc_parser_tool.py 里
vector_store.delete_collection()
vector_store = get_compliance_vector_store()  # 重建
```
**缺点**：多文档场景下会覆盖已有文档。

**方案 B（生产环境）**：按 `source` metadata 去重
```python
# 删除同 source 旧 chunk，再入库新 chunk
existing = vector_store.get(where={"source": str(fp)})
if existing["ids"]:
    vector_store.delete(ids=existing["ids"])
vector_store.add_documents(dedup_docs)
```
**优点**：支持多文档，同文档覆盖更新。

**方案 C**：全局 hash 去重（跳过已存在 chunk）
**缺点**：文档更新后旧版 chunk 残留。

---

## ⚠️ 踩坑记录

### 1. Windows 上 stdio 传输不可用

**症状**：`TimeoutError`，子进程握手失败。

**根因**：`uv run` 双层子进程劫持 stdio 管道；Windows 下 `anyio` 在导入 langchain 后 spawn 子进程触发 `BrokenResourceError`。

**方案**：**全程使用 SSE 网络模式**。

### 2. 系统代理劫持 localhost → 502

**症状**：`httpx.HTTPStatusError: 502 Bad Gateway for url 'http://127.0.0.1:8005/sse'`

**根因**：Windows 系统代理（Clash 等）对 localhost 请求也生效。

**方案**：
- **短期**：关闭系统代理
- **长期**：给 `sse_client` 传 `httpx_client_factory` 定制 `trust_env=False`（**TODO**）

### 3. 事件循环策略被劫持 → SSE 静默挂起

**症状**：`initialize` 发出去了（服务端 202），客户端永远等不到响应。

**根因**：`mcp_tool_client.py` 模块顶层曾调用 `asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())`。**httpx 在 Selector 事件循环下读 SSE 长连接会静默挂起**。

**方案**：**删掉模块顶层的事件循环策略设置**（仅 stdio 模式需要它）。

### 4. `ClientSession` 必须用 `async with` 进入

**症状**：客户端卡死。

**根因**：`ClientSession` 的后台 reader task 只在 `__aenter__` 时启动。直接构造后调 `initialize()`，reader 根本没启动。

**方案**：`MCPToolClient.connect()` 内显式 `await self._session.__aenter__()`。

### 5. MCP Server 工具必须异步化

**症状**：一个耗时工具调用阻塞整个事件循环，所有新请求排队。

**方案**：`@mcp.tool()` 装饰的函数改成 `async def`，内部用 `asyncio.to_thread(...)` 把同步逻辑扔线程池。启动时预热 embedding 模型。

### 6. Embedding 模型在线下载极易失败

**症状**：`WinError 10060` / `Unrecognized processing class` / `1_Pooling/config.json 404`。

**方案**：
- 用 ModelScope 预先下载
- `config.py` 里本地优先，找不到才回退在线
- ModelScope 下载后目录是多层嵌套，需要 `xcopy` 复制到目标位置
- **Windows 下必须 `set HF_HUB_DISABLE_SYMLINKS=1`** 或用 `snapshot_download(force_download=True)`

### 7. 不要用推理模型（Qwen3、DeepSeek-R1）

**症状**：单次 LLM 调用 40+ 秒，`completion_tokens` 上千。

**根因**：推理模型会先生成 ` thinking...` 思维链。

**方案**：`.env` 里用**普通 instruct 模型**，如 `qwen2.5:3b` / `qwen2.5:7b`。

### 8. chunk_size 不是越小越好

**症状**：chunk 300 时章节标题被切成独立 chunk，污染检索。

**方案**：
- 法规文档**按"第X条"切分**（正则 `(?=第[一二三四五六七八九十百千零\d]+条\s)`）
- 过滤长度 < 30 的片段
- 每条法条独立成 chunk

### 9. RAGAS judge 模型影响指标绝对值

**症状**：同一系统，3B judge 判 context_recall=0.63，7B judge 判 0.28。

**根因**：7B 从 ground_truth 提取的断言粒度更细，分母变大。

**方案**：本地评估用 7B，**生产建议用 GPT-4o 类强模型做 judge**。

---

## 🔧 核心实现要点

### HITL 原生中断

```python
approved = interrupt({
    "reason": "检测到高合规风险，需要人工复核审批",
    "risk_level": risk_level,
    "violation_points": state.violation_points,
})
return {"human_approval": approved}
```

**特点**：
- `interrupt()` 不是 sleep，是**整个 graph 线程挂起**
- state 完整持久化到 checkpointer
- 外部通过 `thread_id` + `Command(resume=value)` 恢复
- 恢复值自动 merge 进 state

### 双路检索（retrieval_node.py）

```python
# 原始长句 + LLM 提取的关键词，两路各自检索后合并去重
res1 = await mcp_client.call_tool("retrieve_compliance",
    {"query": user_input, "top_k": 3})
res2 = await mcp_client.call_tool("retrieve_compliance",
    {"query": keywords, "top_k": 3})
```

### Review 节点 JSON 容错

```python
def _extract_json(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    m = re.search(r"\{.*\}", text, re.DOTALL)
    return m.group(0) if m else text
```

外加风险等级归一化（`high` / `高风险` / `高` → 统一 `高`）。

### RRF 混合检索

`compliance_retriever_tool.py`：向量检索 + BM25 → RRF 融合 → top_k 截断。

---

## 🧭 关键开发约束

1. **严禁** Agent 层直接 import `mcp_server` 业务函数
2. **严禁** graph 节点内部创建 MCP 连接，连接在外层注入
3. **严禁**节点内部直接修改 state，只返回待 merge 的 dict
4. **严禁**运行时在线下载 embedding 模型
5. **严禁**使用推理型 LLM（Qwen3 / R1 / QwQ）做业务节点
6. Prompt 全部外置 `agent_orchestrator/prompts/*.txt`

---

## 📅 待办（可选扩展）

- [ ] 修复重复上传问题（按 source 去重）
- [ ] 支持 `.docx` / `.md` 文档格式
- [ ] SSE 客户端加 `trust_env=False` 长期方案
- [ ] 前端 Vue3 最小原型
- [ ] Docker Compose 部署
- [ ] LangFuse 链路追踪
