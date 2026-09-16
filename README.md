# 更新后的 README

```markdown
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
| RAGAS 评估模块 | ⬜ 未开始 | 下一步 |
| Docker 编排 & 一键脚本 | ⬜ 未开始 | |
| 前端 Vue3 | ⬜ 未开始 | 可选 |

**当前端到端已跑通**：`上传文档 → 提交审查 → 高风险中断 → resume 恢复 → 生成报告`。

---

## 🏗️ 架构

```
┌─────────────┐
│  前端/客户端 │
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
│   ├── main.py                    # FastMCP 入口，--transport {stdio|sse}
│   ├── config.py                  # 路径、embedding、集合名配置
│   └── tools/
│       ├── doc_parser_tool.py
│       ├── compliance_retriever_tool.py   # 向量 + BM25 RRF 混合检索
│       └── similarity_checker_tool.py
├── agent_orchestrator/            # LangGraph 编排层
│   ├── server.py                  # Graph 会话管理，thread_id 维护
│   ├── llm_config.py              # Ollama HTTP 调用封装
│   ├── mcp_client/
│   │   └── mcp_tool_client.py     # SSE/stdio 双传输客户端
│   ├── prompts/                   # 3 个 prompt txt
│   └── graph/
│       ├── state.py               # ComplianceAgentState
│       ├── build_graph.py
│       ├── edges.py
│       └── nodes/                 # retrieval / review / hitl / report
├── backend_gateway/               # FastAPI 网关
│   ├── main.py
│   ├── routes/                    # upload / compliance / hitl
│   ├── schemas/                   # request / response
│   └── clients/
│       └── langgraph_client.py
├── scripts/                       # 测试 & 工具脚本
├── data/
│   ├── upload_docs/               # 待入库的法规文档
│   └── violation_case/            # 违规案例库（可选）
├── models/                        # 本地 embedding 模型（不入git）
│   └── all-MiniLM-L6-v2/
├── vector_db/                     # Chroma 持久化（不入git）
├── .env                           # 本地配置（不入git）
└── requirements.txt
```

---

## 🚀 快速开始

### 1. 环境准备

```bash
# 安装 uv（若未安装）
pip install uv

# 创建虚拟环境
uv venv

# 激活（Windows CMD）
.venv\Scripts\activate

# 安装依赖
uv pip install -r requirements.txt
```

### 2. 下载 Embedding 模型到本地（重要）

**不要依赖运行时在线下载**，国内网络极易中断。用 ModelScope 预先下载：

```bash
uv pip install modelscope

# 下载模型到临时目录
modelscope download --model sentence-transformers/all-MiniLM-L6-v2 --local-dir ./models/tmp

# 将 snapshots/master 下的文件复制到目标位置
xcopy models\tmp\...\snapshots\master models\all-MiniLM-L6-v2\ /E /I /Y
```

**验证**：`models/all-MiniLM-L6-v2/` 下应有 `model.safetensors`（~90MB）和 `tokenizer.json`。

`config.py` 会自动优先读取本地路径，找不到才回退到 HF 在线。

### 3. 配置 `.env`

```ini
# ===== LLM（Ollama）=====
LLM_BASE_URL=http://127.0.0.1:11434/v1
LLM_MODEL_NAME=qwen2.5:3b          # 不要用 qwen3 系列推理模型，慢十倍

# ===== MCP =====
MCP_TRANSPORT=sse
MCP_HOST=127.0.0.1
MCP_PORT=8005                       # 必须与 mcp_server 启动参数一致
MCP_RETRY_TIMES=2
MCP_TIMEOUT=120                     # 检索首次调用会慢，30 秒容易超时

# ===== 向量库 =====
CHROMA_PERSIST_PATH=./vector_db
```

### 4. 启动 MCP Server（**终端 A**）

```bash
uv run python mcp_server/main.py --transport sse --port 8005
```

**看到以下两行表示就绪**：
```
[MCP-Server] 模型预热完成
INFO:     Uvicorn running on http://127.0.0.1:8005
```

⚠️ **此终端不能关**，Gateway 和测试脚本都依赖它。

### 5. 启动 FastAPI Gateway（**终端 B**）

```bash
uv run python -m backend_gateway.main
```

浏览器打开 `http://localhost:8000/docs`。

### 6. 端到端验证

**Swagger 中依次调用**：

