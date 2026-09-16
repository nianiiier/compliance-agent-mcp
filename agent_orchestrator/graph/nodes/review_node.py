import json
import re
from pathlib import Path
from agent_orchestrator.llm_config import ollama_invoke_async

PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "review_prompt.txt"
with open(PROMPT_PATH, "r", encoding="utf-8") as f:
    REVIEW_SYS_PROMPT = f.read()

_RISK_MAP = {
    "高": "高", "高风险": "高", "high": "高", "High": "高",
    "中": "中", "中风险": "中", "medium": "中", "Medium": "中",
    "低": "低", "低风险": "低", "low": "低", "Low": "低",
    "无": "无风险", "无风险": "无风险", "none": "无风险",
}

def _extract_json(text: str) -> str:
    """从LLM输出里抠出第一个合法JSON对象；失败则原样返回"""
    text = text.strip()
    # 去 markdown 代码块包裹
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    # 抠第一个 {...}
    m = re.search(r"\{.*\}", text, re.DOTALL)
    return m.group(0) if m else text


async def review_node(state):
    clauses_text = "\n====\n".join(
        [c.get("content", "") for c in state.compliance_clauses]
    ) or "（检索无结果）"

    user_msg = f"""待审查业务文本：{state.user_input}
        检索得到法规条款列表：{clauses_text}"""

    raw_text = await ollama_invoke_async(
        system_prompt=REVIEW_SYS_PROMPT, user_prompt=user_msg
    )

    try:
        data = json.loads(_extract_json(raw_text))
        # 归一化 risk_level，防止 LLM 输出 "High"/"高风险"/"高"
        raw_risk = str(data.get("risk_level", "")).strip()
        risk_level = _RISK_MAP.get(raw_risk, raw_risk or "未知风险")

        confidence = float(data.get("confidence", 0.0))
        confidence = max(0.0, min(1.0, confidence))   # 夹到 [0,1]

        vps = data.get("violation_points", [])
        if not isinstance(vps, list):
            vps = [str(vps)]

        return {
            "risk_level": risk_level,
            "confidence": confidence,
            "violation_points": vps,
        }
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        return {
            "risk_level": "未知风险",
            "confidence": 0.0,
            "violation_points": [f"风险分析解析失败: {str(e)[:100]}"],
        }