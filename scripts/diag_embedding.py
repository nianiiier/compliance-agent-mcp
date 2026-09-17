# scripts/diag_embedding.py 完整替换
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from mcp_server.config import settings
print(f"EMBEDDING_MODEL = {settings.EMBEDDING_MODEL}")

import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

import numpy as np
from langchain_huggingface import HuggingFaceEmbeddings

emb = HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL)

# 测中文语义
q = "虚开发票抵扣进项"
docs = [
    "虚开增值税发票属于违法行为，纳税人不得虚开发票用于进项税额抵扣。",  # 应该最高
    "小规模纳税人可以适用以一个季度为一个计税期间。",
    "免抵退税办法，是指出口环节免征增值税，对应的进项税额抵减应纳增值税税额。",
    "纳税人购进贷款服务的利息支出，对应的进项税额暂不得从销项税额中抵扣。",  # 也应该高
]

v = emb.embed_query(q)
print(f"\nquery = '{q}'  向量维度 = {len(v)}")
print("\n相似度排序：")
results = []
for d in docs:
    dv = emb.embed_query(d)
    sim = float(np.dot(v, dv) / (np.linalg.norm(v) * np.linalg.norm(dv)))
    results.append((sim, d))
for sim, d in sorted(results, reverse=True):
    print(f"  {sim:.4f}  {d[:40]}...")