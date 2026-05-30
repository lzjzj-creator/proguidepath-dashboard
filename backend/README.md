# Recruitment Matching Backend

FastAPI 后端负责简历解析、岗位匹配、结果持久化和招聘建议生成。

## 运行

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

PDF 导出优先使用 Playwright。首次部署如需启用浏览器级 HTML/CSS 导出，可额外执行：

```bash
playwright install chromium
```

如果运行环境没有 Chromium，后端会自动使用 PyMuPDF 兜底生成 A4 PDF。

大模型调用统一走硅基流动平台，只读取以下环境变量：

- `SILICONFLOW_API_KEY`
- `SILICONFLOW_BASE_URL`
- `SILICONFLOW_MODEL`
- `RESUME_LAYOUT_MODEL`
- `RESUME_LAYOUT_API_KEY`
- `RESUME_LAYOUT_BASE_URL`
- `RESUME_DB_PATH`
- `ALLOWED_ORIGINS`

后端不接入其它模型平台，也不读取其它平台的 API Key。

### 部署说明

本地开发时可以使用 `backend/.env`。线上部署时，请不要把真实 key 写入仓库，而是在部署平台环境变量中配置。

建议至少配置：

```env
SILICONFLOW_API_KEY=your_text_model_key
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1
SILICONFLOW_MODEL=deepseek-ai/DeepSeek-V4-Flash

RESUME_LAYOUT_MODEL=Qwen/Qwen3.6-Plus
RESUME_LAYOUT_API_KEY=your_layout_model_key
RESUME_LAYOUT_BASE_URL=https://api.siliconflow.cn/v1

RESUME_DB_PATH=data/resume.db
ALLOWED_ORIGINS=https://your-frontend-domain
```

说明：

- `SILICONFLOW_*`：用于常规文本模型调用，比如岗位要求提取、简历优化等。
- `RESUME_LAYOUT_*`：用于简历优化板块中的版式/板块识别增强。
- 如果布局识别与文本模型走同一服务网关，`RESUME_LAYOUT_BASE_URL` 可以直接复用 `SILICONFLOW_BASE_URL`。
- 如果没有单独配置 `RESUME_LAYOUT_*`，代码会优先读取这组变量；缺失时再回退到通用 `SILICONFLOW_*`。

## API

### `POST /api/ocr`

上传 PDF 简历，返回 `resumeId`、文本预览和结构化模块。

### `POST /api/match`

输入 `resumeId` 和岗位画像，返回企业招聘视角的岗位匹配报告。

```json
{
  "resumeId": 1,
  "jobProfile": {
    "title": "前端开发工程师",
    "responsibilities": "负责招聘产品 Web 工作台开发...",
    "must_haves": ["熟悉 Vue 或 React", "掌握 TypeScript"],
    "nice_to_haves": ["有 AI 产品经验"],
    "experience_years": "1-3 年",
    "keywords": ["Vue", "TypeScript", "数据看板"]
  }
}
```

响应核心字段：

- `match_score` / `result.total_score`：0-100 总分
- `result.skill_score`：技能匹配分，主要来自岗位关键词、硬性要求和简历技能证据
- `result.experience_score`：经验匹配分，来自年限、项目/实习经历等规则信号
- `result.education_score`：教育匹配分，来自学历和院校等简历证据
- `result.candidate_name`：候选人姓名，无法识别时为“未知候选人”
- `recommendation` / `result.recommendation_level`：强烈推荐 / 推荐面试 / 备选 / 不匹配
- `result.strengths`：候选人优势，要求带证据
- `result.gaps`：岗位缺口或风险
- `result.scoring_basis`：每个评分维度的依据，包含 `dimension`、`score`、`basis`、`evidence`
- `result.resume_evidence`：简历证据片段，包含 `keyword` 和 `evidence`
- `result.must_have_hits`：硬性要求命中和证据
- `result.interview_questions`：推荐面试问题，每题包含 `question`、`category`、`difficulty`
- `result.next_step`：给 HR 的下一步建议

当前匹配算法是“关键词 + 规则评分 + AI 解释”的混合方案：

1. 后端先根据岗位关键词、硬性要求、经验年限和教育信号生成稳定规则分。
2. AI 在规则分基础上补充可解释性、优势/缺口、证据和面试问题。
3. 如果 AI 接口失败，接口会返回规则评分兜底结果，并在 `result.ai_explanation_status` 标记失败原因，保证竞赛演示不断流。

### `POST /api/batch-match`

