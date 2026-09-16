import os
# 强制镜像
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

from huggingface_hub import snapshot_download

print("开始下载模型...")
snapshot_download(
    repo_id="sentence-transformers/all-MiniLM-L6-v2",
    local_dir="./models/all-MiniLM-L6-v2",
    endpoint="https://hf-mirror.com",
    # 关键：忽略缓存，强制重新下载
    force_download=True,
)
print("✅ 下载完成")