| 步骤 | 接口 | 输入 | 期望 |
|------|------|------|------|
| ① | `POST /upload/document` | 上传 `data/upload_docs/增值税法实施条例.txt` | `ok: true` |
| ② | `POST /compliance/submit` | `{"user_input": "企业虚开发票用于增值税进项抵扣"}` | 返回 `thread_id` |
| ③ | `GET /compliance/thread/{thread_id}/status` | 填 thread_id | `is_interrupt: true` |
| ④ | `POST /hitl/resume` | `{"thread_id": "...", "human_approval": true}` | `report_markdown` 非空 |
| ⑤ | 重复 ②，`human_approval: false` | — | `report_markdown: null`（被驳回） |

**一键脚本验证**（不依赖 Gateway）：

```bash
# 终端 B
uv run python scripts/test_langgraph_sse_e2e.py
```

---

## 🧪 测试脚本速查

| 脚本 | 用途 | 依赖 |
|------|------|------|
| `scripts/test_mcp_sse_client.py` | 裸测 MCP Server 4 个工具 | 终端 A |
| `scripts/test_agent_base_demo.py` | 验证 MCP Client 封装 + State 填充 | 终端 A |
| `scripts/test_langgraph_flow.py` | 图逻辑（HITL 通过场景，**用 mock MCP**） | 无 |
| `scripts/test_langgraph_reject.py` | 图逻辑（HITL 驳回场景，**用 mock MCP**） | 无 |
| `scripts/test_langgraph_sse_e2e.py` | 真实 SSE 端到端 | 终端 A |
| `scripts/test_ollama_speed.py` | 测 LLM 单次调用速度 | Ollama |

---

## ⚠️ 踩坑记录（重要，供面试/维护参考）

### 1. Windows 上 stdio 传输不可用

**症状**：`TimeoutError`，子进程握手失败。

**根因**：`uv run` 双层子进程劫持 stdio 管道；且 Windows 下 `anyio` 在导入 langchain 后 spawn 子进程会触发 `BrokenResourceError`。

**方案**：**全程使用 SSE 网络模式**。启动 MCP Server 时用 `--transport sse --port 8005`。

### 2. 系统代理劫持 localhost → 502

**症状**：`httpx.HTTPStatusError: Server error '502 Bad Gateway' for url 'http://127.0.0.1:8005/sse'`。

**根因**：Windows 系统代理对 localhost 请求也生效。

**方案**（三选一）：
- 关闭系统代理
- `.env` 加 `NO_PROXY=127.0.0.1,localhost`
- 定制 `httpx.AsyncClient(trust_env=False)` 传入 `sse_client`（**长期方案，TODO**）

### 3. 事件循环策略被劫持 → SSE 静默挂起

**症状**：`initialize` 发出去了（服务端 202），但客户端永远等不到响应。

**根因**：`mcp_tool_client.py` 模块顶层调用了 `asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())`。**httpx 在 Selector 事件循环下读 SSE 长连接会静默挂起**。

**方案**：**删掉模块顶层的事件循环策略设置**（仅 stdio 模式需要它，SSE 模式必须用默认的 ProactorEventLoop）。

### 4. `ClientSession` 必须用 `async with` 进入

**症状**：同上，客户端卡死。

**根因**：`ClientSession` 的后台 reader task 只在 `__aenter__` 时启动。`self._session = ClientSession(...)` 直接构造后调 `initialize()`，**reader 根本没启动**。

**方案**：`MCPToolClient.connect()` 内显式 `await self._session.__aenter__()`，`close()` 里 `await self._session.__aexit__(None, None, None)`。

### 5. MCP Server 工具必须异步化

**症状**：服务端一个耗时工具调用会阻塞整个事件循环，所有新请求排队。

**方案**：`@mcp.tool()` 装饰的函数改成 `async def`，内部用 `asyncio.to_thread(...)` 把同步逻辑扔线程池。同时启动时预热 embedding 模型。

### 6. Embedding 模型在线下载极易失败

**症状**：`WinError 10060` / `Unrecognized processing class` / `1_Pooling/config.json 404`。

**方案**：
- **不在运行时下载**，用 ModelScope 预先下载到 `models/all-MiniLM-L6-v2/`
- `config.py` 里 `EMBEDDING_MODEL` 逻辑：本地存在用本地，不存在回退在线
- ModelScope 下载后目录是 `models/models/sentence-.../snapshots/master/`，**需要复制**到 `models/all-MiniLM-L6-v2/`

### 7. 不要用推理模型（Qwen3、DeepSeek-R1 等）

