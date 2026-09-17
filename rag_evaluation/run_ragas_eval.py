import sys
import types

# ========= SHIM 补丁：修复 ragas 0.4.x vertexai 强制导入bug =========
# 伪造缺失的 langchain_community.chat_models.vertexai 模块
mod = types.ModuleType("langchain_community.chat_models.vertexai")
mod.ChatVertexAI = type("ChatVertexAI", (), {})
sys.modules["langchain_community.chat_models.vertexai"] = mod

# 伪造 langchain_community.llms.VertexAI
import langchain_community.llms
if not hasattr(langchain_community.llms, "VertexAI"):
    langchain_community.llms.VertexAI = type("VertexAI", (), {})

import json
import asyncio
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

import os
os.environ["OPENAI_API_KEY"] = "sk-fake"   # ⚠️ 必须，见下方说明

from dotenv import load_dotenv
load_dotenv()

from datasets import Dataset
from langchain_huggingface import HuggingFaceEmbeddings
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)

from ragas.run_config import RunConfig
from openai import AsyncOpenAI
from ragas.llms import llm_factory
from ragas.embeddings import HuggingFaceEmbeddings as RagasHFEmbeddings

from agent_orchestrator.mcp_client.mcp_tool_client import create_mcp_sse_client
from agent_orchestrator.graph.state import ComplianceAgentState
from agent_orchestrator.graph.build_graph import build_agent_graph
from langgraph.types import Command
from sentence_transformers import SentenceTransformer

# ============ RAGAS 本地化配置 ============

def build_ragas_llm():
    """用 Ollama 的 OpenAI 兼容接口作 RAGAS 评判 LLM；不引入 langchain_ollama"""
    client = AsyncOpenAI(
        base_url=os.getenv("LLM_BASE_URL", "http://127.0.0.1:11434/v1"),
        api_key="ollama",                       # Ollama 不校验，随便填
    )
    return llm_factory(
        model="qwen2.5:7b", 
        # model=os.getenv("LLM_MODEL_NAME", "qwen2.5:3b"),
        client=client,
        # 上下文窗口给大一些，RAGAS 评判 prompt 很长
        # 参数名可能随版本不同，报错时看提示
    )

class LocalRagasEmbeddings:
    """
    RAGAS 需要的 embeddings 接口：embed_query / embed_documents
    直接封装 sentence-transformers，避免引入 langchain 生态
    """
    def __init__(self, model_path: str):
        self.model = SentenceTransformer(model_path)

    def embed_query(self, text: str):
        return self.model.encode(text, normalize_embeddings=True).tolist()

    def embed_documents(self, texts):
        return self.model.encode(texts, normalize_embeddings=True).tolist()


def build_ragas_embeddings():
    """直接用 sentence-transformers 本地模型"""
    local_model = PROJECT_ROOT / "models" / "all-MiniLM-L6-v2"
    model_path = str(local_model) if local_model.exists() \
        else "sentence-transformers/all-MiniLM-L6-v2"
    return LocalRagasEmbeddings(model_path)


# ============ 调用 Graph 采集数据 ============

async def run_single_case(graph, mcp_client, question: str, thread_id: str):
    """
    对单条测试用例跑完整 Graph，返回 contexts 和 answer。
    高风险用例走 HITL resume=True（默认审批通过）。
    """
    config = {"configurable": {"thread_id": thread_id}}

    init_state = ComplianceAgentState(
        user_input=question,
        compliance_clauses=[],
        violation_points=[],
    )

    await graph.ainvoke(init_state, config=config)

    snapshot = await graph.aget_state(config=config)
    is_interrupt = bool(snapshot.tasks and snapshot.tasks[0].interrupts)

    if is_interrupt:
        # 高风险自动审批通过，拿最终报告
        final = await graph.ainvoke(
            input=Command(resume=True),
            config=config,
        )
        state_values = final
    else:
        state_values = snapshot.values

    # 采集 RAGAS 需要的字段
    contexts = [
        c.get("content", "")
        for c in state_values.get("compliance_clauses", [])
    ]
    answer = state_values.get("report_markdown", "") or ""

    return contexts, answer


async def collect_eval_data(testset_path: Path):
    """遍历测试集，跑 Graph，采集 (question, contexts, answer)"""
    with open(testset_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    # ✅ 兼容顶层 {"samples": [...]} 和直接 [...] 两种结构
    if isinstance(raw, dict):
        testset = raw.get("samples") or raw.get("data") or raw.get("testset") or list(raw.values())[0]
    else:
        testset = raw

    print(f"加载测试集 {len(testset)} 条")

    questions, answers, contexts_list, ground_truths = [], [], [], []

    async with create_mcp_sse_client(host="127.0.0.1", port=8005) as mcp_client:
        graph = build_agent_graph(mcp_client)

        for i, case in enumerate(testset):
            thread_id = f"ragas-{i:03d}"
            question = case.get("question", "").strip()
            ground_truth = case.get("ground_truth", "").strip()
            if not question or not ground_truth:
                print(f"[{i+1}/{len(testset)}] ⚠️ 跳过：question 或 ground_truth 为空")
                continue
            print(f"[{i+1}/{len(testset)}] {question[:40]}...")

            try:
                contexts, answer = await run_single_case(
                    graph, mcp_client, question, thread_id
                )
            except Exception as e:
                print(f"  ⚠️ 失败: {e}")
                contexts, answer = [], ""

            questions.append(question)
            answers.append(answer)
            contexts_list.append(contexts)
            ground_truths.append(ground_truth)

    return Dataset.from_dict({
        "question": questions,
        "answer": answers,
        "contexts": contexts_list,
        "reference": ground_truths,
    })


# ============ 主流程 ============

async def main():
    testset_path = Path(__file__).parent / "dataset" / "compliance_testset.json"

    print("=== 采集评估数据 ===")
    eval_dataset = await collect_eval_data(testset_path)
    print(f"采集完成，共 {len(eval_dataset)} 条")

    print("\n=== RAGAS 评估 ===")
    ragas_llm = build_ragas_llm()
    ragas_emb = build_ragas_embeddings()

    metrics = [faithfulness, answer_relevancy, context_precision, context_recall]

    # ⚠️ 关键：必须同时传 llm 和 embeddings，否则 RAGAS 会默认调 OpenAI
    result = evaluate(
        dataset=eval_dataset,
        metrics=metrics,
        llm=ragas_llm,
        embeddings=ragas_emb,
        run_config=RunConfig(max_workers=4, timeout=180),
    )

    print("\n=== 评估结果 ===")
    print(result)

    # 输出 CSV
    df = result.to_pandas()
    out_csv = Path(__file__).parent / "ragas_result.csv"
    df.to_csv(out_csv, index=False, encoding="utf-8-sig")
    print(f"\n✅ 明细已保存: {out_csv}")

    # 输出汇总
    summary = df[["faithfulness", "answer_relevancy",
                   "context_precision", "context_recall"]].mean()
    print("\n=== 指标均值 ===")
    print(summary)

    summary.to_csv(Path(__file__).parent / "ragas_summary.csv",
                   encoding="utf-8-sig")


if __name__ == "__main__":
    asyncio.run(main())