输入多个 `resumeIds` 和同一个岗位画像，返回按匹配分降序排列的结果。

可选字段 `timeoutSeconds` 用于控制批量处理超时时间，默认 90 秒。

### `POST /api/job/extract-requirements`

从岗位描述中自动提取硬性要求、加分项、关键词、职责摘要、经验年限和风险提示，供前端自动填充岗位画像。

```json
{
  "jobDescription": "岗位 JD 原文..."
}
```

返回结构化 JSON：

- `must_haves`：硬性要求，每条包含 `requirement` 和 `evidence`
- `nice_to_haves`：加分项，每条包含 `requirement` 和 `evidence`
- `keywords`：去重关键词
- `experience_years`：年限要求
- `risk_flags`：需要 HR 二次确认的点

### `POST /api/resume/optimize`

岗位定制简历优化接口。根据原始简历和目标岗位要求生成适配岗位的优化版简历。可以传 `resumeId` 复用已解析简历，也可以直接传 `rawResumeText` 和 `sections`。

```json
{
  "resumeId": 1,
  "jobDescription": "目标岗位 JD 原文..."
}
```

或：

```json
{
  "rawResumeText": "原始简历文本...",
  "sections": [],
  "jobRequirements": {
    "title": "后端开发工程师",
    "must_haves": ["Python", "FastAPI"]
  }
}
```

返回内容包含：

- `optimized_resume.sections`：分模块前后对比，含 `before`、`after`、`changes`、`reasons`、`evidence`
- `optimizedResume`：优化后简历，兼容前端直读
- `beforeAfterComparison`：修改前后对比
- `modificationReasons`：修改原因
- `keywords_to_add`：可补充关键词，但必须有原简历证据支撑
- `matched_requirements`：岗位要求匹配情况
- `matchedJobRequirements`：匹配到的岗位要求
- `unmetRequirements`：未满足要求
- `risk_warnings`：不能强行包装或证据不足的风险
- `suggestedExperiencesToAdd`：建议未来真实补充的项目/实习/作品经历
- `non_fabrication_statement`：不虚构声明
- `nonFabricationReminder`：不可虚构提醒
- `structuredResume`：结构化简历数据，可直接用于模板预览和 PDF 导出

安全约束：只能基于原简历已有事实优化表达，禁止虚构经历、学历、公司、项目、年限、技能、证书或成果。

### `POST /api/resume/structure`

把岗位定制简历优化结果或前端传入的简历内容转换为统一结构化数据，方便套用不同模板。

```json
{
  "resumeData": {
    "optimized_resume": {
      "target_title": "前端实习生",
      "summary": "软件工程大三学生...",
      "sections": []
    }
  }
}
```

返回：

- `structuredResume.basics`：姓名、电话、邮箱、地点、摘要、链接
- `structuredResume.education`：教育经历
- `structuredResume.projects`：项目经历
- `structuredResume.experiences`：实习/工作经历
- `structuredResume.skills`：技能分组
- `structuredResume.certificates` / `awards`：证书和获奖
- `structuredResume.selfEvaluation`：自我评价

### `GET /api/resume/templates`

返回可用简历模板列表，每个模板包含：

- `id`：模板 ID
- `name`：模板名称
- `suitableRoles`：适用岗位
- `source`：来源
- `sourceUrl`：来源 URL
- `license`：授权信息

### `POST /api/resume/export-pdf`

根据模板 ID 和结构化简历数据生成正式 A4 PDF。

```json
{
  "templateId": "campus-clean",
  "structuredResume": {
    "basics": {
      "name": "张三",
      "phone": "13800000000",
      "email": "test@example.com",
      "summary": "软件工程大三学生..."
    },
    "targetRole": "前端实习生",
    "education": [],
    "projects": [],
    "experiences": [],
    "skills": []
  },
  "filename": "张三-前端实习生简历.pdf"
}
```

也可以传 `resumeData`，后端会先转换为 `structuredResume` 再导出。响应为 `application/pdf` 文件下载，服务端会处理 A4 页面、中文字体、分页和下载文件名。

### `POST /api/career/plan`

用于大学生职业规划辅助，根据专业、年级、技能、经历、目标城市和兴趣方向推荐求职方向。

```json
{
  "major": "软件工程",
  "grade": "大三",
  "skills": ["Vue", "JavaScript", "Python"],
  "experience": "做过课程项目和一个后台管理系统",
  "targetCity": "杭州",
  "interests": ["前端开发", "AI 产品"]
}
```

