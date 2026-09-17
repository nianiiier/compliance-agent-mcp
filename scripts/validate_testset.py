import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.resolve()

# 读测试集
with open(PROJECT_ROOT / "rag_evaluation" / "dataset" / "compliance_testset.json",
          encoding="utf-8") as f:
    data = json.load(f)

# 读法规原文
with open(PROJECT_ROOT / "data" / "upload_docs" / "增值税法实施条例.txt",
          encoding="utf-8") as f:
    law_text = f.read()

samples = data.get("samples", [])
print(f"共 {len(samples)} 条\n")

for i, case in enumerate(samples):
    for clause in case.get("reference_clauses", []):
        # 检查是否在法规原文里出现
        key = clause.strip()[:30]  # 取前30字匹配
        if key not in law_text:
            print(f"❌ 第{i+1}条：引用法条不在原文中")
            print(f"   引用内容: {clause[:60]}...")
            print(f"   question: {case['question'][:40]}...")
            print()
print("检查完成")