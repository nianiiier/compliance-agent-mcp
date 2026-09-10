import os
from pathlib import Path
from agent_orchestrator.llm_config import ollama_invoke_async

PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "retrieval_prompt.txt"
with open(PROMPT_PATH, "r", encoding="utf-8") as f:
    RETRIEVAL_SYS_PROMPT = f.read()


async def retrieval_node(state, mcp_client):
    user_msg = f"用户待审查文本：{state.user_input}"
    resp_text = await ollama_invoke_async(system_prompt=RETRIEVAL_SYS_PROMPT, user_prompt=user_msg)
    search_query = resp_text.strip()

    res = await mcp_client.call_tool(
        "retrieve_compliance",
        arguments={"query": search_query, "top_k": 3}
    )
    if res.get("ok"):
        return {"compliance_clauses": res.get("clauses", [])}
    return {"compliance_clauses": []}