返回 `recommendedDirections`，每个方向包含 `direction`、`score`、`reason`、`gaps`、`actionPlan`，并补充学习路线、作品集建议、城市建议和风险提醒。

### `POST /api/application/strategy`

用于投递策略。输入学生背景、岗位描述或结构化岗位要求、可选适配度诊断和简历 ID，返回：

- `shouldApply`：是否建议投递
- `priority`：投递优先级
- `resumeVersionAdvice`：简历版本建议
- `applicationMessage`：投递话术
- `riskWarnings`：风险提醒
- `resumeContentToImprove`：需要补强的简历内容
- `bestChannels`：建议投递渠道
- `followUpPlan`：跟进计划

### `POST /api/interview/prepare`

用于面试准备。输入学生背景、岗位描述或结构化岗位要求、可选简历上下文和适配度诊断，返回：

- `highFrequencyQuestions`：高频问题
- `resumeFollowUpQuestions`：简历追问问题
- `projectQuestions`：项目问题
- `behavioralQuestions`：行为面试问题
- `answerFrameworks`：回答框架
- `scoreDimensions`：评分维度
- `riskPoints`：风险点
- `practicePlan`：练习计划

### `GET /api/analytics/recruitment`

返回招聘数据分析，包含：

- `totalResumes`：总简历数
- `recommendedCount`：推荐人数
- `averageScore`：平均分
- `positionEfficiency`：各岗位筛选效率
- `recruitmentFunnel`：招聘漏斗
- `candidateSources`：候选人来源分布
- `estimatedTimeSavedHours`：预计节省时间

数据分析接口会联网检索公开资料，并为每个数据点返回 `sources`，包含 `title`、`url`、`publisher`、`publishedAt`、`accessedAt` 和 `evidenceSummary`。禁止返回无来源演示数据；如果联网来源不可用，接口会返回错误而不是伪造来源。

### `POST /api/suggestions`

保留原简历优化建议接口，作为补充能力。

## 后续扩展

当前方案优先保证可解释、稳定和演示友好。后续可以把规则召回升级为 embedding 语义匹配，例如对岗位要求和简历片段建立向量索引；也可以引入深度学习排序模型，将历史面试/录用结果作为训练信号，进一步优化岗位匹配分。

## 学生端 MVP 定位

MVP 阶段先服务大学生个人求职，不做完整 ATS，也不做复杂企业招聘系统。最完整的闭环是：

职业方向 → 岗位理解 → 简历优化 → 投递建议 → 面试准备。

第一批用户优先聚焦这些社区：

- 大三、大四准备实习和秋招的学生
- 简历空白、不知道怎么写项目经历的学生
- 转专业/跨方向求职的学生
- 学校就业指导老师
- 校园求职社群、学院就业群、实习内推群

这些人群的痛点足够具体，也更容易通过校园社群、学院就业群、内推群和就业指导中心触达。早期不要泛化成“所有求职者”，先在大学生实习和秋招场景里把价值做深。

## 商业化建议

- 免费：简历解析 + 基础适配度
- 单次付费：岗位定制简历优化，9.9 元或 19.9 元一次
- 套餐：简历优化 + 投递话术 + 面试题，29.9 元
- 校园版：面向就业指导中心或班级批量使用

早期获客可以从身边同学、学院就业群、校园求职社群和就业指导老师开始，一对一收集反馈，先验证 20-100 个真实付费或高频使用用户，再考虑更大的企业校招场景。

## 产品价值观

- 真实优先：AI 只优化表达，不虚构经历。
- 帮助学生理解岗位，而不是制造虚假匹配：系统会告诉学生哪些要求满足，哪些不满足。
- 让普通学生也能获得专业求职辅导：把依赖学长、机构、内推资源的经验产品化给更多学生。
- 结果可解释：每一次简历修改和匹配评分都要说明依据。

## 竞赛演示建议

建议用一个真实学生案例：大三软件工程学生想投递“AI 产品前端实习生”，但简历里只有课程项目和后台管理系统经历。

演示流程：

1. 输入学生背景。
2. 系统推荐适合岗位方向。
3. 粘贴岗位 JD。
4. 自动提取硬性要求、加分项和关键词。
5. 上传原始简历。
6. 输出适配度诊断。
7. 一键生成岗位定制简历。
8. 生成投递话术。
9. 生成面试准备问题。
10. 展示最终价值：节省学生反复改简历、猜岗位要求、盲目投递的时间。
