Write-Host "启动合规Agent系统..." -ForegroundColor Green

# 终端1：MCP Server
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\..'; uv run python mcp_server/main.py --transport sse --port 8005"

Start-Sleep -Seconds 3

# 终端2：FastAPI Gateway
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\..'; uv run python -m backend_gateway.main"

Write-Host "`n✅ MCP Server: http://127.0.0.1:8005" -ForegroundColor Cyan
Write-Host "✅ Gateway:    http://127.0.0.1:8000/docs" -ForegroundColor Cyan
Write-Host "`n先等 MCP Server 显示【模型预热完成】再测试接口" -ForegroundColor Yellow