**症状**：单次 LLM 调用 40+ 秒，`completion_tokens` 上千。

**根因**：推理模型会先生成 ` thinking...` 思维链，简单任务也强行推理。

**方案**：`.env` 里 `LLM_MODEL_NAME` 用**普通 instruct 模型**，如 `qwen2.5:3b` / `qwen2.5:7b`。

### 8. HITL 驳回语义

**默认实现**（`edges.py`）：
- `human_approval=True` → 生成报告
- `human_approval=False` → 直接 END，不生成报告
- `human_approval=None` → 异常兜底，END

如果业务想"驳回也出一份意见书"，改 `check_after_hitl` 分支 + `report_node` 内部根据 `human_approval` 分流 prompt。

---

## 🔧 核心实现要点（面试高频）

### HITL 原生中断

```python
# hitl_interrupt_node.py
approved = interrupt({
    "reason": "检测到高合规风险，需要人工复核审批",
    "risk_level": risk_level,
    "violation_points": state.violation_points,
})
return {"human_approval": approved}
```

**特点**：
- `interrupt()` 不是 sleep，是**整个 graph 线程挂起**，state 完整持久化到 checkpointer
- 外部通过 `thread_id` + `Command(resume=value)` 恢复
- 恢复值自动 merge 进 state，**不需要手动改 state**

### Review 节点 JSON 容错

LLM 输出常带 markdown 包裹、前后解释文字。**绝不能裸调 `json.loads()`**：

```python
def _extract_json(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    m = re.search(r"\{.*\}", text, re.DOTALL)
    return m.group(0) if m else text
```

**外加风险等级归一化**（LLM 可能输出 `high` / `高风险` / `高`），统一映射到 `高/中/低/无风险`。

### RRF 混合检索

`compliance_retriever_tool.py`：向量检索 + BM25 检索 → RRF 融合 → top_k 截断。

---

## 📅 后续路线

### P1 — RAGAS 评估（1.5–2 天，简历核心）

- 构造 20+ 条合规测试集（`question` / `ground_truth` / `reference_clauses`）
- 遍历测试集调完整 Graph，采集 `contexts` 和 `answer`
- 跑 `context_precision` / `faithfulness` / `answer_recall`
- 输出 CSV 报表 + `analysis.ipynb` 对比调优前后指标

### P2 — 工程收尾（1–1.5 天）

- `scripts/init_vector_db.py` 一键导入初始法规
- `scripts/start_all.sh` / `.ps1` 一键启动
- `docker-compose.yml`（MCP + Gateway + Chroma）
- 重写本文档为最终版
- 简历素材整理

### P3 — 前端最小原型（可选）

- `ChatPanel.vue` + `HitlApprovalCard.vue` + `ReportViewer.vue`
- 只做演示用，时间紧可砍

---

## 🧭 关键开发约束

1. **严禁** Agent 层直接 import `mcp_server` 业务函数，全部走 MCP 协议
2. **严禁** graph 节点内部创建 MCP 连接，连接在外层注入
3. **严禁**节点内部直接修改 state 对象，只返回待 merge 的 dict
4. **严禁**运行时依赖在线下载 embedding 模型，必须本地化
5. **严禁**使用推理型 LLM（Qwen3 / R1 / QwQ）做业务节点
6. Prompt 全部外置 `agent_orchestrator/prompts/*.txt`，不硬编码在 Python
```

---

## 📋 覆盖后要做的事

1. **覆盖 `README.md`**：把上面整段保存为根目录的 `README.md`
2. **确认 `.env` 内容对得上文档**：尤其 `MCP_PORT=8005`、`LLM_MODEL_NAME=qwen2.5:3b`
3. **创建 `.env.example`**（脱敏模板，入 git）：
   ```ini
   LLM_BASE_URL=http://127.0.0.1:11434/v1
   LLM_MODEL_NAME=qwen2.5:3b
   MCP_TRANSPORT=sse
   MCP_HOST=127.0.0.1
   MCP_PORT=8005
   MCP_RETRY_TIMES=2
   MCP_TIMEOUT=120
   CHROMA_PERSIST_PATH=./vector_db
   ```
4. **确认 `.gitignore`** 包含：
   ```
   .env
   .venv/
   models/
   vector_db/
   __pycache__/
   *.pyc
   data/upload_docs/*.pdf
   ```
5. **git 提交**：
   ```bash
   git add README.md .env.example .gitignore
   git commit -m "docs: 更新README，标注项目当前状态与踩坑记录"
   ```

---
