# Resume Platform - CLAUDE.md

## 项目概览

三个前端项目 + 一个 Python 后端的 monorepo，面向大学生求职场景：
- **简历优化助手** — 上传已有简历，AI 分析、优化排版、岗位匹配
- **简历生成助手** — 从零开始逐步创建简历
- **入口页** — 两个助手的导航入口，v0.dev Bluetooth 模板风格

## 架构

```
resume-platform/
├── apps/
│   ├── landing-page/            # Vite 静态入口页, 包名: landing-page (port 3456)
│   ├── resume-optimizer/        # Vue 3 + Vite, 包名: resume-optimizer-frontend (port 5173)
│   └── resume-generator/        # Next.js 16, 包名: offerlab (port 3000)
├── backend/                     # FastAPI + uvicorn (port 8000)
│   ├── .venv/                   # Python 虚拟环境
│   └── .env                     # API 密钥配置（SiliconFlow 等）
├── docs/
│   └── superpowers/
│       ├── specs/               # 设计文档
│       └── plans/               # 实现计划
├── start.ps1                    # 一键启动脚本 (Windows)
├── start.bat                    # 双击启动 (Windows)
├── start.sh                     # 一键启动脚本 (Unix)
├── _run_backend.ps1             # 后端独立窗口启动辅助脚本
├── CLAUDE.md
├── package.json                 # 根 package.json (npm workspaces, packageManager: npm@11.16.0)
└── turbo.json                   # Turborepo 配置
```

## 技术栈

| 层 | 技术 |
|---|---|
| 包管理 | npm 11.16.0 + npm workspaces |
| 编排 | Turborepo 2.9.16 |
| 入口页 | Vite 6.4 (静态 HTML + Google Fonts Inter) |
| 优化助手 | Vue 3 + Vite 6 |
| 生成助手 | Next.js 16.2.6 + React 19 + Tailwind CSS 4 |
| 后端 | FastAPI + uvicorn + SiliconFlow API |
| 数据库 | SQLite (本地) / Supabase PostgreSQL (生产) |
| 设计风格 | dark navy (`rgb(2, 8, 23)`), Inter font, 蓝紫渐变 |

> 注意：turbo 输出中使用的包名与目录名不同 —  `resume-generator` 目录对应包名 `offerlab`，`resume-optimizer` 目录对应包名 `resume-optimizer-frontend`。

## 启动方式

```bash
# 一键启动全部（推荐）
.\start.bat          # 双击或命令行
.\start.ps1          # PowerShell

# 仅前端（不启动后端）
.\start.ps1 -NoBackend

# 仅后端
.\start.ps1 -NoFrontend

# 或手动分别启动
npm run dev           # turbo dev 启动全部前端
cd backend & .venv\Scripts\python -m uvicorn app.main:app --reload  # 后端
```

`start.ps1` 会自动：
1. 创建 Python venv + 安装依赖（首次）
2. 在独立窗口中启动 uvicorn（日志可见）
3. 健康检查等待后端就绪
4. npm install（如需）
5. 并行启动三个前端服务

## 关键端口

- 入口页: http://localhost:3456
- 优化助手: http://localhost:5173（/api 代理到 8000）
- 生成助手: http://localhost:3000
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs

## 开发注意事项

### 已知约束

1. **`.env` 安全**：`backend/.env` 含有真实的 SiliconFlow API 密钥，已在 `.gitignore` 中排除。不要手动提交此文件。
2. **PowerShell 5.1 编码问题**：`.ps1` 文件必须用 UTF-8 BOM 编码，否则中文会乱码导致解析失败。`start.ps1` 当前使用拼音避免此问题。
3. **PowerShell 5.1 & 操作符**：在 `Start-Process -ArgumentList` 数组中使用 `&` 会触发解析错误。改用 `-File` 参数或 Base64 编码绕过。
4. **npm workspaces 锁文件**：子包中不能有独立的 `package-lock.json`，否则 Next.js 会警告。只保留根目录的 `package-lock.json`。
5. **packageManager 字段**：root `package.json` 必须有 `"packageManager": "npm@11.16.0"`，否则 Turborepo 2.9+ 会报错。
6. **端口占用**：如果 3000 端口被占用，Next.js 会自动切换到 3001。旧进程可用 `Get-Process -Name node | Stop-Process -Force` 清理。

### 后端

- Python 后端使用 SiliconFlow API
- API 密钥配置在 `backend/.env`（支持多个 key 对应不同模型）
- 主入口: `backend/app/main.py` 的 `create_app()` 工厂函数
- 所有 `/api/*` 路由在 `backend/app/api/resume_routes.py` 中（已注册到 `/api` 前缀）
- 健康检查端点: `GET /api/health`
- 错误处理：统一的 `stage`+`message`+`detail`+`retryable` 错误格式
- LLM 调用有超时和降级机制：优先 AI → 失败后兜底规则
- PostgreSQL 连接池（Supabase）在应用关闭时自动释放

### 前端代理

优化助手的 Vite 配置将 `/api` 代理到 `localhost:8000`：
```ts
proxy: { "/api": "http://localhost:8000" }
```

## 入口页设计参考

入口页视觉风格参考 v0.dev Bluetooth 模板（https://v0.app/templates/bluetooth-VFadjtPosNu）：
- 背景: `rgb(2, 8, 23)`
- 卡片: `rgba(31, 41, 55, 0.5)` + 1px solid `rgb(55, 65, 81)` + 圆角 10px
- 卡片悬停: 背景变亮，边框变亮，箭头右移 3px
- 字体: Inter（Google Fonts 加载）
- 渐变区: `linear-gradient(to right, rgba(59, 130, 246, 0.15), rgba(168, 85, 247, 0.15))`
- 阴影: `0 1px 2px rgba(0, 0, 0, 0.05)`（Tailwind shadow-2xs 等效）
- 响应式: 640px 以下卡片堆叠、标题缩小
- 导航方式: 点击卡片通过 `window.location.href` 直接跳转（同标签页）

## 对话历史摘要

### 用户偏好
- 中文交互，面向中国大学生求职场景
- 追求便捷：一键启动，不用分别启动多个项目
- 期望全面检查：启动后要验证所有功能可用
- Bug 修复优先：在检查过程中直接修复发现的问题

### 关键决策
1. **Monorepo 方案**（vs 微前端）— 三个前端 + 后端放在同一仓库下，Turborepo 编排前端，Python 后端独立管理但随仓库一起维护
2. **Vite 服务入口页**（vs 直接双击 HTML）— 解决 CORS 问题，且能与 turbo 并行启动
3. **后端独立窗口** — 用 `Start-Process` 在新窗口中运行 uvicorn，日志可见且不与前端输出混淆
4. **拼音替代中文** — 由于 PowerShell 5.1 UTF-8 编码兼容性问题，`start.ps1` 输出使用拼音

### 已修复问题
- 删除 `apps/resume-optimizer/package-lock.json`（重复锁文件）
- 修复 `apps/resume-optimizer/package.json` 中 `"latest"` 版本号为具体 semver 范围
- 后端添加 `GET /api/health` 健康检查端点
- `start.ps1` 多次语法兼容性修复（& 操作符、编码、emoji 字符）

## 构建与部署

```bash
npm run build          # turbo build 构建所有前端
```

后端部署参考 `backend/.env` 配置，FastAPI 应用入口为 `backend/app/main.py:app`。
Zeabur 部署参考 `apps/resume-optimizer/zeabur.toml`。
