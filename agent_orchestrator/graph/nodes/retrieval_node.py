from pathlib import Path
from agent_orchestrator.llm_config import ollama_invoke_async

PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "retrieval_prompt.txt"
with open(PROMPT_PATH, "r", encoding="utf-8") as f:
    RETRIEVAL_SYS_PROMPT = f.read()


async def retrieval_node(state, mcp_client):
    user_input = state.user_input

    # ① 用 LLM 提取关键词（prompt 外置在 retrieval_prompt.txt）
    keyword_text = await ollama_invoke_async(
        system_prompt=RETRIEVAL_SYS_PROMPT,
        user_prompt=user_input,
    )
    keyword_query = keyword_text.strip()

    # ② 双路检索：原始长句（保证覆盖）+ 关键词（保证精度）
    res_origin = await mcp_client.call_tool(
        "retrieve_compliance",
        arguments={"query": user_input, "top_k": 3},
    )
    res_keyword = await mcp_client.call_tool(
        "retrieve_compliance",
        arguments={"query": keyword_query, "top_k": 3},
    )

    # ③ 合并去重（按 content 文本）
    seen = set()
    merged = []
    for res in (res_origin, res_keyword):
        if not res.get("ok"):
            continue
        for c in res.get("clauses", []):
            content = c.get("content", "")
            if content and content not in seen:
                seen.add(content)
                merged.append(c)

    return {"compliance_clauses": merged[:5]}