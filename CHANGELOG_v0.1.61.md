# Sub2API v0.1.61 工作日志

**日期**: 2026-01-24
**版本**: v0.1.61
**GitHub**: https://github.com/lairulan/sub2api/releases/tag/v0.1.61

---

## 一、问题背景

用户反馈下游使用时出现以下错误：
```
API Error: 400 InvokeModelWithResponseStream: operation error Bedrock Runtime:
ValidationException: ***.***.***.***signature: Field required
```

**问题原因**: 下游客户端使用 thinking 模式（如 claude-opus-4-5-thinking），但请求中的 thinking block 缺少必需的 signature 字段，导致 AWS Bedrock 拒绝请求。

---

## 二、代码修改

### 1. 增强错误检测 (antigravity_gateway_service.go)

**位置**: `backend/internal/service/antigravity_gateway_service.go`

修改 `isSignatureRelatedError` 函数，增加以下检测：
- AWS Bedrock 的 `ValidationException` + `Field required` 组合
- `thinking`/`thought` 相关的验证错误

### 2. 增加账号切换次数 (gateway_handler.go)

**位置**: `backend/internal/handler/gateway_handler.go`

| 模型类型 | 修改前 | 修改后 |
|----------|--------|--------|
| Claude | 10 次 | 15 次 |
| Gemini | 3 次 | 5 次 |

### 3. 扩大自动重试错误范围 (antigravity_gateway_service.go)

**位置**: `shouldFailoverUpstreamError` 函数

新增自动切换账号的错误码：
- 408 (Request Timeout)
- 502 (Bad Gateway)
- 503 (Service Unavailable)
- 504 (Gateway Timeout)

### 4. 优化错误消息

将技术性错误消息改为用户友好的提示：

| 错误码 | 修改前 | 修改后 |
|--------|--------|--------|
| 400 | Invalid request | Request format error, please check and retry |
| 401 | Upstream authentication failed | Service authentication failed, please retry later |
| 429 | Upstream rate limit exceeded | Service is busy, please retry later |
| 其他 | Upstream request failed | Service temporarily unavailable, please retry later |

---

## 三、文件变更清单

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `backend/internal/service/antigravity_gateway_service.go` | 修改 | 错误检测、重试范围、错误消息 |
| `backend/internal/handler/gateway_handler.go` | 修改 | 账号切换次数 |
| `backend/cmd/server/VERSION` | 修改 | 版本号更新为 0.1.61 |
| `README.md` | 修改 | 添加联系方式和版本更新说明 |
| `README_CN.md` | 修改 | 添加联系方式和版本更新说明（中文） |

---

## 四、部署步骤

### 编译命令
```bash
# 1. 编译前端
cd frontend && npm run build

# 2. 编译后端（带 embed 标签嵌入前端）
cd backend && GOOS=linux GOARCH=amd64 go build -tags embed -o sub2api_linux_amd64 ./cmd/server
```

### 服务器更新命令
```bash
# 上传文件
scp sub2api_linux_amd64 ubuntu@服务器IP:/tmp/sub2api_new

# 更新服务
sudo systemctl stop sub2api
sudo mv /tmp/sub2api_new /opt/sub2api/sub2api
sudo chmod +x /opt/sub2api/sub2api
sudo systemctl start sub2api
```

---

## 五、Git 提交记录

```
5fc9736 docs: 更新中文 README，添加联系方式和 v0.1.61 版本说明
932858f docs: 添加联系方式和 v0.1.61 版本更新说明
207911f chore: 更新版本号到 v0.1.61
143b54c feat: 优化错误处理，减少用户端错误提示
```

---

## 六、联系方式

微信: **faheng2009**

---

**工作完成时间**: 2026-01-24 10:00
