# Resume Platform（简历平台）

> AI 驱动的简历优化与岗位匹配平台，面向大学生求职场景。集简历生成、优化、岗位匹配、投递策略和面试准备于一体，帮助学生从零到一完成求职全流程。

## 功能特性

- **简历生成助手** — 从零开始逐步创建简历，智能引导填写各模块，内置多套模板
- **简历优化助手** — 上传已有简历，AI 分析优化、岗位定制改写，支持修改前后对比
- **岗位匹配诊断** — 输入岗位 JD 或粘贴职位描述，自动匹配简历，输出适配度评分、优势/缺口分析和面试问题
- **投递策略** — 针对目标岗位生成投递话术、建议投递渠道和跟进计划
- **面试准备** — 根据岗位要求和简历内容生成高频面试题、项目追问和回答框架
- **PDF 导出** — 支持多模板套用，一键生成 A4 正式简历 PDF
- **职业规划辅助** — 根据专业、技能、兴趣推荐求职方向和学习路线
- **招聘数据分析** — 批量候选人匹配、筛选效率分析和招聘漏斗

## 技术栈

| 层 | 技术 |
|---|---|
| 包管理 | npm 11.16.0 + npm workspaces |
| 编排 | Turborepo 2.9+ |
| 入口页 | Vite 6（静态 HTML, Google Fonts Inter） |
| 优化助手 | Vue 3 + Vite 6 |
| 生成助手 | Next.js 16 + React 19 + Tailwind CSS 4 |
| 后端 | FastAPI + uvicorn + SiliconFlow API |
| 数据库 | SQLite（本地）/ Supabase PostgreSQL（生产） |
| 设计风格 | Dark Navy（`rgb(2, 8, 23)`），蓝紫渐变，Inter 字体 |

## 项目结构

```
resume-platform/
├── apps/
│   ├── landing-page/            # 入口导航页 (port 3456)
│   ├── resume-optimizer/        # 简历优化助手 (port 5173)
│   └── resume-generator/        # 简历生成助手 (port 3000)
├── backend/                     # FastAPI 后端 (port 8000)
│   ├── app/                     # 应用主代码（路由、服务、数据库）
│   ├── config/                  # 模型配置
│   └── tests/                   # 测试用例
├── docs/
│   └── superpowers/
│       ├── specs/               # 设计文档
│       └── plans/               # 实现计划
├── start.ps1                    # Windows 一键启动（PowerShell）
├── start.bat                    # Windows 一键启动（双击）
├── start.sh                     # Unix 一键启动
├── CLAUDE.md                    # 项目开发指南
├── package.json                 # npm workspaces 配置
└── turbo.json                   # Turborepo 配置
```

## 快速开始

### 一键启动（推荐）

```bash
# Windows
.\start.bat
.\start.ps1

# Unix / macOS / WSL
./start.sh
```

启动脚本会自动完成：Python 虚拟环境创建 → 依赖安装 → 后端启动 → npm install → 并行启动三个前端服务。

### 手动启动

```bash
# 安装依赖
npm install

# 启动全部前端（turbo dev）
npm run dev

# 单独启动后端
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

### 仅前端 / 仅后端

```bash
.\start.ps1 -NoBackend    # 仅启动前端
.\start.ps1 -NoFrontend   # 仅启动后端
```

## 各模块端口

| 模块 | 地址 |
|---|---|
| 入口页 | http://localhost:3456 |
| 优化助手 | http://localhost:5173 |
| 生成助手 | http://localhost:3000 |
| 后端 API | http://localhost:8000 |
| API 文档 | http://localhost:8000/docs |

> 优化助手 Vite 配置已代理 `/api` 到 `localhost:8000`，开发时无需处理跨域。

## 后端 API 概览

| 端点 | 功能 |
|---|---|
| `POST /api/ocr` | PDF 简历解析 |
| `POST /api/match` | 岗位匹配评分 |
| `POST /api/batch-match` | 批量匹配 |
| `POST /api/job/extract-requirements` | 岗位要求自动提取 |
| `POST /api/resume/optimize` | 简历优化 |
| `POST /api/resume/structure` | 简历结构化 |
| `POST /api/resume/export-pdf` | PDF 导出 |
| `POST /api/career/plan` | 职业规划推荐 |
| `POST /api/application/strategy` | 投递策略 |
| `POST /api/interview/prepare` | 面试准备 |
| `GET /api/analytics/recruitment` | 招聘数据分析 |
| `GET /api/resume/templates` | 模板列表 |
| `GET /api/health` | 健康检查 |

所有 LLM 调用统一走 [硅基流动（SiliconFlow）](https://siliconflow.cn) API，支持多模型配置和失败自动降级。

## 部署

### 前端

前端各模块支持 Zeabur 部署，参考各子目录下的 `zeabur.toml`。

### 后端

后端环境变量配置参考 `backend/.env.example`，关键变量：

```env
SILICONFLOW_API_KEY=your_api_key
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1
SILICONFLOW_MODEL=deepseek-ai/DeepSeek-V4-Flash
RESUME_DB_PATH=data/resume.db
ALLOWED_ORIGINS=https://your-frontend-domain
```

> 注意：不要将真实 API Key 提交到仓库。

## 产品价值观

- **真实优先** — AI 只优化表达，不虚构经历、学历、项目或技能
- **结果可解释** — 每一次简历修改和匹配评分都说明依据和证据来源
- **面向学生** — 把依赖学长、机构、内推资源的求职经验产品化，降低普通学生的求职门槛

## 路线图

- [ ] Embedding 语义匹配（替代关键词规则）
- [ ] 深度学习排序模型
- [ ] 校园版（面向就业指导中心批量使用）
- [ ] 多语言简历支持

## License

MIT
