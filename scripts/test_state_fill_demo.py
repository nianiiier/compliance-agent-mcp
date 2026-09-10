import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))
import json
from agent_orchestrator.graph.state import ComplianceAgentState

def main():
    # PowerShell > 重定向输出默认GBK编码
    with open("raw_mcp_out.json","r",encoding="gbk") as f:
        mcp_data = json.load(f)

    clauses = mcp_data.get("clauses",[])
    state = ComplianceAgentState(
        user_input="请审查增值税进项抵扣相关合规风险",
        compliance_clauses=clauses,
        violation_points=[]
    )
    print("✅ State模型实例化成功")
    print(state.model_dump_json(indent=2))

if __name__ == "__main__":
    main()
