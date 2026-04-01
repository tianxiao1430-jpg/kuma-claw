# GCP 一键部署指南

> 🚀 5 分钟将 Kuma Claw 部署到 Google Cloud Platform 免费额度

## 📋 前置条件

- Google Cloud Platform 账号（[免费试用](https://cloud.google.com/free)）
- GCP 项目（已启用 Cloud Build 和 Cloud Run API）
- 必要的 API 密钥（Google Generative AI、Telegram Bot Token 等）

## 🎯 快速部署（推荐）

### 方式一：点击部署按钮

点击下方的 **Deploy to GCP** 按钮，自动跳转到 Cloud Console 部署页面：

[![Deploy to GCP](https://storage.googleapis.com/cloudrun/button.svg)](https://deploy.cloud.run/?git_repo=https://github.com/tianxiao1430-jpg/kuma-claw.git)

### 方式二：使用 Cloud Shell

```bash
# 1. 打开 Cloud Shell
# 2. 克隆仓库
git clone https://github.com/tianxiao1430-jpg/kuma-claw.git
cd kuma-claw

# 3. 设置项目 ID
export PROJECT_ID=$(gcloud config get-value project)
export REGION=asia-northeast1

# 4. 启用必要的 API
gcloud services enable cloudbuild.googleapis.com run.googleapis.com containerregistry.googleapis.com

# 5. 提交构建
gcloud builds submit --tag gcr.io/$PROJECT_ID/kuma-claw

# 6. 部署到 Cloud Run
gcloud run deploy kuma-claw \
  --image gcr.io/$PROJECT_ID/kuma-claw \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --concurrency 80 \
  --timeout 300s
```

## 🔧 手动部署（使用 cloudbuild.yaml）

```bash
# 1. 设置环境变量
export PROJECT_ID=$(gcloud config get-value project)
export REGION=asia-northeast1

# 2. 启用 API
gcloud services enable cloudbuild.googleapis.com run.googleapis.com containerregistry.googleapis.com

# 3. 提交构建（自动使用 cloudbuild.yaml）
gcloud builds submit --config cloudbuild.yaml \
  --substitutions _REGION=$REGION,_MEMORY=512Mi,_CPU=1,_CONCURRENCY=80,_TIMEOUT=300s
```

## ⚙️ 配置环境变量

部署完成后，在 Cloud Console 中配置必要的环境变量：

### 必要变量

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `GOOGLE_GENAI_USE_VERTEXAI` | 使用 Vertex AI | `true` |
| `GOOGLE_CLOUD_PROJECT` | GCP 项目 ID | `your-project-id` |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token | `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11` |
| `OPENCLAW_WORKSPACE` | OpenClaw 工作目录 | `/home/kuma/.openclaw/workspace` |

### 可选变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `LOG_LEVEL` | 日志级别 | `INFO` |
| `MEMORY_ENABLED` | 启用记忆系统 | `true` |
| `SKILLS_ENABLED` | 启用技能系统 | `true` |

### 配置步骤

1. 打开 [Cloud Console](https://console.cloud.google.com/)
2. 导航到 **Cloud Run** → 选择 `kuma-claw` 服务
3. 点击 **编辑 & 部署新版本**
4. 在 **环境变量** 部分添加上述变量
5. 点击 **部署**

## 💰 成本估算

Cloud Run 免费额度（每月）：

- **请求数**: 200 万次
- **CPU 时间**: 180,000 vCPU-秒
- **内存**: 360,000 GiB-秒
- **网络**: 1GB 出站流量

**典型使用场景**（个人/小团队）：
- 每日 1000 次请求
- 平均响应时间 500ms
- 内存使用 256MB
- **月成本**: ¥0（在免费额度内）

## 🔍 验证部署

```bash
# 获取服务 URL
export SERVICE_URL=$(gcloud run services describe kuma-claw \
  --platform managed \
  --region $REGION \
  --format 'value(status.url)')

# 健康检查
curl $SERVICE_URL/health

# 预期输出：{"status": "healthy"}
```

## 🐛 故障排查

### 构建失败

```bash
# 查看构建日志
gcloud builds list --limit=5
gcloud builds log <BUILD_ID>
```

### 部署失败

```bash
# 查看 Cloud Run 日志
gcloud run services describe kuma-claw \
  --platform managed \
  --region $REGION

# 查看日志
gcloud run logs read kuma-claw --platform managed --region $REGION
```

### 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| `PERMISSION_DENIED` | 缺少 API 权限 | 启用 Cloud Build / Cloud Run API |
| `IMAGE_NOT_FOUND` | 镜像构建失败 | 检查 Dockerfile 和构建日志 |
| `HEALTH_CHECK_FAILED` | 健康检查失败 | 确保应用监听 8080 端口 |
| `MEMORY_LIMIT_EXCEEDED` | 内存不足 | 增加内存配置（--memory） |

## 📚 相关文档

- [Cloud Run 定价](https://cloud.google.com/run/pricing)
- [Cloud Build 文档](https://cloud.google.com/build/docs)
- [环境变量最佳实践](https://cloud.google.com/run/docs/configuring/environment-variables)

---

**最后更新**: 2026-04-01
**版本**: v0.1.1
