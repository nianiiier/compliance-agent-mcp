from pathlib import Path
from agent_orchestrator.llm_config import ollama_invoke_async

PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "report_prompt.txt"
with open(PROMPT_PATH, "r", encoding="utf-8") as f:
    REPORT_SYS_PROMPT = f.read()


async def report_node(state):
    clauses_text = "\n====\n".join([c["content"] for c in state.compliance_clauses])
    vp_text = "\n‑ ".join(state.violation_points) if state.violation_points else "未识别明显违规点"

    user_msg = f"""待审查原文：{state.user_input}
风险等级：{state.risk_level}
置信度：{state.confidence}
识别违规要点：{vp_text}
参考法规片段：{clauses_text}
人工复核审批结果：{state.human_approval}
"""
    markdown_text = await ollama_invoke_async(system_prompt=REPORT_SYS_PROMPT, user_prompt=user_msg)
    return {"report_markdown": markdown_text}
