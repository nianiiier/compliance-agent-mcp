import json
from pathlib import Path
from agent_orchestrator.llm_config import ollama_invoke_async

PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "review_prompt.txt"
with open(PROMPT_PATH, "r", encoding="utf-8") as f:
    REVIEW_SYS_PROMPT = f.read()


async def review_node(state):
    clauses_text = "\n====\n".join([c["content"] for c in state.compliance_clauses])
    user_msg = f"""待审查业务文本：{state.user_input}
检索得到法规条款列表：{clauses_text}"""

    raw_text = await ollama_invoke_async(system_prompt=REVIEW_SYS_PROMPT, user_prompt=user_msg)
    raw_text = raw_text.strip()
    try:
        data = json.loads(raw_text)
        return {
            "risk_level": data.get("risk_level", "未知风险"),
            "confidence": float(data.get("confidence", 0.0)),
            "violation_points": data.get("violation_points", [])
        }
    except json.JSONDecodeError:
        return {
            "risk_level": "未知风险",
            "confidence": 0.0,
            "violation_points": ["风险分析解析失败，LLM返回格式异常"]
        }
