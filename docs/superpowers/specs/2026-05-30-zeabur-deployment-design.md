# Zeabur 部署方案

## 概述

将简历平台四个服务部署到 Zeabur，解决生产环境中前端无法调用后端 API 的问题。

## 架构

```
Zeabur Project: resume-platform
├── backend                 Python FastAPI     zeabur.app subdomain A
├── resume-optimizer        Vue 3 + Vite       zeabur.app subdomain B
├── resume-generator        Next.js 16         zeabur.app subdomain C
└── landing-page            Vite 静态页面       zeabur.app subdomain D
```

## 服务配置

### 1. backend (FastAPI)

- **构建**: 已有 `zeabur.toml` (python builder, uvicorn 启动)
- **环境变量** (需在 Zeabur Dashboard 设置):
  - `SILICONFLOW_API_KEY` — SiliconFlow API 密钥
  - `SILICONFLOW_MODEL` — 主模型
  - `RESUME_LAYOUT_MODEL` — 排版模型
  - `RESUME_LAYOUT_API_KEY` — 排版模型密钥
  - `SUPABASE_DATABASE_URL` — Supabase PostgreSQL 连接串
  - `APP_ENV=production`
  - `ALLOWED_ORIGINS` — 部署后填写前端三个服务的域名

### 2. resume-optimizer (Vue 3 + Vite)

- **构建**: 已有 `zeabur.toml` (vite builder)
- **环境变量**:
  - `VITE_API_BASE_URL` — 指向部署后的 backend URL

### 3. resume-generator (Next.js)

- **构建**: 已添加 `zeabur.toml` (next builder)
- **环境变量**:
  - `OPENAI_API_KEY`
  - `OPENAI_BASE_URL`
  - `OPENAI_MODEL`
  - `NEXT_PUBLIC_SUPABASE_URL`
  - `NEXT_PUBLIC_SUPABASE_ANON_KEY`

### 4. landing-page (Vite 静态)

- **构建**: 已添加 `zeabur.toml` (vite builder)
- **环境变量**:
  - `VITE_OPTIMIZER_URL` — 部署后填写 optimizer 的 URL
  - `VITE_GENERATOR_URL` — 部署后填写 generator 的 URL

## 已完成的准备工作

1. ✅ `apps/resume-generator/zeabur.toml` — Next.js 构建配置
2. ✅ `apps/landing-page/zeabur.toml` — Vite 静态构建配置
3. ✅ `apps/landing-page/.env` — 本地开发 URL 默认值
4. ✅ 入口页硬编码 localhost 链接已改为变量 `OPTIMIZER_URL` / `GENERATOR_URL`
5. ✅ 后端 CORS 默认降级为 `*`（未设置 ALLOWED_ORIGINS 时）

## 数据库

- **生产环境**: Supabase PostgreSQL (`SUPABASE_DATABASE_URL` 已在 `.env` 中)
- 后端 `connection.py` 检测到 postgres:// 协议自动使用 PostgreSQL 连接池
- Zeabur 文件系统是临时性的，不能用 SQLite

## 部署步骤

1. **Git push**: 把本地修改提交并推送到 GitHub
2. **Zeabur 创建项目**: 登录 zeabur.com → 新建项目 → 关联 GitHub 仓库
3. **添加服务**: 依次添加 4 个服务，分别指向对应目录
4. **设置后端环境变量**: 先部署 backend，拿到 URL
5. **设置前端环境变量**: 将 backend URL 填入 optimizer 的 `VITE_API_BASE_URL`，将各前端 URL 填入 landing-page 和 `ALLOWED_ORIGINS`
6. **验证**: 访问入口页 → 尝试优化助手和生成助手功能

## 注意事项

- 部署顺序: backend 先部署，前端后部署（前端需要知道后端 URL）
- .gitignore 已排除 `.env` 文件，密钥通过 Zeabur Dashboard 设置，安全
- 后端的 ALLOWED_ORIGINS 在 Zeabur 中设置（不提交到 .env）
- 如果首次部署后端出现数据库错误，确认 SUPABASE_DATABASE_URL 是否正确
