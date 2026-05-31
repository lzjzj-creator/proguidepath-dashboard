<template>
  <main class="app-shell">
    <aside class="sidebar">
      <div class="brand">
        <span>AI</span>
        <div>
          <strong>大学生求职助手</strong>
          <small>Career Copilot</small>
        </div>
      </div>

      <nav class="nav-list" aria-label="功能导航">
        <button
          v-for="item in visiblePages"
          :key="item.key"
          type="button"
          :class="{ active: currentPage === item.key }"
          @click="currentPage = item.key"
        >
          <span>{{ item.icon }}</span>
          {{ item.label }}
        </button>
      </nav>
    </aside>

    <section class="page-area">
      <input
        ref="fileInputRef"
        class="upload-input"
        type="file"
        accept="application/pdf"
        multiple
        @change="onFileChange"
      />
      <header class="topbar">
        <div>
          <p class="eyebrow">AI Job Search Assistant 路 SiliconFlow</p>
          <h1>{{ pageTitle }}</h1>
          <p>{{ pageSubtitle }}</p>
        </div>
        <div class="topbar-actions">
          <label class="role-switch">
            <span>当前视角</span>
            <select v-model="currentUserRole">
              <option value="student">学生端</option>
              <option value="operator">老师/运营端</option>
            </select>
          </label>
        </div>
        <button v-if="currentPage === 'template'" class="primary-btn" type="button" :disabled="templateExporting || !hasTemplateResume" @click="exportPdf">
          {{ templateExporting ? "导出中..." : "后端导出 PDF" }}
        </button>
      </header>

      <section v-if="currentPage === 'dashboard'" class="dashboard-grid">
        <article class="hero-panel">
          <p class="eyebrow">主流程</p>
          <h2>工作台 → 岗位解析 → 简历诊断 → 简历优化 → 简历排版 → 投递建议 → 职业规划 → 面试准备</h2>
          <p>
            这个系统面向大学生求职，不再站在 HR 视角筛人，而是帮助学生判断岗位值不值得投、简历怎么改、如何投递以及如何准备面试。
          </p>
          <div class="hero-actions">
            <button class="primary-btn" type="button" @click="currentPage = 'job'">先解析岗位 JD</button>
            <button class="secondary-btn" type="button" @click="fillDemo">填入示例数据</button>
          </div>
        </article>

        <article class="metric-card metric-card--upload" role="button" tabindex="0" @click="openFilePicker" @keydown.enter.prevent="openFilePicker" @keydown.space.prevent="openFilePicker">
          <span>已上传简历</span>
            <strong>{{ selectedFiles.length ? "已选择 " + selectedFiles.length + " 份简历" : "拖拽 PDF 简历到这里，或点击上传" }}</strong>
          <small>支持 PDF 简历解析，先传可在诊断和优化中直接复用</small>
        </article>
        <article class="metric-card">
          <span>岗位适配分</span>
          <strong>{{ selectedCandidate?.metrics.total || "--" }}</strong>
          <small>学生视角诊断</small>
        </article>
        <article class="metric-card">
          <span>投递建议</span>
          <strong>{{ applyLabel(selectedCandidate?.metrics.total || 0) }}</strong>
          <small>按适配度生成</small>
        </article>

        <article class="panel full-span">
          <div class="panel-heading">
            <div>
              <h2>快捷入口</h2>
              <p class="form-note">点击后会直接打开对应环节；“简历优化”在条件齐全时会自动开始运行。</p>
            </div>
          </div>
          <div class="journey-grid">
            <button class="journey-card" type="button" @click="currentPage = 'job'">
              <span class="journey-icon">JD</span>
              <strong>岗位解析</strong>
              <small>先理解岗位要求、关键词和硬性条件。</small>
            </button>
            <button class="journey-card" type="button" @click="currentPage = 'diagnosis'">
              <span class="journey-icon">✓</span>
              <strong>简历诊断</strong>
              <small>上传简历并完成岗位适配度分析。</small>
            </button>
            <button class="journey-card journey-card--primary" type="button" @click="openOptimizeEntry">
              <span class="journey-icon">✎</span>
              <strong>简历优化</strong>
              <small>{{ optimizeEntryHint }}</small>
            </button>
            <button class="journey-card" type="button" @click="openTemplateEntry">
              <span class="journey-icon">A4</span>
              <strong>简历排版</strong>
              <small>把优化后的内容整理成正式投递版简历。</small>
            </button>
            <button class="journey-card" type="button" @click="currentPage = 'delivery'">
              <span class="journey-icon">↗</span>
              <strong>投递建议</strong>
              <small>判断要不要投、优先投哪里、怎么投。</small>
            </button>
            <button class="journey-card" type="button" @click="currentPage = 'planning'">
              <span class="journey-icon">◎</span>
              <strong>职业规划</strong>
              <small>面向大一大二，补全成长路径和行动计划。</small>
            </button>
            <button class="journey-card" type="button" @click="currentPage = 'interview'">
              <span class="journey-icon">?</span>
              <strong>面试准备</strong>
              <small>围绕岗位和简历生成模拟问题与答题框架。</small>
            </button>
          </div>
        </article>

        <article class="panel full-span">
          <h2>求职闭环</h2>
          <div class="flow-steps">
            <span v-for="step in flowSteps" :key="step">{{ step }}</span>
          </div>
        </article>
      </section>

      <section v-else-if="currentPage === 'planning'" class="content-grid">
        <article class="panel">
          <h2>填写你的背景</h2>
          <div class="action-row planning-actions">
            <button class="secondary-btn" type="button" :disabled="careerAutofillLoading" @click="autofillCareerFormFromResume">
              {{ careerAutofillLoading ? "正在提取简历信息..." : "从已上传简历自动填写" }}
            </button>
            <span class="form-note planning-hint">{{ careerAutofillHint }}</span>
          </div>
          <label class="field">
            <span>专业</span>
            <input v-model="careerForm.major" placeholder="例如：软件工程" />
          </label>
          <label class="field">
            <span>年级</span>
            <select v-model="careerForm.grade">
              <option>大一</option>
              <option>大二</option>
              <option>大三</option>
              <option>大四</option>
              <option>研一</option>
              <option>研二</option>
              <option>研三</option>
            </select>
          </label>
          <label class="field">
            <span>技能 / 项目 / 实习</span>
            <textarea v-model="careerForm.skills" rows="5" placeholder="例如：Vue、Python、课程项目、校园社团官网、数据可视化" />
          </label>
          <label class="field">
            <span>目标方向</span>
            <input v-model="careerForm.direction" placeholder="例如：前端开发实习" />
          </label>
          <label class="field">
            <span>目标城市</span>
            <input v-model="careerForm.targetCity" placeholder="例如：北京 / 上海 / 杭州" />
          </label>
          <label class="field">
            <span>兴趣关键词</span>
            <input v-model="careerForm.interests" placeholder="例如：Web 开发、数据产品、AI 应用" />
          </label>
          <button class="primary-btn" type="button" :disabled="careerPlanLoading" @click="generateCareerPlan">
            {{ careerPlanLoading ? "生成中..." : "生成职业行动计划" }}
          </button>
          <p v-if="careerAutofillMessage" class="form-note">{{ careerAutofillMessage }}</p>
          <p class="form-note">{{ careerPlanLoading ? "正在生成职业方向、行动计划和作品集建议..." : careerPlanMessage || "填写背景后即可生成职业行动计划。" }}</p>
          <p v-if="careerPlanIssue" class="alert">失败阶段：{{ careerPlanIssue.stage }}。{{ careerPlanIssue.message }}</p>
          <p v-if="careerPlanIssue?.retryable" class="form-note">可恢复操作：重新点击“生成职业行动计划”即可重试。</p>
        </article>

        <article class="panel">
          <h2>推荐岗位方向</h2>
          <div v-if="careerPlan.roles.length" class="direction-list">
            <div v-for="role in careerPlan.roles" :key="role.title">
              <span>{{ role.title }}</span>
              <p>{{ role.reason }}</p>
              <strong>{{ role.fit }}%</strong>
            </div>
          </div>
          <div v-else class="empty-state">填写背景后生成推荐方向。</div>
          <p v-if="careerPlan.cityAdvice" class="form-note">{{ careerPlan.cityAdvice }}</p>
        </article>

        <article class="panel">
          <h2>行动计划</h2>
          <ol v-if="careerPlan.actions.length" class="action-list">
            <li v-for="action in careerPlan.actions" :key="action">{{ action }}</li>
          </ol>
          <div v-else class="empty-state">这里会告诉你补什么技能、做什么项目、投什么岗位。</div>
        </article>

        <article v-if="careerPlan.portfolioSuggestions.length || careerPlan.riskWarnings.length" class="panel full-span">
          <h2>作品集与风险提醒</h2>
          <div class="content-grid inner-grid">
            <div>
              <p class="panel-subtitle">建议补充的作品或证明材料</p>
              <ul class="action-list">
                <li v-for="item in careerPlan.portfolioSuggestions" :key="item">{{ item }}</li>
              </ul>
            </div>
            <div>
              <p class="panel-subtitle">风险提醒</p>
              <ul class="action-list">
                <li v-for="item in careerPlan.riskWarnings" :key="item">{{ item }}</li>
              </ul>
            </div>
          </div>
        </article>
      </section>

      <section v-else-if="currentPage === 'job'" class="content-grid">
        <article class="panel wide-panel">
          <h2>目标岗位 JD</h2>
          <label class="field">
            <span>岗位名称</span>
            <input v-model="jobForm.title" placeholder="例如：前端实习生" />
          </label>
          <label class="field">
            <span>岗位描述</span>
            <textarea v-model="jobForm.responsibilities" rows="9" placeholder="粘贴岗位职责、任职要求、加分项和招聘对象。" />
          </label>
          <button class="primary-btn" type="button" :disabled="extractingJob || !jobForm.responsibilities.trim()" @click="extractJob">
            {{ extractingJob ? "解析中..." : "解析 JD 并填充要求" }}
          </button>
          <p v-if="extractionMessage" class="form-note">{{ extractionMessage }}</p>
        </article>

        <article class="panel">
          <h2>硬性要求</h2>
          <textarea v-model="mustHaveText" rows="8" />
        </article>
        <article class="panel">
          <h2>加分项与关键词</h2>
          <label class="field">
            <span>加分项</span>
            <textarea v-model="niceHaveText" rows="5" />
          </label>
          <label class="field">
            <span>关键词</span>
            <input v-model="keywordText" placeholder="Vue, TypeScript, 组件化" />
          </label>
        </article>
      </section>

      <section v-else-if="currentPage === 'diagnosis'" class="content-grid">
        <article class="panel">
          <h2>上传简历</h2>
          <div
            :class="['upload-zone', { dragging: isDragging, success: selectedFiles.length }]"
            @dragenter.prevent="isDragging = true"
            @dragover.prevent="isDragging = true"
            @dragleave.prevent="isDragging = false"
            @drop.prevent="onDrop"
          >
            <strong>{{ selectedFiles.length ? "已选择 " + selectedFiles.length + " 份简历" : "拖拽 PDF 简历到这里，或点击上传" }}</strong>
            <span>建议上传与你要投岗位最相关的简历版本。</span>
            <button class="secondary-btn upload-trigger" type="button" @click="openFilePicker">
              选择 PDF 文件
            </button>
          </div>
          <div v-if="selectedFiles.length" class="file-list">
            <div v-for="file in selectedFiles" :key="file.name + file.size">
              <span>{{ file.name }}</span>
              <b>{{ formatSize(file.size) }}</b>
            </div>
          </div>
          <p v-for="item in fileFeedback" :key="item" class="alert">{{ item }}</p>
          <button class="primary-btn" type="button" :disabled="!canRunDiagnosis" @click="processQueue">
            {{ diagnosisButtonLabel }}
          </button>
          <p class="form-note">{{ diagnosisSummary }}</p>
          <p v-if="diagnosisIssue" class="alert">本次诊断未完成，请查看下方“学生视角诊断”中的具体原因。</p>
          <p v-if="diagnosisIssue?.retryable" class="form-note">可恢复操作：重新诊断，或重新上传简历后再试。</p>
          <div v-if="selectedCandidate" class="action-row">
            <button class="secondary-btn" type="button" :disabled="processing" @click="processQueue">
              重新诊断
            </button>
            <button class="secondary-btn" type="button" :disabled="processing" @click="resetDiagnosis">
              重新上传简历            </button>
          </div>
        </article>

        <article class="panel">
          <h2>我的简历版本</h2>
          <div v-if="rankedCandidates.length" class="resume-list">
            <button
              v-for="candidate in rankedCandidates"
              :key="candidate.localId"
              type="button"
              :class="{ active: candidate.localId === selectedLocalId }"
              @click="selectedLocalId = candidate.localId"
            >
              <span>
                {{ candidate.displayName }}
                <small class="candidate-stage">{{ candidate.phaseLabel }}</small>
              </span>
              <strong>{{ candidate.metrics.total || "--" }}</strong>
            </button>
          </div>
          <div v-else class="empty-state">上传并诊断后，这里会展示简历适配度。</div>
        </article>

        <article class="panel">
          <h2>学生视角诊断</h2>
          <template v-if="selectedCandidate && selectedCandidate.phase === 'done'">
            <div class="decision-summary">
              <div>
                <span>我适不适合</span>
                <strong>{{ selectedCandidate.metrics.total }}</strong>
              </div>
              <div>
                <span>要不要投</span>
                <strong>{{ applyLabel(selectedCandidate.metrics.total) }}</strong>
              </div>
            </div>
            <div class="bar-chart">
              <div v-for="bar in scoreBars" :key="bar.label">
                <span>{{ bar.label }}</span>
                <b><i :style="{ width: `${bar.value}%` }"></i></b>
                <em>{{ bar.value }}</em>
              </div>
            </div>
            <dl class="explain-list">
              <dt>哪里匹配</dt>
              <dd>{{ joinList(selectedCandidate.skillMatches) }}</dd>
              <dt>哪里不够</dt>
              <dd>{{ joinList(selectedCandidate.gaps) }}</dd>
              <dt>怎么改</dt>
              <dd>{{ selectedCandidate.summary }}</dd>
            </dl>
          </template>
          <template v-else-if="selectedCandidate">
            <div class="status-card">
              <div class="status-head">
                <strong>{{ selectedCandidate.phaseLabel }}</strong>
                <span>{{ selectedCandidate.progress }}%</span>
              </div>
              <div class="timeline">
                <div
                  v-for="item in diagnosisTimeline"
                  :key="item.key"
                  :class="['timeline-step', { done: item.done, active: item.active }]"
                >
                  <i></i>
                  <span>{{ item.label }}</span>
                </div>
              </div>
              <p class="form-note">{{ diagnosisSummary }}</p>
              <p v-if="selectedCandidate.phase === 'error'" class="alert">
                失败阶段：{{ selectedCandidate.errorStage || "诊断流程" }}。{{ selectedCandidate.error }}
              </p>
              <p v-if="selectedCandidate.phase === 'error' && selectedCandidate.errorAction" class="form-note">
                恢复建议：{{ selectedCandidate.errorAction }}
              </p>
            </div>
          </template>
          <div v-else class="empty-state">点击“AI 诊断适配度”后查看结果。</div>
        </article>
      </section>

      <section v-else-if="currentPage === 'optimize'" class="content-grid">
        <article class="panel">
          <h2>岗位定制简历</h2>
          <p class="muted">基于你已有经历优化表达，不虚构经历、学校、公司、项目、年限或技能。</p>
          <label class="field">
            <span>硅基流动平台模型</span>
            <select v-model="selectedModel">
              <option v-for="model in siliconFlowModels" :key="model">{{ model }}</option>
            </select>
          </label>
          <button class="primary-btn" type="button" :disabled="optimizing" @click="openOptimizeEntry">
            {{ optimizing ? "正在优化..." : "生成岗位定制简历" }}
          </button>
          <button class="primary-btn" type="button" :disabled="!canGenerateTemplateResume" @click="generateTemplateResume">
            {{ templateStructureLoading ? "正在生成排版简历..." : "一键生成排版简历" }}
          </button>
          <p class="form-note">{{ optimizeHint }}</p>
          <div v-if="optimizing || optimizeStage !== 'idle'" class="timeline compact-timeline">
            <div
              v-for="item in optimizeTimeline"
              :key="item.key"
              :class="['timeline-step', { done: item.done, active: item.active }]"
            >
              <i></i>
              <span>{{ item.label }}</span>
            </div>
          </div>
          <p class="form-note">{{ optimizeHintText }}</p>
          <p class="form-note">{{ templateMessage }}</p>
          <p v-if="optimizeIssue" class="alert">失败阶段：{{ optimizeIssue.stage }}。{{ optimizeIssue.message }}</p>
          <p v-if="optimizeIssue?.retryable" class="form-note">可恢复操作：检查前置条件后重新点击生成。</p>
        </article>

        <article class="panel wide-panel">
          <h2>完整成稿预览</h2>
          <p v-if="optimizationResult?.recognitionMode" class="form-note">
            识别方式：{{ optimizationResult.recognitionMode }}
            <span v-if="optimizationResult.layoutConfidence"> / 置信度：{{ Math.round(optimizationResult.layoutConfidence * 100) }}%</span>
          </p>
          <p v-if="optimizationResult?.layoutWarnings?.length" class="form-note">
            识别提示：{{ joinList(optimizationResult.layoutWarnings) }}
          </p>
          <div v-if="optimizationRecognizedBlocks.length" class="recognition-grid">
            <article v-for="block in optimizationRecognizedBlocks" :key="block.key" class="recognition-card">
              <header>
                <strong>{{ block.name }}</strong>
                <span>{{ block.items?.length || 0 }} 条</span>
              </header>
              <ul v-if="block.items?.length" class="recognition-items">
                <li v-for="item in block.items.slice(0, 3)" :key="`${block.key}-${item.title}-${item.content}`">
                  <b>{{ item.title }}</b>
                  <span>{{ item.content }}</span>
                </li>
              </ul>
              <p v-else class="multiline-content">{{ block.content }}</p>
            </article>
          </div>
          <div v-if="optimizationFinalDraftSections.length" class="draft-preview">
            <section v-for="section in optimizationFinalDraftSections" :key="section.title" class="draft-section">
              <h3>{{ section.title }}</h3>
                <p class="multiline-content">{{ section.content }}</p>
            </section>
          </div>
          <div v-else-if="optimizationFinalDraftText" class="script-box draft-preview-text">{{ optimizationFinalDraftText }}</div>
          <div v-else class="empty-state">生成后这里会显示整理好的完整简历成稿预览。</div>
        </article>

        <article class="panel wide-panel">
          <h2>修改前后对比</h2>
          <p v-if="optimizationResult?.isFallback" class="alert">
            本次没有拿到完整的 AI 润色结果，下面展示的是保守兜底建议。{{ optimizationResult.fallbackReason || "建议稍后重试，或缩短 JD 后重新生成。" }}
          </p>
          <p v-if="optimizationResult?.isFallback && optimizationResult.riskWarnings.length" class="form-note">
            风险提示：{{ joinList(optimizationResult.riskWarnings) }}
          </p>
          <p v-if="optimizationResult && !optimizationResult.hasRenderableModules" class="alert">
            AI 暂时无法生成可直接排版的完整简历内容，当前结果可能缺少关键模块。建议检查原简历内容是否完整，或精简 JD 后重试。
          </p>
          <div v-if="optimizationResult" class="optimize-overview">
            <div class="optimize-metric">
              <span>识别模块</span>
              <strong>{{ optimizationCoverage.totalModules }}</strong>
            </div>
            <div class="optimize-metric">
              <span>已优化</span>
              <strong>{{ optimizationCoverage.optimizedModules }}</strong>
            </div>
            <div class="optimize-metric">
              <span>已跳过</span>
              <strong>{{ optimizationCoverage.skippedModules }}</strong>
            </div>
            <div class="optimize-metric">
              <span>可排版</span>
              <strong>{{ optimizationResult.templateReady ? "是" : "待补" }}</strong>
            </div>
          </div>
          <div v-if="optimizationSkippedModules.length" class="skipped-module-list">
            <article v-for="item in optimizationSkippedModules" :key="`${item.moduleName}-${item.reason}`" class="skipped-module-card">
              <strong>{{ item.moduleName }}</strong>
              <p>{{ item.reason || "当前未返回跳过原因" }}</p>
              <small v-if="item.originalContent">原文片段：{{ item.originalContent }}</small>
            </article>
          </div>
          <div v-if="optimizationResult" class="compare-list">
            <section v-for="module in optimizationDisplayModules" :key="module.moduleName" class="compare-card">
              <header>
                <div class="compare-card-title">
                  <h3>{{ module.moduleName }}</h3>
                  <span class="status-pill" :class="module.status === 'optimized' ? 'status-pill--success' : 'status-pill--muted'">
                    {{ module.status === "optimized" ? "已优化" : "保留原文" }}
                  </span>
                </div>
                <span>{{ module.skippedReason ? `跳过原因：${module.skippedReason}` : `关键词补强：${module.addedKeywords.join("、") || "无"}` }}</span>
              </header>
              <div v-if="module.addedKeywords.length || module.matchedRequirements.length" class="chip-row">
                <span v-for="keyword in module.addedKeywords" :key="`${module.moduleName}-keyword-${keyword}`" class="info-chip">
                  关键词：{{ keyword }}
                </span>
                <span v-for="requirement in module.matchedRequirements" :key="`${module.moduleName}-match-${requirement}`" class="info-chip info-chip--light">
                  命中：{{ requirement }}
                </span>
              </div>
              <div class="compare-columns">
                <div>
                  <h4>修改前</h4>
                  <p class="multiline-content">{{ module.originalContent || "暂无内容" }}</p>
                </div>
                <div>
                  <h4>修改后</h4>
                  <p class="multiline-content">{{ module.optimizedContent || "暂无内容" }}</p>
                </div>
              </div>
              <dl class="explain-list">
                <dt>修改原因</dt>
                <dd>{{ module.changeReason || (optimizationResult?.isFallback ? "当前显示的是兜底建议，建议稍后重新生成 AI 优化结果。" : "突出岗位相关经历和关键词。") }}</dd>
                <dt>命中要求</dt>
                <dd>{{ joinList(module.matchedRequirements) }}</dd>
                <dt>证据</dt>
                <dd>{{ joinList(module.evidence || []) }}</dd>
                <dt>风险提醒</dt>
                <dd>{{ joinList(module.riskWarnings) }}</dd>
              </dl>
            </section>
          </div>
          <div v-else class="empty-state">生成后展示每个模块的修改原因、关键词补强和风险提醒。</div>
        </article>
      </section>

      <section v-else-if="currentPage === 'template'" class="template-page">
        <article class="panel template-panel-shell">
          <div class="template-panel-title">
            <div>
              <p class="eyebrow">Template Gallery</p>
              <h2>六套正式模板</h2>
              <p class="form-note">五套参考图式中文单栏，一套重做的左窄右宽双栏；模板之间保留风格差异，不再保留过大的布局差异。</p>
            </div>
            <div class="template-chip">{{ selectedTemplateFamily === "double" ? "双栏重做" : "参考图单栏" }}</div>
          </div>

          <div class="template-grid">
            <button
              v-for="template in resumeTemplates"
              :key="template.id"
              type="button"
              class="template-card"
              :class="{ 'is-selected': selectedTemplateId === template.id }"
              @click="selectedTemplateId = template.id"
            >
              <span class="template-swatch" :style="{ background: template.accent }" />
              <strong class="template-name">{{ template.name }}</strong>
              <span class="template-scene">{{ template.scene }}</span>
              <span class="template-tone">{{ template.layout === "cn-campus-double" ? "左窄右宽双栏" : "参考图式中文单栏" }}</span>
            </button>
          </div>

          <section class="source-box template-meta-box">
            <div class="template-meta-grid">
              <p><b>当前数据：</b>{{ templateSource }}</p>
              <p><b>适用场景：</b>{{ selectedTemplate.scene }}</p>
              <p><b>版式类型：</b>{{ selectedTemplateFamily === "double" ? "左窄右宽双栏" : "参考图式单栏" }}</p>
              <p><b>风格描述：</b>{{ selectedTemplate.tone }}</p>
            </div>
            <p class="form-note">{{ templateMessage }}</p>
            <p v-if="templateError" class="alert">{{ templateError }}</p>
            <div class="action-row">
              <button class="secondary-btn" type="button" :disabled="templateStructureLoading || !optimizationResult" @click="generateTemplateResume">
                {{ templateStructureLoading ? "同步中..." : "重新同步优化结果" }}
              </button>
              <button class="secondary-btn" type="button" :disabled="!hasTemplateResume" @click="printTemplateResume">浏览器打印</button>
            </div>
          </section>
        </article>

        <div class="template-workspace">
          <article class="panel template-editor-shell">
            <h2>排版内容</h2>
            <div v-if="templateStructureLoading" class="empty-state">正在把优化结果整理成可排版简历...</div>
            <div v-else-if="!hasTemplateResume" class="empty-state">{{ templateEmptyMessage }}</div>
            <template v-else>
              <section class="form-section">
                <h3>基础信息</h3>
                <div class="form-grid">
                  <label class="field"><span>姓名</span><input v-model="templateWorkspace.profile.name" :disabled="templateEditorDisabled" /></label>
                  <label class="field"><span>职位标题</span><input v-model="templateWorkspace.profile.title" :disabled="templateEditorDisabled" /></label>
                  <label class="field"><span>电话 / 微信</span><input v-model="templateWorkspace.profile.phone" :disabled="templateEditorDisabled" /></label>
                  <label class="field"><span>邮箱</span><input v-model="templateWorkspace.profile.email" :disabled="templateEditorDisabled" /></label>
                  <label class="field"><span>所在城市</span><input v-model="templateWorkspace.profile.city" :disabled="templateEditorDisabled" /></label>
                  <label class="field"><span>个人网站</span><input v-model="templateWorkspace.profile.website" :disabled="templateEditorDisabled" /></label>
                  <label class="field"><span>GitHub</span><input v-model="templateWorkspace.profile.github" :disabled="templateEditorDisabled" /></label>
                  <label class="field"><span>自媒体</span><input v-model="templateWorkspace.profile.media" :disabled="templateEditorDisabled" /></label>
                  <label class="field field-wide"><span>头像链接 / Base64</span><input v-model="templateWorkspace.profile.photo" :disabled="templateEditorDisabled" placeholder="可粘贴图片链接或 base64" /></label>
                  <label class="field field-wide"><span>求职意向</span><input v-model="templateWorkspace.profile.target" :disabled="templateEditorDisabled" /></label>
                  <label class="field field-wide"><span>个人简介</span><textarea v-model="templateWorkspace.profile.summary" :disabled="templateEditorDisabled" rows="4" /></label>
                </div>
              </section>

              <section class="form-section">
                <h3>教育背景</h3>
                <div class="form-grid">
                  <div v-for="item in templateWorkspace.education" :key="item.id" class="field-card field-wide">
                    <button class="icon-button" type="button" :disabled="templateEditorDisabled" @click="removeWorkspaceEntry('education', item.id)">删除</button>
                    <div class="form-grid">
                      <label class="field"><span>学校</span><input v-model="item.title" :disabled="templateEditorDisabled" /></label>
                      <label class="field"><span>学历</span><input v-model="item.organization" :disabled="templateEditorDisabled" /></label>
                      <label class="field"><span>专业</span><input v-model="item.role" :disabled="templateEditorDisabled" /></label>
                      <label class="field"><span>开始时间</span><input v-model="item.start" :disabled="templateEditorDisabled" /></label>
                      <label class="field"><span>结束时间</span><input v-model="item.end" :disabled="templateEditorDisabled" /></label>
                      <label class="field field-wide"><span>核心课程</span><input v-model="item.coursework" :disabled="templateEditorDisabled" placeholder="用 、 或回车语义分隔均可" /></label>
                      <label class="field field-wide"><span>说明 / 亮点</span><textarea v-model="item.details" :disabled="templateEditorDisabled" rows="3" /></label>
                    </div>
                  </div>
                  <button class="add-button field-wide" type="button" :disabled="templateEditorDisabled" @click="addWorkspaceEntry('education')">添加教育背景</button>
                </div>
              </section>

              <section class="form-section">
                <h3>实践 / 实习经历</h3>
                <div class="form-grid">
                  <div v-for="item in templateWorkspace.experience" :key="item.id" class="field-card field-wide">
                    <button class="icon-button" type="button" :disabled="templateEditorDisabled" @click="removeWorkspaceEntry('experience', item.id)">删除</button>
                    <div class="form-grid">
                      <label class="field"><span>经历名称</span><input v-model="item.title" :disabled="templateEditorDisabled" /></label>
                      <label class="field"><span>机构 / 场景</span><input v-model="item.organization" :disabled="templateEditorDisabled" /></label>
                      <label class="field"><span>角色</span><input v-model="item.role" :disabled="templateEditorDisabled" /></label>
                      <label class="field"><span>开始时间</span><input v-model="item.start" :disabled="templateEditorDisabled" /></label>
                      <label class="field"><span>结束时间</span><input v-model="item.end" :disabled="templateEditorDisabled" /></label>
                      <label class="field field-wide"><span>成果描述</span><textarea v-model="item.details" :disabled="templateEditorDisabled" rows="4" /></label>
                    </div>
                  </div>
                  <button class="add-button field-wide" type="button" :disabled="templateEditorDisabled" @click="addWorkspaceEntry('experience')">添加实践 / 实习经历</button>
                </div>
              </section>

              <section class="form-section">
                <h3>核心项目与研发经历</h3>
                <div class="form-grid">
                  <div v-for="item in templateWorkspace.projects" :key="item.id" class="field-card field-wide">
                    <button class="icon-button" type="button" :disabled="templateEditorDisabled" @click="removeWorkspaceEntry('projects', item.id)">删除</button>
                    <div class="form-grid">
                      <label class="field"><span>项目名称</span><input v-model="item.title" :disabled="templateEditorDisabled" /></label>
                      <label class="field"><span>项目归属</span><input v-model="item.organization" :disabled="templateEditorDisabled" /></label>
                      <label class="field"><span>角色</span><input v-model="item.role" :disabled="templateEditorDisabled" /></label>
                      <label class="field"><span>开始时间</span><input v-model="item.start" :disabled="templateEditorDisabled" /></label>
                      <label class="field"><span>结束时间</span><input v-model="item.end" :disabled="templateEditorDisabled" /></label>
                      <label class="field field-wide"><span>项目描述</span><textarea v-model="item.details" :disabled="templateEditorDisabled" rows="4" /></label>
                    </div>
                  </div>
                  <button class="add-button field-wide" type="button" :disabled="templateEditorDisabled" @click="addWorkspaceEntry('projects')">添加项目经历</button>
                </div>
              </section>

              <section class="form-section">
                <h3>技能证书</h3>
                <div class="form-grid">
                  <label class="field field-wide">
                    <span>技能标签 <em>每行一个</em></span>
                    <textarea :value="templateWorkspace.skills.join('\n')" :disabled="templateEditorDisabled" rows="5" @input="handleWorkspaceSkillInput" />
                  </label>
                  <div v-for="item in templateWorkspace.certificates" :key="item.id" class="field-card field-wide">
                    <button class="icon-button" type="button" :disabled="templateEditorDisabled" @click="removeWorkspaceCertificate(item.id)">删除</button>
                    <div class="form-grid">
                      <label class="field"><span>名称</span><input v-model="item.name" :disabled="templateEditorDisabled" /></label>
                      <label class="field"><span>机构</span><input v-model="item.issuer" :disabled="templateEditorDisabled" /></label>
                      <label class="field"><span>时间</span><input v-model="item.date" :disabled="templateEditorDisabled" /></label>
                    </div>
                  </div>
                  <button class="add-button field-wide" type="button" :disabled="templateEditorDisabled" @click="addWorkspaceCertificate">添加证书 / 奖项</button>
                </div>
              </section>

              <section class="form-section">
                <h3>自定义模块</h3>
                <div class="form-grid">
                  <div v-for="item in templateWorkspace.custom" :key="item.id" class="field-card field-wide">
                    <button class="icon-button" type="button" :disabled="templateEditorDisabled" @click="removeWorkspaceCustom(item.id)">删除</button>
                    <div class="form-grid">
                      <label class="field field-wide"><span>标题</span><input v-model="item.title" :disabled="templateEditorDisabled" /></label>
                      <label class="field field-wide"><span>内容</span><textarea v-model="item.details" :disabled="templateEditorDisabled" rows="4" /></label>
                    </div>
                  </div>
                  <button class="add-button field-wide" type="button" :disabled="templateEditorDisabled" @click="addWorkspaceCustom">添加自定义模块</button>
                </div>
              </section>
            </template>
          </article>

          <article class="panel template-style-shell">
            <div class="template-panel-title template-panel-title--compact">
              <div>
                <p class="eyebrow">Style Playground</p>
                <h2>样式控制</h2>
              </div>
            </div>
            <div class="style-panel-section">
              <div class="style-panel-section__title"><h3>主题色</h3></div>
              <div class="style-theme-grid">
                <button
                  v-for="theme in templateThemePresets"
                  :key="theme.id"
                  type="button"
                  class="style-theme-card"
                  :class="{ 'is-selected': templateStyle.themeColor === theme.color }"
                  :disabled="templateEditorDisabled"
                  @click="templateStyle.themeColor = theme.color"
                >
                  <span class="style-theme-card__swatch" :style="{ background: theme.color }" />
                  <span class="style-theme-card__label">{{ theme.label }}</span>
                </button>
              </div>
            </div>

            <div class="style-panel-section">
              <div class="style-panel-section__title"><h3>字体与密度</h3></div>
              <div class="segmented-control">
                <button
                  v-for="option in templateFontOptions"
                  :key="option.id"
                  type="button"
                  :class="{ 'is-active': templateStyle.fontFamily === option.id }"
                  :disabled="templateEditorDisabled"
                  :style="{ fontFamily: option.id }"
                  @click="templateStyle.fontFamily = option.id"
                >
                  {{ option.label }}
                </button>
              </div>
              <div class="style-slider-list">
                <label class="style-range"><span class="style-range__head"><strong>姓名字号</strong><em>{{ templateStyle.nameSize }}px</em></span><input v-model="templateStyle.nameSize" :disabled="templateEditorDisabled" type="range" min="24" max="38" step="1" /></label>
                <label class="style-range"><span class="style-range__head"><strong>页边距</strong><em>{{ templateStyle.pagePadding }}mm</em></span><input v-model="templateStyle.pagePadding" :disabled="templateEditorDisabled" type="range" min="10" max="22" step="1" /></label>
                <label class="style-range"><span class="style-range__head"><strong>行高</strong><em>{{ templateStyle.lineHeight.toFixed(2) }}</em></span><input v-model="templateStyle.lineHeight" :disabled="templateEditorDisabled" type="range" min="1.35" max="1.9" step="0.02" /></label>
              </div>
            </div>

            <div class="style-panel-section">
              <div class="style-panel-section__title"><h3>模式</h3></div>
              <div class="form-grid">
                <label class="toggle-card" :class="{ 'is-checked': templateStyle.denseMode }">
                  <div class="toggle-card__copy"><div><strong>紧凑模式</strong><p>压缩段落与条目间距，更接近一页式正式投递。</p></div></div>
                  <span class="toggle-card__switch"><input v-model="templateStyle.denseMode" :disabled="templateEditorDisabled" type="checkbox" /><span /></span>
                </label>
              </div>
            </div>
          </article>

          <article class="resume-preview-wrap">
            <div v-if="templateStructureLoading" class="empty-state">模板预览生成中，请稍候...</div>
            <div v-else-if="!hasTemplateResume" class="empty-state">{{ templateEmptyMessage }}</div>
            <div v-else class="preview-stage">
              <div class="preview-meta">
                <span>{{ selectedTemplate.name }}</span>
                <span>{{ selectedTemplate.scene }}</span>
                <span>A4 实时预览</span>
              </div>
              <div class="paper-stage">
                <article
                  id="resume-print-area"
                  class="resume-page"
                  :class="[
                    selectedTemplateFamily === 'double' ? 'resume-cn-campus-double' : 'resume-cn-campus-single',
                    `resume-variant-${selectedTemplate.styleVariant || 'clean'}`,
                    { 'resume-dense': templateStyle.denseMode },
                  ]"
                  :style="templateStyleVars"
                >
                  <template v-if="selectedTemplateFamily === 'double'">
                    <div class="resume-cn-double-shell">
                      <aside class="resume-cn-double-sidebar">
                        <div class="resume-photo-block" :class="{ 'resume-photo-block--empty': !previewPhoto }">
                          <img v-if="previewPhoto" :src="previewPhoto" alt="头像" class="resume-photo" />
                          <div v-else class="resume-photo resume-photo--placeholder">头像</div>
                        </div>
                        <header class="resume-cn-double-head">
                          <h1>{{ templateWorkspace.profile.name || "请补充姓名" }}</h1>
                          <p>{{ templateWorkspace.profile.title || templateWorkspace.profile.target || "请补充职位标题" }}</p>
                        </header>
                        <section class="resume-section" v-if="previewSidebarContactItems.length">
                          <h2>联系方式</h2>
                          <div class="resume-contact-stack">
                            <span v-for="item in previewSidebarContactItems" :key="item">{{ item }}</span>
                          </div>
                        </section>
                        <section class="resume-section" v-if="previewHasSkills">
                          <h2>技能标签</h2>
                          <div class="skill-tags">
                            <span v-for="skill in templateWorkspace.skills.filter(Boolean)" :key="skill">{{ skill }}</span>
                          </div>
                        </section>
                        <section class="resume-section" v-if="previewHasCertificates">
                          <h2>证书 / 奖项</h2>
                          <div v-for="item in templateWorkspace.certificates.filter((entry) => entry.name || entry.issuer || entry.date)" :key="item.id" class="resume-entry resume-entry--compact">
                            <strong>{{ renderCertificateTitle(item) }}</strong>
                            <span>{{ item.date }}</span>
                          </div>
                        </section>
                        <section class="resume-section" v-if="previewHasSummary">
                          <h2>个人概况</h2>
                          <ul class="resume-lines">
                            <li v-for="line in renderDetailsLines(templateWorkspace.profile.summary)" :key="line">{{ line }}</li>
                          </ul>
                        </section>
                      </aside>

                      <main class="resume-cn-double-main">
                        <section v-if="previewHasEducation" class="resume-section">
                          <h2>教育背景</h2>
                          <div v-for="item in templateWorkspace.education.filter(hasWorkspaceEntryContent)" :key="item.id" class="resume-entry">
                            <div class="entry-head">
                              <strong>{{ renderWorkspaceHeadline(item) }}</strong>
                              <span>{{ entryPeriod(item) }}</span>
                            </div>
                            <p v-if="item.coursework" class="resume-coursework">核心课程：{{ item.coursework }}</p>
                            <ul class="resume-lines"><li v-for="line in renderDetailsLines(item.details)" :key="line">{{ line }}</li></ul>
                          </div>
                        </section>
                        <section v-if="previewHasProjects" class="resume-section">
                          <h2>核心项目与研发经历</h2>
                          <div v-for="item in templateWorkspace.projects.filter(hasWorkspaceEntryContent)" :key="item.id" class="resume-entry">
                            <div class="entry-head">
                              <strong>{{ renderWorkspaceHeadline(item) }}</strong>
                              <span>{{ entryPeriod(item) }}</span>
                            </div>
                            <ul class="resume-lines"><li v-for="line in renderDetailsLines(item.details)" :key="line">{{ line }}</li></ul>
                          </div>
                        </section>
                        <section v-if="previewHasExperience" class="resume-section">
                          <h2>实践 / 实习经历</h2>
                          <div v-for="item in templateWorkspace.experience.filter(hasWorkspaceEntryContent)" :key="item.id" class="resume-entry">
                            <div class="entry-head">
                              <strong>{{ renderWorkspaceHeadline(item) }}</strong>
                              <span>{{ entryPeriod(item) }}</span>
                            </div>
                            <ul class="resume-lines"><li v-for="line in renderDetailsLines(item.details)" :key="line">{{ line }}</li></ul>
                          </div>
                        </section>
                        <section v-for="item in templateWorkspace.custom.filter((entry) => entry.title || entry.details)" :key="item.id" class="resume-section">
                          <h2>{{ item.title || "自定义模块" }}</h2>
                          <ul class="resume-lines"><li v-for="line in renderDetailsLines(item.details)" :key="line">{{ line }}</li></ul>
                        </section>
                      </main>
                    </div>
                  </template>

                  <template v-else>
                    <header class="resume-cn-header">
                      <div class="resume-cn-header-main">
                        <h1>{{ templateWorkspace.profile.name || "请补充姓名" }}</h1>
                        <p>{{ templateWorkspace.profile.title || templateWorkspace.profile.target || "请补充职位标题" }}</p>
                        <div class="resume-contact-grid">
                          <span v-for="item in previewContactItems" :key="item">{{ item }}</span>
                        </div>
                      </div>
                      <div v-if="previewPhoto" class="resume-cn-header-photo">
                        <img :src="previewPhoto" alt="头像" class="resume-photo" />
                      </div>
                    </header>

                    <section v-if="previewHasEducation" class="resume-section">
                      <h2>教育背景</h2>
                      <div v-for="item in templateWorkspace.education.filter(hasWorkspaceEntryContent)" :key="item.id" class="resume-entry">
                        <div class="entry-head">
                          <strong>{{ renderWorkspaceHeadline(item) }}</strong>
                          <span>{{ entryPeriod(item) }}</span>
                        </div>
                        <p v-if="item.coursework" class="resume-coursework">核心课程：{{ item.coursework }}</p>
                        <ul class="resume-lines"><li v-for="line in renderDetailsLines(item.details)" :key="line">{{ line }}</li></ul>
                      </div>
                    </section>
                    <section v-if="previewHasProjects" class="resume-section">
                      <h2>核心项目与研发经历</h2>
                      <div v-for="item in templateWorkspace.projects.filter(hasWorkspaceEntryContent)" :key="item.id" class="resume-entry">
                        <div class="entry-head">
                          <strong>{{ renderWorkspaceHeadline(item) }}</strong>
                          <span>{{ entryPeriod(item) }}</span>
                        </div>
                        <ul class="resume-lines"><li v-for="line in renderDetailsLines(item.details)" :key="line">{{ line }}</li></ul>
                      </div>
                    </section>
                    <section v-if="previewHasExperience" class="resume-section">
                      <h2>实践 / 实习经历</h2>
                      <div v-for="item in templateWorkspace.experience.filter(hasWorkspaceEntryContent)" :key="item.id" class="resume-entry">
                        <div class="entry-head">
                          <strong>{{ renderWorkspaceHeadline(item) }}</strong>
                          <span>{{ entryPeriod(item) }}</span>
                        </div>
                        <ul class="resume-lines"><li v-for="line in renderDetailsLines(item.details)" :key="line">{{ line }}</li></ul>
                      </div>
                    </section>
                    <section v-if="previewHasSkills || previewHasCertificates" class="resume-section">
                      <h2>技能证书</h2>
                      <div v-if="previewHasSkills" class="skill-tags">
                        <span v-for="skill in templateWorkspace.skills.filter(Boolean)" :key="skill">{{ skill }}</span>
                      </div>
                      <div v-if="previewHasCertificates" class="resume-cert-list">
                        <div v-for="item in templateWorkspace.certificates.filter((entry) => entry.name || entry.issuer || entry.date)" :key="item.id" class="resume-entry resume-entry--compact">
                          <strong>{{ renderCertificateTitle(item) }}</strong>
                          <span>{{ item.date }}</span>
                        </div>
                      </div>
                    </section>
                    <section v-for="item in templateWorkspace.custom.filter((entry) => entry.title || entry.details)" :key="item.id" class="resume-section">
                      <h2>{{ item.title || "自定义模块" }}</h2>
                      <ul class="resume-lines"><li v-for="line in renderDetailsLines(item.details)" :key="line">{{ line }}</li></ul>
                    </section>
                  </template>
                </article>
              </div>
            </div>
          </article>
        </div>
      </section>

      <section v-else-if="currentPage === 'delivery'" class="content-grid">
        <article class="panel">
          <h2>投递优先级</h2>
          <button class="primary-btn" type="button" :disabled="deliveryLoading" @click="generateDeliveryStrategy">
            {{ deliveryLoading ? "生成中..." : "生成投递策略" }}
          </button>
          <div class="priority-card">
            <strong>{{ applicationStrategy?.priority || applyLabel(selectedCandidate?.metrics.total || 0) }}</strong>
            <p>{{ applicationStrategy ? (applicationStrategy.shouldApply ? "建议投递，并按下方策略执行。" : "当前更建议先补强再投递。") : deliveryReason }}</p>
          </div>
          <p v-if="deliveryError" class="alert">{{ deliveryError }}</p>
        </article>
        <article class="panel">
          <h2>推荐投递话术</h2>
          <p class="script-box">{{ applicationStrategy?.applicationMessage || `您好，我正在申请${jobForm.title || "目标岗位"}。我已根据 JD 调整简历，重点突出与岗位相关的项目经历和技能，希望有机会进一步沟通。谢谢。` }}</p>
        </article>
        <article class="panel">
          <h2>简历版本建议</h2>
          <p v-if="applicationStrategy?.resumeVersionAdvice" class="script-box">{{ applicationStrategy.resumeVersionAdvice }}</p>
          <ul class="action-list">
            <li v-for="item in deliveryChecklist" :key="item">{{ item }}</li>
          </ul>
        </article>

        <article v-if="applicationStrategy" class="panel full-span">
          <h2>渠道与跟进</h2>
          <div class="content-grid inner-grid">
            <div>
              <p class="panel-subtitle">推荐投递渠道</p>
              <ul class="action-list">
                <li v-for="item in applicationStrategy.bestChannels" :key="item">{{ item }}</li>
              </ul>
            </div>
            <div>
              <p class="panel-subtitle">跟进计划</p>
              <ul class="action-list">
                <li v-for="item in applicationStrategy.followUpPlan" :key="item">{{ item }}</li>
              </ul>
            </div>
            <div>
              <p class="panel-subtitle">风险提醒</p>
              <ul class="action-list">
                <li v-for="item in applicationStrategy.riskWarnings" :key="item">{{ item }}</li>
              </ul>
            </div>
          </div>
        </article>
      </section>

      <section v-else-if="currentPage === 'interview'" class="content-grid">
        <article class="panel wide-panel">
          <h2>岗位相关问题</h2>
          <button class="primary-btn" type="button" :disabled="interviewLoading" @click="generateInterviewPlan">
            {{ interviewLoading ? "生成中..." : "生成面试准备" }}
          </button>
          <div v-if="interviewQuestionCards.length" class="question-list">
            <article v-for="question in interviewQuestionCards" :key="question.question">
              <span>{{ question.category }}</span>
              <b>{{ question.difficulty }}</b>
              <p>{{ question.question }}</p>
              <p v-if="question.tip" class="question-note">{{ question.tip }}</p>
            </article>
          </div>
          <div v-else class="empty-state">完成简历诊断后生成岗位相关问题。</div>
          <p v-if="interviewError" class="alert">{{ interviewError }}</p>
        </article>
        <article class="panel">
          <h2>简历追问</h2>
          <ul class="action-list">
            <li v-for="gap in interviewFollowups" :key="gap">{{ gap }}</li>
          </ul>
        </article>
        <article class="panel">
          <h2>回答建议</h2>
          <ul class="action-list">
            <li v-for="item in interviewAdviceList" :key="item">{{ item }}</li>
          </ul>
        </article>

        <article v-if="interviewPrep" class="panel full-span">
          <h2>练习重点</h2>
          <div class="content-grid inner-grid">
            <div>
              <p class="panel-subtitle">评分维度</p>
              <ul class="action-list">
                <li v-for="item in interviewPrep.scoreDimensions" :key="item">{{ item }}</li>
              </ul>
            </div>
            <div>
              <p class="panel-subtitle">风险点</p>
              <ul class="action-list">
                <li v-for="item in interviewPrep.riskPoints" :key="item">{{ item }}</li>
              </ul>
            </div>
            <div>
              <p class="panel-subtitle">练习计划</p>
              <ul class="action-list">
                <li v-for="item in interviewPrep.practicePlan" :key="item">{{ item }}</li>
              </ul>
            </div>
          </div>
        </article>
      </section>

      <section v-else class="content-grid">
        <article class="panel wide-panel">
          <h2>数据分析</h2>
          <p class="muted">数据分析页只展示有来源的数据，不展示无来源 mock 数据。</p>
          <button class="primary-btn" type="button" :disabled="analyticsLoading" @click="loadAnalytics">
            {{ analyticsLoading ? "加载中..." : "加载带来源数据" }}
          </button>
          <p v-if="analyticsError" class="alert">{{ analyticsError }}</p>
        </article>

        <template v-if="analyticsData">
          <article class="metric-card">
            <span>简历数</span>
            <strong>{{ analyticsData?.totalResumes }}</strong>
            <small>来源支撑</small>
          </article>
          <article class="metric-card">
            <span>推荐数</span>
            <strong>{{ analyticsData?.recommendedCount }}</strong>
            <small>来源支撑</small>
          </article>
          <article class="metric-card">
            <span>平均分</span>
            <strong>{{ analyticsData?.averageScore }}</strong>
            <small>来源支撑</small>
          </article>
          <article class="panel full-span">
            <h2>数据来源</h2>
            <div class="source-list">
              <article v-for="source in analyticsSources" :key="source.link">
                <h3>{{ source.title }}</h3>
                <a :href="source.link" target="_blank" rel="noreferrer">{{ source.link }}</a>
                <p>机构：{{ source.organization }}</p>
                <p>发布时间：{{ source.publishedAt }}</p>
                <p>访问时间：{{ source.accessedAt }}</p>
              </article>
            </div>
          </article>
        </template>
      </section>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import {
  ApiRequestError,
  createDefaultTemplateStyleSettings,
  createEmptyTemplateWorkspaceData,
  exportResumePdf,
  extractJobProfile,
  generateApplicationStrategy,
  generateCareerPlan as requestCareerPlan,
  generateInterviewPrepare,
  getRecruitmentAnalytics,
  getResumeTemplates,
  matchResume,
  ocrResume,
  optimizeResumeForJob,
  structureResumeData,
  type UserRole,
} from "../api/client";
import type {
  AnalyticsResponse,
  AnalyticsSource,
  ApplicationStrategyResponse,
  InterviewPrepareResponse,
  JobProfile,
  MatchResponse,
  ResumeOptimizeResponse,
  ResumeContextPayload,
  ResumeTemplateSummary,
  ResumeTemplateLayout,
  Section,
  StructuredResume,
  StructuredResumeEntry,
  StructuredResumeSkillGroup,
  TemplateStyleSettings,
  TemplateWorkspaceCertificate,
  TemplateWorkspaceCustomSection,
  TemplateWorkspaceData,
  TemplateWorkspaceEntry,
} from "../types";

type PageKey = "dashboard" | "planning" | "job" | "diagnosis" | "optimize" | "template" | "delivery" | "interview" | "analytics";
type CandidateStatus = "queued" | "uploading" | "parsing" | "matching" | "done" | "error";
type DiagnosisPhase = "idle" | "uploading" | "parsing" | "matching" | "done" | "error";
type OptimizeStage = "idle" | "validating" | "reading" | "generating" | "done" | "failed";
type FlowIssue = {
  stage: string;
  message: string;
  retryable: boolean;
};

type TemplatePreset = ResumeTemplateSummary & {
  layout: ResumeTemplateLayout;
  accent: string;
  scene: string;
  tone: string;
};

type Candidate = {
  localId: number;
  file: File | null;
  displayName: string;
  status: CandidateStatus;
  phase: DiagnosisPhase;
  phaseLabel: string;
  progress: number;
  resumeId: number | null;
  sections: Section[];
  metrics: {
    total: number;
    skill: number;
    experience: number;
    project: number;
  };
  summary: string;
  skillMatches: string[];
  experienceSupport: string[];
  gaps: string[];
  questions: Array<{ category: string; difficulty: string; question: string }>;
  matchResult: MatchResponse["result"] | null;
  error: string;
  errorStage: string;
  errorAction: string;
  retryable: boolean;
  requestEndpoint: string;
  lastUpdatedAt: number | null;
};

const pages: Array<{ key: PageKey; label: string; icon: string; subtitle: string }> = [
  { key: "dashboard", label: "工作台", icon: "⌂", subtitle: "大学生求职全流程入口。" },
  { key: "job", label: "岗位解析", icon: "JD", subtitle: "解析岗位 JD，提取硬性要求、加分项和关键词。" },
  { key: "diagnosis", label: "简历诊断", icon: "✓", subtitle: "判断我适不适合这个岗位、哪里不够、要不要投。" },
  { key: "optimize", label: "简历优化", icon: "✎", subtitle: "把已有经历表达得更贴近岗位，不虚构事实。" },
  { key: "template", label: "简历排版", icon: "A4", subtitle: "选择正式模板，预览 ATS 友好 A4 简历并导出 PDF。" },
  { key: "delivery", label: "投递建议", icon: "↗", subtitle: "生成投递优先级、投递话术和简历版本建议。" },
  { key: "planning", label: "职业规划", icon: "◎", subtitle: "填写专业、年级、技能和目标方向，生成岗位方向与行动计划。" },
  { key: "interview", label: "面试准备", icon: "?", subtitle: "生成岗位相关问题、简历追问和回答建议。" },
  { key: "analytics", label: "数据分析", icon: "▥", subtitle: "仅展示带来源的数据分析。" },
];

const currentPage = ref<PageKey>("dashboard");
const currentUserRole = ref<UserRole>("student");
const studentPages: PageKey[] = ["dashboard", "job", "diagnosis", "optimize", "template", "delivery", "planning", "interview"];
const adminPages: PageKey[] = ["analytics"];
const visiblePages = computed(() => pages.filter((item) => (currentUserRole.value === "student" ? studentPages : adminPages).includes(item.key)));
const pageTitle = computed(() => visiblePages.value.find((item) => item.key === currentPage.value)?.label || "");
const pageSubtitle = computed(() => visiblePages.value.find((item) => item.key === currentPage.value)?.subtitle || "");

const flowSteps = ["工作台", "岗位解析", "简历诊断", "简历优化", "简历排版", "投递建议", "职业规划", "面试准备"];
const siliconFlowModels = ["deepseek-ai/DeepSeek-V4-Flash", "Qwen/Qwen2.5-32B-Instruct", "Qwen/Qwen2.5-72B-Instruct", "deepseek-ai/DeepSeek-V3", "deepseek-ai/DeepSeek-R1"];
const selectedModel = ref(siliconFlowModels[0]);

const careerForm = reactive({
  major: "",
  grade: "大三",
  skills: "",
  direction: "",
  targetCity: "",
  interests: "",
});
const careerPlan = reactive({
  roles: [] as Array<{ title: string; reason: string; fit: number }>,
  actions: [] as string[],
  portfolioSuggestions: [] as string[],
  riskWarnings: [] as string[],
  cityAdvice: "",
});

const jobForm = reactive<JobProfile>({
  title: "前端实习生",
  responsibilities: "参与 Web 前端页面和组件开发，使用 Vue 或 React 完成业务功能，与产品和后端协作，要求掌握 JavaScript、TypeScript、组件化开发，有项目经验者优先。",
  must_haves: ["掌握 JavaScript / TypeScript", "了解 Vue 或 React", "有前端项目经验"],
  nice_to_haves: ["有实习经历", "做过数据看板或后台系统", "了解工程化工具"],
  experience_years: "应届或实习生",
  keywords: ["Vue", "React", "TypeScript", "组件化", "前端项目"],
});
const mustHaveText = ref(jobForm.must_haves.join("\n"));
const niceHaveText = ref(jobForm.nice_to_haves.join("\n"));
const keywordText = ref(jobForm.keywords.join(", "));

const selectedFiles = ref<File[]>([]);
const fileInputRef = ref<HTMLInputElement | null>(null);
const fileFeedback = ref<string[]>([]);
const candidates = ref<Candidate[]>([]);
const selectedLocalId = ref<number | null>(null);
const isDragging = ref(false);
const processing = ref(false);
const optimizing = ref(false);
const optimizeStage = ref<OptimizeStage>("idle");
const extractingJob = ref(false);
const careerPlanLoading = ref(false);
const deliveryLoading = ref(false);
const interviewLoading = ref(false);
const extractionMessage = ref("");
const careerPlanMessage = ref("");
const careerAutofillLoading = ref(false);
const careerAutofillMessage = ref("");
const careerPlanIssue = ref<FlowIssue | null>(null);
const diagnosisIssue = ref<FlowIssue | null>(null);
const optimizeIssue = ref<FlowIssue | null>(null);
const deliveryError = ref("");
const interviewError = ref("");
const optimizationResult = ref<ResumeOptimizeResponse | null>(null);
const applicationStrategy = ref<ApplicationStrategyResponse | null>(null);
const interviewPrep = ref<InterviewPrepareResponse | null>(null);
const analyticsData = ref<AnalyticsResponse | null>(null);
const analyticsLoading = ref(false);
const analyticsError = ref("");
const templateExporting = ref(false);
const templateStructureLoading = ref(false);
const templateError = ref("");
const templateMessage = ref("优化完成后，可一键进入模板页生成完整排版简历。");
const templateStructuredResume = ref<StructuredResume | null>(null);
const templateSource = ref("默认示例");
const optimizationVersion = ref(0);
const templateSyncedOptimizationVersion = ref(0);
let nextLocalId = 1;
const diagnosisPhaseOrder: DiagnosisPhase[] = ["uploading", "parsing", "matching", "done"];
const optimizeStageOrder: OptimizeStage[] = ["validating", "reading", "generating", "done"];
const fallbackResumeTemplates: TemplatePreset[] = [
  {
    id: "campus-clean",
    name: "校园清简",
    scene: "校招、实习、通用投递",
    tone: "参考图式中文单栏，横向联系方式，正文紧凑",
    accent: "#2f6f73",
    layout: "cn-campus-single",
    styleVariant: "clean",
    suitableRoles: ["互联网", "产品", "运营"],
    source: "本地迁入自 4173 模板工作台",
    sourceUrl: "internal://resume-templates/campus-clean",
    license: "项目演示与课程竞赛可用；商业分发前建议替换为自有设计资产",
  },
  {
    id: "tech-intern",
    name: "技术实习",
    scene: "前端、后端、算法、数据",
    tone: "参考图式中文单栏，项目和技能更突出",
    accent: "#2d5b88",
    layout: "cn-campus-single",
    styleVariant: "tech",
    suitableRoles: ["前端", "后端", "数据"],
    source: "本地迁入自 4173 模板工作台",
    sourceUrl: "internal://resume-templates/tech-intern",
    license: "项目演示与课程竞赛可用；商业分发前建议替换为自有设计资产",
  },
  {
    id: "product-ops",
    name: "产品运营",
    scene: "产品、运营、内容、新媒体",
    tone: "参考图式中文单栏，实践与成果导向",
    accent: "#8a4b39",
    layout: "cn-campus-single",
    styleVariant: "ops",
    suitableRoles: ["产品", "运营", "内容"],
    source: "本地迁入自 4173 模板工作台",
    sourceUrl: "internal://resume-templates/product-ops",
    license: "项目演示与课程竞赛可用；商业分发前建议替换为自有设计资产",
  },
  {
    id: "research-note",
    name: "研究纪要",
    scene: "科研、教育、留学申请",
    tone: "参考图式中文单栏，标题更克制，学术感更强",
    accent: "#3d5a80",
    layout: "cn-campus-single",
    styleVariant: "research",
    suitableRoles: ["科研", "教育", "申请"],
    source: "本地迁入自 4173 模板工作台",
    sourceUrl: "internal://resume-templates/research-note",
    license: "项目演示与课程竞赛可用；商业分发前建议替换为自有设计资产",
  },
  {
    id: "state-owned",
    name: "传统正式",
    scene: "国企、事业单位、传统行业",
    tone: "参考图式中文单栏，宋衬混排，正式稳妥",
    accent: "#7c2222",
    layout: "cn-campus-single",
    styleVariant: "formal",
    suitableRoles: ["国企", "事业单位", "传统行业"],
    source: "本地迁入自 4173 模板工作台",
    sourceUrl: "internal://resume-templates/state-owned",
    license: "项目演示与课程竞赛可用；商业分发前建议替换为自有设计资产",
  },
  {
    id: "editorial-split",
    name: "双栏精选",
    scene: "信息量大、技能丰富、需要侧栏归纳",
    tone: "左窄右宽，保留双栏特色，但更适合中文正式投递",
    accent: "#30445f",
    layout: "cn-campus-double",
    styleVariant: "double",
    suitableRoles: ["技术", "综合", "高信息密度"],
    source: "本地迁入自 4173 模板工作台",
    sourceUrl: "internal://resume-templates/editorial-split",
    license: "项目演示与课程竞赛可用；商业分发前建议替换为自有设计资产",
  },
];
const templateThemePresets = [
  { id: "teal", label: "青釉", color: "#2f6f73" },
  { id: "brick", label: "陶砖", color: "#8a4b39" },
  { id: "olive", label: "橄榄", color: "#556b4d" },
  { id: "ink", label: "墨黑", color: "#30343a" },
  { id: "royal", label: "靛青", color: "#315da8" },
  { id: "wine", label: "酒红", color: "#8a1f1f" },
];
const templateFontOptions = [
  { id: '"Noto Serif SC", "Microsoft YaHei", "PingFang SC", Georgia, serif', label: "衬线" },
  { id: '"Noto Sans SC", "Microsoft YaHei", "PingFang SC", sans-serif', label: "黑体" },
  { id: '"SimSun", "Songti SC", serif', label: "宋体" },
  { id: '"LXGW WenKai Screen", "KaiTi", serif', label: "文楷" },
];
const resumeTemplates = ref<TemplatePreset[]>(fallbackResumeTemplates);
const selectedTemplateId = ref("campus-clean");
const selectedTemplate = computed<TemplatePreset>(
  () => resumeTemplates.value.find((item) => item.id === selectedTemplateId.value) || resumeTemplates.value[0] || fallbackResumeTemplates[0],
);
const selectedTemplateFamily = computed(() => selectedTemplate.value.layout === "cn-campus-double" ? "double" : "single");
const templateWorkspace = reactive<TemplateWorkspaceData>(createEmptyTemplateWorkspaceData());
const templateStyle = reactive<TemplateStyleSettings>(createDefaultTemplateStyleSettings());
const isApplyingTemplateWorkspace = ref(false);

const canRunDiagnosis = computed(() => selectedFiles.value.length > 0 && !processing.value && Boolean(jobForm.title.trim()) && Boolean(jobForm.responsibilities.trim()));
const canOptimize = computed(() => selectedFiles.value.length > 0 && !optimizing.value && Boolean(jobForm.title.trim()) && Boolean(jobForm.responsibilities.trim()));
const careerAutofillHint = computed(() => {
  if (careerAutofillLoading.value) return "会先解析当前已上传的简历，再回填专业、年级和技能信息。";
  if (!selectedFiles.value.length && !selectedCandidate.value) return "先上传一份简历，这里就能直接帮你回填。";
  if (selectedCandidate.value?.sections.length) return "将优先读取当前选中简历的解析结果。";
  return "如果简历还没解析，这里会自动先做一次简历解析。";
});
const selectedCandidate = computed(() => candidates.value.find((item) => item.localId === selectedLocalId.value) || null);
const rankedCandidates = computed(() => [...candidates.value].sort((a, b) => b.metrics.total - a.metrics.total));
const diagnosisButtonLabel = computed(() => {
  if (!processing.value) return "AI 诊断适配度";
  return selectedCandidate.value?.phaseLabel ? `${selectedCandidate.value.phaseLabel}...` : "正在诊断...";
});
const diagnosisTimeline = computed(() => diagnosisPhaseOrder.map((phase) => {
  const candidate = selectedCandidate.value;
  const activeIndex = candidate ? diagnosisPhaseOrder.indexOf(candidate.phase) : -1;
  const phaseIndex = diagnosisPhaseOrder.indexOf(phase);
  const label = phaseLabelMap(phase);
  return {
    key: phase,
    label,
    done: activeIndex > phaseIndex || candidate?.phase === "done",
    active: candidate?.phase === phase,
  };
}));
const optimizeTimeline = computed(() => optimizeStageOrder.map((stage) => {
  const activeIndex = optimizeStageOrder.indexOf(optimizeStage.value);
  const stageIndex = optimizeStageOrder.indexOf(stage);
  return {
    key: stage,
    label: optimizeStageLabel(stage),
    done: activeIndex > stageIndex || optimizeStage.value === "done",
    active: optimizeStage.value === stage,
  };
}));
const diagnosisSummary = computed(() => {
  const candidate = selectedCandidate.value;
  if (!candidate) return "点击 AI 诊断适配度后查看结果。";
  if (candidate.phase === "error") {
    return candidate.errorAction || "本次诊断未完成，你可以直接重新诊断。";
  }
  if (candidate.phase === "done") {
    return "诊断已完成，可以查看匹配分、缺口和下一步建议。";
  }
  return `${candidate.phaseLabel}，请稍候。`;
});
const optimizeHint = computed(() => {
  if (!selectedFiles.value.length) return "请先上传简历，再生成岗位定制简历。";
  if (!jobForm.title.trim() || !jobForm.responsibilities.trim()) return "请先填写岗位名称和岗位 JD。";
  if (!selectedCandidate.value?.resumeId) return "当前还没有简历解析结果，点击后会先执行简历解析。";
  return "将基于简历解析结果和岗位信息生成定制化版本。";
});
const optimizeHintText = computed(() => {
  if (optimizing.value) return `${optimizeStageLabel(optimizeStage.value)}...`;
  if (!selectedFiles.value.length && !selectedCandidate.value) return "请先上传简历，并在简历诊断中完成解析。";
  if (!jobForm.responsibilities.trim()) return "请先填写岗位 JD，再生成岗位定制简历。";
  if (!selectedCandidate.value?.resumeId) return "请先完成简历诊断和简历解析，优化不会自动触发 OCR。";
  if (!selectedCandidate.value.sections.length) return "已有 resumeId，但缺少结构化解析结果，请返回先解析简历。";
  if (optimizeStage.value === "done") return "岗位定制简历已生成，可继续重试或进入排版。";
  if (optimizeStage.value === "failed") return "本次优化未完成，可重试优化或返回先解析简历。";
  return "将基于已解析简历和岗位 JD 生成定制化版本。";
});
const optimizeEntryHint = computed(() => {
  if (optimizing.value) return "当前正在生成岗位定制简历，请稍候查看结果。";
  if (!jobForm.title.trim() || !jobForm.responsibilities.trim()) return "请先补全岗位名称和岗位 JD。";
  if (!selectedFiles.value.length) return "请先上传 PDF 简历，再进入优化。";
  if (optimizationResult.value && optimizeStage.value === "done") return "优化结果已生成，点击可继续查看或重新调整。";
  return "条件已满足，点击后会直接打开并运行简历优化。";
});
const canGenerateTemplateResume = computed(() => Boolean(optimizationResult.value) && !templateStructureLoading.value);
const templateNeedsSync = computed(() => Boolean(optimizationResult.value) && templateSyncedOptimizationVersion.value !== optimizationVersion.value);
const hasTemplateResume = computed(() => Boolean(templateStructuredResume.value));
const templateEditorDisabled = computed(() => templateStructureLoading.value || !templateStructuredResume.value);
const templateEmptyMessage = computed(() => {
  if (templateStructureLoading.value) return "正在整合优化结果并生成排版简历...";
  if (templateError.value) return templateError.value;
  return "请先在“简历优化”页生成岗位定制简历，然后使用“一键生成排版简历”。";
});
const previewContactItems = computed(() =>
  [
    templateWorkspace.profile.phone.trim() && `电话/微信：${templateWorkspace.profile.phone.trim()}`,
    templateWorkspace.profile.email.trim() && `邮箱：${templateWorkspace.profile.email.trim()}`,
    templateWorkspace.profile.github.trim() && `GitHub：${templateWorkspace.profile.github.trim()}`,
    templateWorkspace.profile.website.trim() && `个人网站：${templateWorkspace.profile.website.trim()}`,
    templateWorkspace.profile.media.trim() && `自媒体：${templateWorkspace.profile.media.trim()}`,
  ].filter(Boolean) as string[],
);
const previewSidebarContactItems = computed(() =>
  [
    templateWorkspace.profile.phone.trim(),
    templateWorkspace.profile.email.trim(),
    templateWorkspace.profile.github.trim(),
    templateWorkspace.profile.website.trim(),
    templateWorkspace.profile.media.trim(),
    templateWorkspace.profile.city.trim(),
  ].filter(Boolean),
);
const previewPhoto = computed(() => templateWorkspace.profile.photo.trim());
const previewHasSummary = computed(() => Boolean(templateWorkspace.profile.summary.trim()));
const previewHasEducation = computed(() => templateWorkspace.education.some((item) => hasWorkspaceEntryContent(item)));
const previewHasExperience = computed(() => templateWorkspace.experience.some((item) => hasWorkspaceEntryContent(item)));
const previewHasProjects = computed(() => templateWorkspace.projects.some((item) => hasWorkspaceEntryContent(item)));
const previewHasSkills = computed(() => templateWorkspace.skills.some((item) => item.trim()));
const previewHasCertificates = computed(() => templateWorkspace.certificates.some((item) => item.name.trim() || item.issuer.trim() || item.date.trim()));
const optimizationCoverage = computed(() => {
  const fallback = optimizationResult.value?.modules.length || 0;
  return optimizationResult.value?.coverage || {
    totalModules: fallback,
    optimizedModules: fallback,
    skippedModules: optimizationResult.value?.skippedModules?.length || 0,
  };
});
const optimizationSkippedModules = computed(() => optimizationResult.value?.skippedModules || []);
const optimizationRecognizedBlocks = computed(() => optimizationResult.value?.normalizedBlocks || []);
const optimizationDisplayModules = computed(() => {
  if (optimizationResult.value?.beforeAfterGroups?.length) return optimizationResult.value.beforeAfterGroups;
  return optimizationResult.value?.modules || [];
});
const optimizationFinalDraftSections = computed(() => optimizationResult.value?.finalResumeSections || []);
const optimizationFinalDraftText = computed(() => {
  if (optimizationFinalDraftSections.value.length) return "";
  return optimizationResult.value?.finalResumeText || "";
});

const scoreBars = computed(() => {
  const candidate = selectedCandidate.value;
  if (!candidate) return [];
  return [
    { label: "总分", value: candidate.metrics.total },
    { label: "技能", value: candidate.metrics.skill },
    { label: "经验", value: candidate.metrics.experience },
    { label: "项目", value: candidate.metrics.project },
  ];
});
const deliveryReason = computed(() => {
  const score = selectedCandidate.value?.metrics.total || 0;
  if (score >= 80) return "匹配度较高，建议优先投递，并准备项目细节追问。";
  if (score >= 65) return "值得投递，但建议先做岗位定制简历，突出最相关经历。";
  if (score >= 50) return "可以作为备选岗位，先补强关键词和项目证据。";
  return "建议暂缓投递，先补齐核心技能或换更匹配的岗位。";
});
const deliveryChecklist = computed(() => {
  if (applicationStrategy.value?.resumeContentToImprove?.length) {
    return applicationStrategy.value.resumeContentToImprove;
  }
  return [
    "文件名包含姓名、学校、岗位方向。",
    "前 1/3 屏突出岗位关键词和最相关项目。",
    "如果适配分低于 70，先使用岗位定制简历再投递。",
  ];
});
const interviewQuestionCards = computed(() => {
  if (interviewPrep.value) {
    const groups = [
      ["高频问题", "高频", interviewPrep.value.highFrequencyQuestions],
      ["项目追问", "项目", interviewPrep.value.projectQuestions],
      ["行为面试", "行为", interviewPrep.value.behavioralQuestions],
    ] as const;
    return groups.flatMap(([category, difficulty, items]) =>
      items.slice(0, 2).map((item) => ({
        category,
        difficulty,
        question: item.question,
        tip: item.answerFramework || (item.scoreDimensions || []).join(" / "),
      })),
    );
  }
  return (selectedCandidate.value?.questions || []).map((item) => ({ ...item, tip: "" }));
});
const interviewFollowups = computed(() => {
  if (interviewPrep.value?.resumeFollowUpQuestions?.length) {
    return interviewPrep.value.resumeFollowUpQuestions.map(
      (item) => item.riskPoint ? `${item.question}：${item.riskPoint}` : item.question,
    );
  }
  return selectedCandidate.value?.gaps.length ? selectedCandidate.value.gaps : ["请准备一个最能证明岗位能力的项目。"];
});
const interviewAdviceList = computed(() => {
  if (interviewPrep.value?.answerFrameworks?.length) {
    return interviewPrep.value.answerFrameworks.map(
      (item) => `${item.name}：${item.usage}，结构为 ${item.structure.join(" - ")}`,
    );
  }
  return [
    "先讲项目背景，再讲你负责的动作，最后讲可量化结果。",
    "遇到不会的问题，说明分析路径和补齐计划。",
    "每个回答都尽量回扣岗位 JD 的关键词。",
  ];
});
const analyticsSources = computed<AnalyticsSource[]>(() => analyticsData.value?.sources || []);
const isCareerPlanningAllowed = computed(() => ["大一", "大二"].includes(careerForm.grade.trim()));
const careerPlanningBlockedReason = computed(() => "职业规划当前只对大一、大二开放，请把主要精力放在岗位诊断、简历优化和投递准备。");
const profileSkillKeywords = [
  "Vue",
  "React",
  "TypeScript",
  "JavaScript",
  "Python",
  "Java",
  "FastAPI",
  "Node.js",
  "Node",
  "SQL",
  "MySQL",
  "PostgreSQL",
  "Docker",
  "Git",
  "数据分析",
  "数据可视化",
  "机器学习",
  "深度学习",
  "产品运营",
  "新媒体运营",
  "用户研究",
  "原型设计",
  "Axure",
  "Figma",
  "项目管理",
  "AIGC",
  "LLM",
];
const profileCityKeywords = [
  "北京",
  "上海",
  "杭州",
  "深圳",
  "广州",
  "成都",
  "南京",
  "武汉",
  "西安",
  "苏州",
];

type CareerProfileDraft = {
  major: string;
  grade: string;
  skills: string;
  direction: string;
  targetCity: string;
  interests: string;
};

function normalizeSectionName(name: string) {
  return name.trim().toLowerCase();
}

function findSectionText(sections: Section[], matchers: string[]) {
  return sections
    .filter((section) => matchers.some((matcher) => normalizeSectionName(section.name).includes(matcher)))
    .map((section) => section.content || "")
    .join("\n");
}

function inferMajor(text: string) {
  const matches = [
    text.match(/([\u4e00-\u9fa5A-Za-z]{2,20}专业)/),
    text.match(/专业[：:\s]*([\u4e00-\u9fa5A-Za-z]{2,20})/),
    text.match(/([\u4e00-\u9fa5A-Za-z]{2,20}(?:工程|科学|技术|管理|设计|经济学|法学|文学|医学|教育))/),
  ];
  return matches.map((item) => item?.[1] || "").find(Boolean) || "";
}

function inferGrade(educationText: string) {
  const startYearMatch = educationText.match(/(20\d{2})[.\-/年]/);
  if (!startYearMatch) return "";
  const startYear = Number(startYearMatch[1]);
  if (!Number.isFinite(startYear)) return "";

  const now = new Date();
  const currentYear = now.getFullYear();
  const schoolYearOffset = now.getMonth() >= 7 ? 1 : 0;
  const gradeIndex = Math.max(1, currentYear - startYear + schoolYearOffset);
  const isMaster = /硕士|研究生|mba/i.test(educationText);
  const labels = isMaster ? ["研一", "研二", "研三"] : ["大一", "大二", "大三", "大四"];
  return labels[Math.min(gradeIndex, labels.length) - 1] || "";
}

function collectSkillTokens(text: string) {
  const found = profileSkillKeywords.filter((keyword) => new RegExp(keyword.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "i").test(text));
  if (/课程项目|项目经历/.test(text)) found.push("课程项目");
  if (/实习|工作经历/.test(text)) found.push("实习经历");
  if (/校园|社团|学生会/.test(text)) found.push("校园经历");
  return Array.from(new Set(found));
}

function inferDirection(text: string) {
  if (/Vue|React|前端|JavaScript|TypeScript/i.test(text)) return "前端开发实习";
  if (/Python|Java|FastAPI|后端|服务端|数据库/i.test(text)) return "后端开发实习";
  if (/数据分析|可视化|SQL|BI|爬虫/i.test(text)) return "数据分析实习";
  if (/产品|原型|需求|用户研究/i.test(text)) return "产品实习";
  if (/运营|新媒体|增长|内容/i.test(text)) return "运营实习";
  if (/AI|AIGC|LLM|机器学习|深度学习/i.test(text)) return "AI 应用实习";
  return "";
}

function inferTargetCity(text: string) {
  return profileCityKeywords.find((city) => text.includes(city)) || "";
}

function extractCareerProfileFromSections(sections: Section[]): CareerProfileDraft {
  const basicsText = findSectionText(sections, ["基本", "个人", "信息"]);
  const educationText = findSectionText(sections, ["教育"]);
  const projectText = findSectionText(sections, ["项目"]);
  const internshipText = findSectionText(sections, ["实习", "工作", "经历"]);
  const skillText = findSectionText(sections, ["技能", "技术", "skill"]);
  const allText = [basicsText, educationText, projectText, internshipText, skillText].filter(Boolean).join("\n");
  const skillTokens = collectSkillTokens(allText);
  const direction = inferDirection(allText);

  return {
    major: inferMajor(educationText || allText),
    grade: inferGrade(educationText),
    skills: skillTokens.join("、"),
    direction,
    targetCity: inferTargetCity(basicsText || allText),
    interests: Array.from(new Set([direction.replace(/实习$/, ""), ...skillTokens.filter((item) => item.length <= 12)])).filter(Boolean).slice(0, 4).join("、"),
  };
}

function mergeCareerForm(profile: CareerProfileDraft) {
  if (profile.major) careerForm.major = profile.major;
  if (profile.grade) careerForm.grade = profile.grade;
  if (profile.skills) careerForm.skills = profile.skills;
  if (profile.direction) careerForm.direction = profile.direction;
  if (profile.targetCity) careerForm.targetCity = profile.targetCity;
  if (profile.interests) careerForm.interests = profile.interests;
}

function logUiEvent(action: string, detail?: Record<string, unknown>) {
  if (!import.meta.env.DEV) return;
  console.info(`[ui] ${action}`, detail || {});
}

async function autofillCareerFormFromResume() {
  logUiEvent("career-autofill:click", { hasUpload: selectedFiles.value.length > 0 || Boolean(selectedCandidate.value) });
  careerAutofillLoading.value = true;
  careerAutofillMessage.value = "";
  currentPage.value = "planning";

  try {
    const candidate = await ensureSelectedCandidateReady();
    const profile = extractCareerProfileFromSections(candidate.sections);
    mergeCareerForm(profile);

    const filledCount = Object.values(profile).filter(Boolean).length;
    careerAutofillMessage.value = filledCount
      ? "已根据已上传简历自动回填表单，你可以在提交前再微调。"
      : "已完成简历解析，但暂时没识别出足够多的背景信息，建议你补充或微调。";
  } catch (err: any) {
    careerAutofillMessage.value = "";
    careerPlanIssue.value = createFlowIssue(err, "简历回填", "无法从当前简历自动填写，请先检查简历上传和解析是否正常。");
  } finally {
    careerAutofillLoading.value = false;
  }
}

async function fillDemo() {
  logUiEvent("fill-demo:click");
  currentPage.value = "planning";
  careerAutofillMessage.value = "";
  careerForm.major = "软件工程";
  careerForm.grade = "大三";
  careerForm.skills = "Vue、TypeScript、Python、课程项目、校园官网、数据可视化";
  careerForm.direction = "前端开发实习";
  careerForm.targetCity = "杭州";
  careerForm.interests = "Web 开发、数据可视化、AI 应用";
  careerPlanMessage.value = "示例数据已填充，正在生成职业行动计划。";
  void generateCareerPlan();
}

async function generateCareerPlan() {
  logUiEvent("career-plan:click", { hasMajor: Boolean(careerForm.major.trim()), hasSkills: Boolean(careerForm.skills.trim()) });
  if (!isCareerPlanningAllowed.value) {
    careerPlanIssue.value = {
      stage: "职业规划",
      message: careerPlanningBlockedReason.value,
      retryable: false,
    };
    careerPlanMessage.value = careerPlanningBlockedReason.value;
    return;
  }
  careerPlanLoading.value = true;
  careerPlanIssue.value = null;
  careerPlanMessage.value = "正在生成职业方向、行动计划和作品集建议...";
  try {
    const data = await requestCareerPlan({
      major: careerForm.major.trim(),
      grade: careerForm.grade.trim(),
      skills: splitTokens(careerForm.skills),
      experience: careerForm.skills.trim(),
      targetCity: careerForm.targetCity.trim(),
      interests: splitTokens(careerForm.interests || careerForm.direction),
    });
    careerPlan.roles = data.recommendedDirections.map((item) => ({
      title: item.direction,
      reason: item.reason,
      fit: clamp(item.score),
    }));
    careerPlan.actions = data.learningRoadmap.flatMap((item) => [
      `${item.stage}：${item.tasks.join("；")}`,
      `预期结果：${item.outcome}`,
    ]);
    careerPlan.portfolioSuggestions = data.portfolioSuggestions || [];
    careerPlan.riskWarnings = data.riskWarnings || [];
    careerPlan.cityAdvice = data.cityAdvice || "";
    careerPlanMessage.value = "职业行动计划已生成，可以继续查看推荐方向和行动步骤。";
  } catch (err: any) {
    careerPlanIssue.value = createFlowIssue(err, "职业规划", "职业规划生成失败，请稍后重试。");
    applyCareerPlanFallback();
    careerPlanMessage.value = "职业规划接口失败，已展示前端兜底建议，方便继续演示。";
  } finally {
    careerPlanLoading.value = false;
  }
}

async function extractJob() {
  if (!jobForm.responsibilities.trim()) return;
  extractingJob.value = true;
  extractionMessage.value = "";
  try {
    const extracted = await extractJobProfile(jobForm.responsibilities);
    jobForm.title = extracted.title || jobForm.title;
    jobForm.responsibilities = extracted.responsibilities || jobForm.responsibilities;
    mustHaveText.value = extracted.must_haves.join("\n") || mustHaveText.value;
    niceHaveText.value = extracted.nice_to_haves.join("\n") || niceHaveText.value;
    keywordText.value = extracted.keywords.join(", ") || keywordText.value;
    jobForm.experience_years = extracted.experience_years || jobForm.experience_years;
    extractionMessage.value = "已解析 JD，可继续手动调整。";
  } catch (err: any) {
    extractionMessage.value = err?.message || "JD 解析失败，可手动填写。";
  } finally {
    extractingJob.value = false;
  }
}

function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement;
  acceptFiles(Array.from(input.files || []));
  input.value = "";
}

function onDrop(event: DragEvent) {
  isDragging.value = false;
  acceptFiles(Array.from(event.dataTransfer?.files || []));
}

function openFilePicker() {
  fileInputRef.value?.click();
}

function acceptFiles(files: File[]) {
  fileFeedback.value = [];
  const valid: File[] = [];
  for (const file of files) {
    if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
      fileFeedback.value.push(`${file.name}: 仅支持 PDF 文件。`);
      continue;
    }
    if (file.size > 20 * 1024 * 1024) {
      fileFeedback.value.push(`${file.name}: 文件过大，单份不能超过 20MB。`);
      continue;
    }
    valid.push(file);
  }
  selectedFiles.value = valid;
  candidates.value = [];
  selectedLocalId.value = null;
  diagnosisIssue.value = null;
  optimizeIssue.value = null;
  optimizationResult.value = null;
  optimizeStage.value = "idle";
  optimizationVersion.value = 0;
  templateSyncedOptimizationVersion.value = 0;
  templateStructuredResume.value = null;
  templateError.value = "";
  templateMessage.value = "优化完成后，可一键进入模板页生成完整排版简历。";
}

function resetDiagnosis() {
  logUiEvent("diagnosis:reset");
  processing.value = false;
  diagnosisIssue.value = null;
  selectedFiles.value = [];
  fileFeedback.value = [];
  candidates.value = [];
  selectedLocalId.value = null;
}

async function processQueue() {
  logUiEvent("diagnosis:click", { fileCount: selectedFiles.value.length });
  if (!canRunDiagnosis.value) return;
  processing.value = true;
  diagnosisIssue.value = null;
  applicationStrategy.value = null;
  interviewPrep.value = null;
  candidates.value = selectedFiles.value.map(createCandidate);
  selectedLocalId.value = candidates.value[0]?.localId ?? null;

  try {
    for (const candidate of candidates.value) {
      selectedLocalId.value = candidate.localId;
      try {
        setCandidatePhase(candidate, "uploading", 15);
        await parseCandidate(candidate);
        setCandidatePhase(candidate, "matching", 75);
        const match = await matchResume(candidate.resumeId as number, currentJob());
        applyMatch(candidate, match);
        setCandidatePhase(candidate, "done", 100);
      } catch (err: any) {
        applyDiagnosisError(candidate, err);
        diagnosisIssue.value = {
          stage: candidate.errorStage || "诊断流程",
          message: candidate.error,
          retryable: candidate.retryable,
        };
      }
    }
  } finally {
    processing.value = false;
  }
}

async function optimizeSelectedResume() {
  logUiEvent("optimize:click", {
    fileCount: selectedFiles.value.length,
    hasJobTitle: Boolean(jobForm.title.trim()),
    hasJobDescription: Boolean(jobForm.responsibilities.trim()),
  });
  optimizeIssue.value = null;
  if (!selectedFiles.value.length) {
    optimizeIssue.value = { stage: "简历解析", message: "缺少简历文件，请先上传简历。", retryable: false };
    return;
  }
  if (!jobForm.title.trim() || !jobForm.responsibilities.trim()) {
    optimizeIssue.value = { stage: "岗位信息", message: "缺少岗位名称或岗位 JD，请先补全岗位信息。", retryable: false };
    return;
  }
  if (!canOptimize.value) return;
  optimizing.value = true;
  optimizeStage.value = "validating";
  currentPage.value = "optimize";
  try {
    const candidate = await ensureSelectedCandidateReady();
    optimizeStage.value = "reading";
    optimizeStage.value = "generating";
    optimizationResult.value = await optimizeResumeForJob(candidate.resumeId as number, currentJob(), selectedModel.value);
    optimizationVersion.value += 1;
    optimizeStage.value = "done";
    optimizeIssue.value = null;
    templateError.value = "";
    templateMessage.value = optimizationResult.value.isFallback
      ? "本次仅拿到兜底建议。你仍可继续排版和导出，但建议稍后重试 AI 润色。"
      : "优化结果已生成，可一键进入模板排版。";
  } catch (err: any) {
    optimizeStage.value = "failed";
    optimizeIssue.value = createFlowIssue(err, "简历优化", "岗位定制简历生成失败，请稍后重试。");
  } finally {
    optimizing.value = false;
  }
}

async function openOptimizeEntry() {
  logUiEvent("optimize-entry:click", {
    fileCount: selectedFiles.value.length,
    hasJobTitle: Boolean(jobForm.title.trim()),
    hasJobDescription: Boolean(jobForm.responsibilities.trim()),
    hasOptimization: Boolean(optimizationResult.value),
  });
  currentPage.value = "optimize";
  optimizeIssue.value = null;

  if (!jobForm.title.trim() || !jobForm.responsibilities.trim()) {
    optimizeIssue.value = { stage: "岗位信息", message: "请先补全岗位名称和岗位 JD，再运行简历优化。", retryable: false };
    return;
  }

  if (!selectedFiles.value.length) {
    optimizeIssue.value = { stage: "简历解析", message: "请先上传 PDF 简历，再进行岗位定制简历优化。", retryable: false };
    return;
  }

  if (optimizing.value || (optimizationResult.value && optimizeStage.value === "done")) {
    return;
  }

  await optimizeSelectedResume();
}

function openTemplateEntry() {
  if (!optimizationResult.value) {
    currentPage.value = "optimize";
    templateError.value = "";
    templateMessage.value = "请先完成简历优化，再生成排版简历。";
    return;
  }
  currentPage.value = "template";
  if ((!templateStructuredResume.value || templateNeedsSync.value) && !templateStructureLoading.value) {
    void generateTemplateResume();
  }
}

async function parseCandidate(candidate: Candidate) {
  if (candidate.resumeId) return;
  if (!candidate.file) throw new Error("请先上传简历。");
  setCandidatePhase(candidate, "parsing", 45);
  const ocr = await ocrResume(candidate.file);
  candidate.resumeId = ocr.resumeId;
  candidate.sections = Array.isArray(ocr.sections) ? (ocr.sections as Section[]) : [];
}

function createCandidate(file: File): Candidate {
  return {
    localId: nextLocalId++,
    file,
    displayName: file.name.replace(/\.pdf$/i, ""),
    status: "queued",
    phase: "idle",
    phaseLabel: "等待开始",
    progress: 10,
    resumeId: null,
    sections: [],
    metrics: { total: 0, skill: 0, experience: 0, project: 0 },
    summary: "",
    skillMatches: [],
    experienceSupport: [],
    gaps: [],
    questions: [],
    matchResult: null,
    error: "",
    errorStage: "",
    errorAction: "",
    retryable: true,
    requestEndpoint: "",
    lastUpdatedAt: null,
  };
}

function applyMatch(candidate: Candidate, match: MatchResponse) {
  const result = match.result;
  const hits = result.must_have_hits || [];
  const hitCount = hits.filter((hit) => /命中|hit|matched/i.test(hit.status)).length;
  const partialCount = hits.filter((hit) => /部分|partial/i.test(hit.status)).length;
  const skill = hits.length ? Math.round(((hitCount + partialCount * 0.5) / hits.length) * 100) : match.match_score;
  candidate.metrics = {
    total: clamp(match.match_score),
    skill: clamp(skill),
    experience: clamp(match.match_score * 0.82 + (result.strengths?.length || 0) * 4 - (result.gaps?.length || 0) * 3),
    project: clamp(match.match_score * 0.88 + (result.evidence?.length || 0) * 3),
  };
  candidate.summary = result.match_reason || result.next_step || "你和岗位有一定匹配，但需要结合缺口决定是否投递。";
  candidate.skillMatches = result.skill_matches || hits.map((hit) => `${hit.requirement}: ${hit.evidence}`).filter(Boolean);
  candidate.experienceSupport = result.experience_support || result.evidence || [];
  candidate.gaps = result.gaps || [];
  candidate.questions = normalizeQuestions(result.interview_questions || [], candidate.gaps);
  candidate.matchResult = result;
}

function setCandidatePhase(candidate: Candidate, phase: DiagnosisPhase, progress: number) {
  candidate.phase = phase;
  candidate.phaseLabel = phaseLabelMap(phase);
  candidate.progress = progress;
  candidate.status = phase === "idle" ? "queued" : phase === "error" ? "error" : phase;
  candidate.lastUpdatedAt = Date.now();
  if (phase !== "error") {
    candidate.error = "";
    candidate.errorStage = "";
    candidate.errorAction = "";
    candidate.requestEndpoint = "";
  }
}

function phaseLabelMap(phase: DiagnosisPhase) {
  switch (phase) {
    case "uploading":
      return "上传中";
    case "parsing":
      return "简历解析中";
    case "matching":
      return "岗位匹配中";
    case "done":
      return "完成";
    case "error":
      return "失败";
    default:
      return "等待开始";
  }
}

function optimizeStageLabel(stage: OptimizeStage) {
  switch (stage) {
    case "validating":
      return "检查岗位与简历";
    case "reading":
      return "读取简历解析结果";
    case "generating":
      return "生成岗位定制简历";
    case "done":
      return "优化完成";
    case "failed":
      return "优化失败";
    default:
      return "等待开始";
  }
}

function applyDiagnosisError(candidate: Candidate, err: unknown) {
  const fallback = "诊断失败，请稍后重试。";
  const previousPhase = candidate.phase;
  setCandidatePhase(candidate, "error", candidate.progress || 0);
  candidate.error = err instanceof Error ? err.message : fallback;
  candidate.retryable = true;

  if (err instanceof ApiRequestError) {
    candidate.errorStage = err.stage || (previousPhase === "parsing" ? "简历解析" : "岗位匹配");
    candidate.requestEndpoint = err.endpoint;
    candidate.retryable = err.retryable;

    if (err.isTimeout) {
      candidate.errorAction = previousPhase === "parsing"
        ? "这通常是解析耗时过长，不代表 PDF 一定损坏。建议先重新诊断一次；若仍超时，再更换更清晰的 PDF 或检查后端模型服务。"
        : "这通常是岗位匹配耗时过长。建议重新诊断一次；若仍超时，请稍后再试或检查后端模型服务。";
      return;
    }

    candidate.errorAction = previousPhase === "parsing"
      ? "请先确认后端服务正常，再重新诊断；如果同一份 PDF 持续失败，建议换一份可复制文本的 PDF。"
      : "请检查后端服务和岗位信息后重新诊断。";
    return;
  }

  candidate.errorStage = previousPhase === "parsing" ? "简历解析" : "岗位匹配";
  candidate.errorAction = "可以重新诊断；如果问题持续，建议重新上传简历后再试。";
}

function createFlowIssue(err: unknown, stage: string, fallbackMessage: string): FlowIssue {
  if (err instanceof ApiRequestError) {
    return {
      stage: err.stage || stage,
      message: err.message || fallbackMessage,
      retryable: true,
    };
  }

  if (err instanceof Error) {
    return {
      stage,
      message: err.message || fallbackMessage,
      retryable: true,
    };
  }

  return {
    stage,
    message: fallbackMessage,
    retryable: true,
  };
}

function applyCareerPlanFallback() {
  const direction = careerForm.direction.trim() || "前端开发实习";
  const major = careerForm.major.trim() || "当前专业";
  const targetCity = careerForm.targetCity.trim() || "目标城市";
  const skills = splitTokens(careerForm.skills);
  const highlightedSkill = skills[0] || "项目经验";

  careerPlan.roles = [
    {
      title: direction,
      reason: `你的 ${major} 背景中，${highlightedSkill} 能力和该方向最接近，适合作为优先尝试岗位。`,
      fit: 78,
    },
    {
      title: "产品化前端 / 数据可视化",
      reason: "如果你希望提高作品集展示力，这个方向更容易形成可演示成果。",
      fit: 68,
    },
  ];
  careerPlan.actions = [
    `第 1 周：围绕 ${direction} 补齐 1 个最能体现能力的项目说明。`,
    `第 2 周：根据目标岗位 JD 提炼 6 到 10 个关键词，补强到简历前半屏。`,
    `第 3 周：针对 ${targetCity} 的目标公司，整理一份投递清单并准备自我介绍。`,
  ];
  careerPlan.portfolioSuggestions = [
    "准备一个可直接打开演示的项目链接或截图。",
    "补一页项目复盘，说明你的职责、动作和结果。",
  ];
  careerPlan.riskWarnings = [
    "如果简历里只有技术栈没有结果，面试时会很难证明价值。",
    "如果目标方向过宽，建议先锁定一类岗位做定向投递。",
  ];
  careerPlan.cityAdvice = `${targetCity} 方向建议优先关注校招、实习转正和中小团队的多面手岗位。`;
}

function normalizeQuestions(items: MatchResponse["result"]["interview_questions"], gaps: string[]) {
  const source = items.length ? items : gaps.map((gap) => `请结合项目说明你如何补齐：${gap}`);
  return source.slice(0, 6).map((item, index) => {
    if (typeof item === "string") {
      return { category: index % 2 ? "简历追问" : "岗位相关问题", difficulty: index > 3 ? "困难" : index > 1 ? "中等" : "简单", question: item };
    }
    return { category: item.category, difficulty: item.difficulty, question: item.question };
  });
}

function currentJob(): JobProfile {
  return {
    title: jobForm.title.trim(),
    responsibilities: jobForm.responsibilities.trim(),
    must_haves: splitLines(mustHaveText.value),
    nice_to_haves: splitLines(niceHaveText.value),
    experience_years: jobForm.experience_years,
    keywords: keywordText.value.split(/[,，\n]/).map((item) => item.trim()).filter(Boolean),
  };
}

function createEmptyStructuredResume(): StructuredResume {
  return {
    basics: {
      name: "",
      title: "",
      phone: "",
      email: "",
      location: "",
      summary: "",
      website: "",
      github: "",
      media: "",
      photo: "",
      links: [],
    },
    targetRole: "",
    education: [],
    experiences: [],
    projects: [],
    skills: [],
    certificates: [],
    awards: [],
    selfEvaluation: "",
    metadata: {},
  };
}

function normalizeTemplatePreset(template: ResumeTemplateSummary): TemplatePreset {
  const normalizedLayout = template.layout === "cn-campus-double"
    ? "cn-campus-double"
    : "cn-campus-single";
  return {
    id: template.id,
    name: template.name,
    scene: template.scene || template.suitableRoles?.join(" / ") || "通用场景",
    tone: template.tone || "正式、可投递、结构清晰",
    accent: template.accent || "#2f6f73",
    layout: normalizedLayout,
    styleVariant: template.styleVariant || (normalizedLayout === "cn-campus-double" ? "double" : "clean"),
    suitableRoles: template.suitableRoles || [],
    source: template.source || "本地迁入自 4173 模板工作台",
    sourceUrl: template.sourceUrl || `internal://resume-templates/${template.id}`,
    license: template.license || "项目演示与课程竞赛可用；商业分发前建议替换为自有设计资产",
  };
}

function createWorkspaceId(prefix: string) {
  return `${prefix}-${Math.random().toString(36).slice(2, 10)}`;
}

function createWorkspaceEntry(prefix: string): TemplateWorkspaceEntry {
  return {
    id: createWorkspaceId(prefix),
    title: "",
    organization: "",
    role: "",
    start: "",
    end: "",
    details: "",
    coursework: "",
  };
}

function createWorkspaceCertificate(): TemplateWorkspaceCertificate {
  return {
    id: createWorkspaceId("certificate"),
    name: "",
    issuer: "",
    date: "",
  };
}

function createWorkspaceCustom(): TemplateWorkspaceCustomSection {
  return {
    id: createWorkspaceId("custom"),
    title: "",
    details: "",
  };
}

function hasWorkspaceEntryContent(entry: TemplateWorkspaceEntry) {
  return Boolean(entry.title.trim() || entry.organization.trim() || entry.role.trim() || entry.start.trim() || entry.end.trim() || entry.details.trim());
}

function entryPeriod(entry: TemplateWorkspaceEntry) {
  return [entry.start.trim(), entry.end.trim()].filter(Boolean).join(" - ");
}

function renderWorkspaceHeadline(entry: TemplateWorkspaceEntry) {
  return [entry.title.trim(), entry.organization.trim(), entry.role.trim()].filter(Boolean).join("    ");
}

function renderCertificateTitle(entry: TemplateWorkspaceCertificate) {
  return [entry.name.trim(), entry.issuer.trim()].filter(Boolean).join(" / ");
}

function renderDetailsLines(value: string) {
  return value.split("\n").map((line) => line.trim()).filter(Boolean);
}

function structuredEntryToWorkspaceEntry(entry: StructuredResumeEntry, prefix: string): TemplateWorkspaceEntry {
  const [start = "", end = ""] = entry.period.split(/\s*-\s*/);
  return {
    id: createWorkspaceId(prefix),
    title: entry.title || "",
    organization: entry.organization || "",
    role: entry.role || "",
    start: start.trim(),
    end: end.trim(),
    details: entry.bullets.join("\n"),
    coursework: (entry.coursework || []).join("、"),
  };
}

function workspaceEntryToStructuredEntry(entry: TemplateWorkspaceEntry): StructuredResumeEntry {
  return {
    title: entry.title.trim(),
    organization: entry.organization.trim(),
    role: entry.role.trim(),
    period: entryPeriod(entry),
    bullets: renderDetailsLines(entry.details),
    coursework: renderDetailsLines((entry.coursework || "").replace(/[、；]/g, "\n")),
  };
}

function structuredResumeToWorkspace(data: StructuredResume): TemplateWorkspaceData {
  const metadataCustomSections = Array.isArray((data.metadata as { customSections?: unknown[] } | undefined)?.customSections)
    ? ((data.metadata as { customSections?: unknown[] }).customSections || [])
        .map((item) => {
          const section = item && typeof item === "object" ? item as Record<string, unknown> : {};
          return {
            id: createWorkspaceId("custom"),
            title: String(section.title || ""),
            details: String(section.details || section.content || ""),
          };
        })
        .filter((item) => item.title.trim() || item.details.trim())
    : [];
  return {
    profile: {
      name: data.basics.name || "",
      title: data.basics.title || "",
      phone: data.basics.phone || "",
      email: data.basics.email || "",
      city: data.basics.location || "",
      website: data.basics.website || data.basics.links?.[0] || "",
      github: data.basics.github || "",
      media: data.basics.media || "",
      photo: data.basics.photo || "",
      target: data.targetRole || data.basics.title || "",
      summary: data.basics.summary || "",
    },
    education: data.education.map((entry) => structuredEntryToWorkspaceEntry(entry, "education")),
    experience: data.experiences.map((entry) => structuredEntryToWorkspaceEntry(entry, "experience")),
    projects: data.projects.map((entry) => structuredEntryToWorkspaceEntry(entry, "project")),
    skills: data.skills.flatMap((group) => group.items).filter(Boolean),
    certificates: [...data.certificates, ...data.awards].map((value) => ({
      id: createWorkspaceId("certificate"),
      name: value,
      issuer: "",
      date: "",
    })),
    custom: [
      ...metadataCustomSections,
      ...(data.selfEvaluation
        ? [{ id: createWorkspaceId("custom"), title: "补充说明", details: data.selfEvaluation }]
        : []),
    ],
  };
}

function workspaceToStructuredResume(): StructuredResume {
  const current = templateStructuredResume.value || createEmptyStructuredResume();
  const customSections = templateWorkspace.custom.filter((item) => item.title.trim() || item.details.trim());
  const supplementalNote = customSections.find((item) => item.title.trim() === "补充说明");
  return {
    ...current,
    basics: {
      ...current.basics,
      name: templateWorkspace.profile.name.trim(),
      title: templateWorkspace.profile.title.trim(),
      phone: templateWorkspace.profile.phone.trim(),
      email: templateWorkspace.profile.email.trim(),
      location: templateWorkspace.profile.city.trim(),
      summary: templateWorkspace.profile.summary.trim(),
      website: templateWorkspace.profile.website.trim(),
      github: templateWorkspace.profile.github.trim(),
      media: templateWorkspace.profile.media.trim(),
      photo: templateWorkspace.profile.photo.trim(),
      links: [
        templateWorkspace.profile.website.trim(),
        templateWorkspace.profile.github.trim(),
        templateWorkspace.profile.media.trim(),
      ].filter(Boolean),
    },
    targetRole: templateWorkspace.profile.target.trim(),
    education: templateWorkspace.education.filter(hasWorkspaceEntryContent).map(workspaceEntryToStructuredEntry),
    experiences: templateWorkspace.experience.filter(hasWorkspaceEntryContent).map(workspaceEntryToStructuredEntry),
    projects: templateWorkspace.projects.filter(hasWorkspaceEntryContent).map(workspaceEntryToStructuredEntry),
    skills: templateWorkspace.skills.filter(Boolean).length ? [{ category: "技能", items: templateWorkspace.skills.filter(Boolean) }] as StructuredResumeSkillGroup[] : [],
    certificates: templateWorkspace.certificates
      .filter((item) => item.name.trim() || item.issuer.trim() || item.date.trim())
      .map((item) => [item.name.trim(), item.issuer.trim(), item.date.trim()].filter(Boolean).join(" / ")),
    awards: [],
    selfEvaluation: supplementalNote?.details.trim() || "",
    metadata: {
      ...(current.metadata || {}),
      sourceLabel: templateSource.value,
      lastEditedAt: new Date().toISOString(),
      customSections: customSections
        .filter((item) => item.title.trim() !== "补充说明")
        .map((item) => ({ title: item.title.trim(), details: item.details.trim() })),
    },
  };
}

function applyStructuredResumeToWorkspace(data: StructuredResume, source: string) {
  const normalized = createEmptyTemplateWorkspaceData();
  const next = structuredResumeToWorkspace(data);
  isApplyingTemplateWorkspace.value = true;
  templateSource.value = source;
  templateStructuredResume.value = data;
  normalized.profile = next.profile;
  normalized.education = next.education;
  normalized.experience = next.experience;
  normalized.projects = next.projects;
  normalized.skills = next.skills;
  normalized.certificates = next.certificates;
  normalized.custom = next.custom;
  Object.assign(templateWorkspace, normalized);
  if (!templateWorkspace.education.length) templateWorkspace.education.push(createWorkspaceEntry("education"));
  if (!templateWorkspace.experience.length) templateWorkspace.experience.push(createWorkspaceEntry("experience"));
  if (!templateWorkspace.projects.length) templateWorkspace.projects.push(createWorkspaceEntry("project"));
  if (!templateWorkspace.certificates.length) templateWorkspace.certificates.push(createWorkspaceCertificate());
  if (!templateWorkspace.custom.length) templateWorkspace.custom.push(createWorkspaceCustom());
  templateStyle.themeColor = selectedTemplate.value.accent;
  isApplyingTemplateWorkspace.value = false;
}

const templateStyleVars = computed<Record<string, string | number>>(() => ({
  "--accent": templateStyle.themeColor || selectedTemplate.value.accent,
  "--resume-font-family": templateStyle.fontFamily,
  "--resume-line-height": templateStyle.lineHeight,
  "--resume-base-size": `${templateStyle.baseFontSize}px`,
  "--resume-section-title-size": `${templateStyle.sectionTitleSize}px`,
  "--resume-name-size": `${templateStyle.nameSize}px`,
  "--resume-page-padding": `${templateStyle.pagePadding}mm`,
  "--resume-section-gap": `${templateStyle.sectionGap}px`,
  "--resume-entry-gap": `${templateStyle.entryGap}px`,
}));

function addWorkspaceEntry(kind: "education" | "experience" | "projects") {
  templateWorkspace[kind].push(createWorkspaceEntry(kind));
}

function removeWorkspaceEntry(kind: "education" | "experience" | "projects", id: string) {
  templateWorkspace[kind] = templateWorkspace[kind].filter((item) => item.id !== id);
  if (!templateWorkspace[kind].length) {
    templateWorkspace[kind].push(createWorkspaceEntry(kind));
  }
}

function addWorkspaceCertificate() {
  templateWorkspace.certificates.push(createWorkspaceCertificate());
}

function removeWorkspaceCertificate(id: string) {
  templateWorkspace.certificates = templateWorkspace.certificates.filter((item) => item.id !== id);
  if (!templateWorkspace.certificates.length) {
    templateWorkspace.certificates.push(createWorkspaceCertificate());
  }
}

function addWorkspaceCustom() {
  templateWorkspace.custom.push(createWorkspaceCustom());
}

function removeWorkspaceCustom(id: string) {
  templateWorkspace.custom = templateWorkspace.custom.filter((item) => item.id !== id);
  if (!templateWorkspace.custom.length) {
    templateWorkspace.custom.push(createWorkspaceCustom());
  }
}

function updateWorkspaceSkills(value: string) {
  templateWorkspace.skills = value.split("\n").map((item) => item.trim()).filter(Boolean);
}

function handleWorkspaceSkillInput(event: Event) {
  updateWorkspaceSkills((event.target as HTMLTextAreaElement).value);
}

async function loadResumeTemplateOptions() {
  try {
    const templates = await getResumeTemplates();
    if (templates.length) {
      resumeTemplates.value = templates.map(normalizeTemplatePreset);
      if (!templates.some((item) => item.id === selectedTemplateId.value)) {
        selectedTemplateId.value = templates[0].id;
      }
    }
  } catch {
    resumeTemplates.value = fallbackResumeTemplates;
  }
}

function currentStructuredResumeSource() {
  if (templateStructuredResume.value && !templateNeedsSync.value) {
    return templateStructuredResume.value;
  }
  if (optimizationResult.value?.optimizedStructure) return optimizationResult.value.optimizedStructure;
  if (optimizationResult.value?.structuredResume) return optimizationResult.value.structuredResume;
  return null;
}

function currentResumeContextPayload(candidate?: Candidate | null): ResumeContextPayload {
  const structuredResume = currentStructuredResumeSource() || undefined;
  const optimizedText = optimizationResult.value?.modules
    ?.map((item) => item.optimizedContent.trim())
    .filter(Boolean)
    .join("\n\n");

  return {
    rawResumeText: optimizedText || undefined,
    sections: candidate?.sections?.length ? candidate.sections : undefined,
    structuredResume,
  };
}

async function generateTemplateResume() {
  if (!optimizationResult.value) {
    templateError.value = "请先完成简历优化，再生成排版简历。";
    currentPage.value = "optimize";
    return;
  }

  templateStructureLoading.value = true;
  templateError.value = "";
  templateMessage.value = "正在整合优化结果并生成可排版的简历内容...";

  try {
    await loadResumeTemplateOptions();
    const structureSource = currentStructuredResumeSource()
      || ((optimizationResult.value.rawResult as Record<string, unknown>) || { optimizedResume: optimizationResult.value });
    const structuredPayload = await structureResumeData(structureSource as Record<string, unknown>);
    applyStructuredResumeToWorkspace(structuredPayload.structuredResume, "优化结果");
    templateSyncedOptimizationVersion.value = optimizationVersion.value;
    if (structuredPayload.completeness !== "complete" || structuredPayload.warnings.length || structuredPayload.missingFields.length) {
      const tips = [
        optimizationResult.value.isFallback ? "当前展示的是保守兜底结果" : "",
        structuredPayload.missingFields.length ? `仍待补充：${structuredPayload.missingFields.join("、")}` : "",
      ].filter(Boolean).join("；");
      templateMessage.value = `排版简历已生成，但还有信息需要你再确认。${tips}`;
    } else {
      templateMessage.value = "排版简历已生成，可继续微调内容后导出 PDF。";
    }
    currentPage.value = "template";
  } catch (err: any) {
    templateError.value = err?.message || "排版简历生成失败，请稍后重试。";
    templateMessage.value = "排版简历暂未生成。";
  } finally {
    templateStructureLoading.value = false;
  }
}
watch(
  templateWorkspace,
  () => {
    if (isApplyingTemplateWorkspace.value || !templateStructuredResume.value) return;
    templateStructuredResume.value = workspaceToStructuredResume();
  },
  { deep: true },
);

watch(selectedTemplateId, () => {
  if (!selectedTemplate.value) return;
  if (!templateStyle.themeColor || templateThemePresets.some((item) => item.color === templateStyle.themeColor)) {
    templateStyle.themeColor = selectedTemplate.value.accent;
  }
});

onMounted(() => {
  void loadResumeTemplateOptions();
});

async function loadAnalytics() {
  analyticsLoading.value = true;
  analyticsError.value = "";
  try {
    const data = await getRecruitmentAnalytics("operator");
    analyticsData.value = data;
    if (!data.sources?.length) {
      analyticsError.value = "暂无带来源的数据，页面不会展示无来源 mock 数据。";
    }
  } catch (err: any) {
    analyticsData.value = null;
    analyticsError.value = err?.message || "数据加载失败。";
  } finally {
    analyticsLoading.value = false;
  }
}

async function generateDeliveryStrategy() {
  deliveryLoading.value = true;
  deliveryError.value = "";
  try {
    const candidate = await ensureSelectedCandidateReady(true);
    const resumeContext = currentResumeContextPayload(candidate);
    applicationStrategy.value = await generateApplicationStrategy({
      studentProfile: currentStudentProfile(),
      jobDescription: currentJob().responsibilities,
      jobRequirements: currentJob(),
      matchResult: candidate.matchResult || {},
      resumeId: candidate.resumeId || undefined,
      rawResumeText: resumeContext.rawResumeText,
      sections: resumeContext.sections,
      structuredResume: resumeContext.structuredResume,
    });
  } catch (err: any) {
    deliveryError.value = err?.message || "投递策略生成失败。";
  } finally {
    deliveryLoading.value = false;
  }
}

async function generateInterviewPlan() {
  interviewLoading.value = true;
  interviewError.value = "";
  try {
    const candidate = await ensureSelectedCandidateReady(true);
    const resumeContext = currentResumeContextPayload(candidate);
    interviewPrep.value = await generateInterviewPrepare({
      studentProfile: currentStudentProfile(),
      jobDescription: currentJob().responsibilities,
      jobRequirements: currentJob(),
      matchResult: candidate.matchResult || {},
      resumeId: candidate.resumeId || undefined,
      rawResumeText: resumeContext.rawResumeText,
      sections: resumeContext.sections,
      structuredResume: resumeContext.structuredResume,
    });
  } catch (err: any) {
    interviewError.value = err?.message || "面试准备生成失败。";
  } finally {
    interviewLoading.value = false;
  }
}

watch(currentUserRole, (role) => {
  if (role === "student" && currentPage.value === "analytics") {
    currentPage.value = "dashboard";
  } else if (role !== "student" && currentPage.value !== "analytics") {
    currentPage.value = "analytics";
    void loadAnalytics();
  }
});

function printTemplateResume() {
  if (!templateStructuredResume.value) {
    templateError.value = "当前没有可打印的排版简历，请先生成或补全内容。";
    currentPage.value = "template";
    return;
  }
  window.print();
}

async function exportPdf() {
  if (!templateStructuredResume.value) {
    templateError.value = "当前没有可导出的排版简历，请先生成或补全内容。";
    currentPage.value = "template";
    return;
  }

  templateExporting.value = true;
  templateError.value = "";
  try {
    const blob = await exportResumePdf({
      templateId: selectedTemplateId.value,
      structuredResume: templateStructuredResume.value,
      filename: `${templateWorkspace.profile.name || "resume"}_${selectedTemplateId.value}.pdf`,
    });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${templateWorkspace.profile.name || "resume"}_${selectedTemplateId.value}.pdf`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
    templateMessage.value = "已使用后端结构化数据生成 PDF。";
  } catch (err: any) {
    templateError.value = err?.message || "PDF 导出失败，请稍后重试。";
  } finally {
    templateExporting.value = false;
  }
}

async function ensureSelectedCandidateReady(requireMatch = false) {
  let candidate = selectedCandidate.value;
  if (!candidate) {
    const firstFile = selectedFiles.value[0];
    if (!firstFile) throw new Error("请先上传简历。");
    candidate = createCandidate(firstFile);
    candidates.value = [candidate];
    selectedLocalId.value = candidate.localId;
  }
  await parseCandidate(candidate);
  if (requireMatch && !candidate.matchResult) {
    const match = await matchResume(candidate.resumeId as number, currentJob());
    applyMatch(candidate, match);
  }
  return candidate;
}

function currentStudentProfile() {
  return {
    major: careerForm.major.trim(),
    grade: careerForm.grade.trim(),
    skills: splitTokens(careerForm.skills),
    experience: careerForm.skills.trim(),
    targetCity: careerForm.targetCity.trim(),
    interests: splitTokens(careerForm.interests || careerForm.direction),
  };
}

function splitLines(value: string) {
  return value.split("\n").map((item) => item.trim()).filter(Boolean);
}

function splitTokens(value: string) {
  return value.split(/[、，,\n/]+/).map((item) => item.trim()).filter(Boolean);
}

function applyLabel(score: number) {
  if (!score) return "--";
  if (score >= 85) return "优先投";
  if (score >= 70) return "值得投";
  if (score >= 55) return "淇敼鍚庢姇";
  return "先不投";
}

function formatSize(size: number) {
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

function joinList(items: string[]) {
  return items.filter(Boolean).join("；") || "暂无明确证据";
}

function clamp(value: number) {
  return Math.max(0, Math.min(100, Math.round(value)));
}
</script>

<style scoped>
/* ===== Design Tokens ===== */
.app-shell {
  --color-bg: #f7f5f0;
  --color-surface: #ffffff;
  --color-navy: #0f1a2e;
  --color-navy-light: #1a2d4a;
  --color-terracotta: #c4644a;
  --color-terracotta-light: #e0896e;
  --color-teal: #2d7d7a;
  --color-text-primary: #1a1a1a;
  --color-text-secondary: #6b6560;
  --color-text-muted: #a09890;
  --color-border: #e2ddd6;
  --color-border-hover: #c9c2b8;
  --font-display: 'Bricolage Grotesque', 'PingFang SC', sans-serif;
  --font-body: 'Outfit', 'PingFang SC', 'Noto Sans SC', sans-serif;
}

:deep(*) {
  box-sizing: border-box;
}

.app-shell {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 256px minmax(0, 1fr);
  color: var(--color-text-primary);
  background: var(--color-bg);
  font-family: var(--font-body);
}

.app-shell::before {
  content: '';
  position: fixed;
  inset: 0;
  opacity: 0.3;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E");
  background-repeat: repeat;
  background-size: 256px 256px;
  pointer-events: none;
  z-index: 0;
}

button,
input,
textarea,
select {
  font: inherit;
}

button {
  cursor: pointer;
}

h1,
h2,
h3,
h4,
p {
  margin-top: 0;
}

.sidebar {
  min-height: 100vh;
  height: 100vh;
  position: sticky;
  top: 0;
  padding: 22px 16px;
  background: var(--color-surface);
  box-shadow: 4px 0 20px rgba(15,26,46,0.04);
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
}

.brand > span {
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  border-radius: 12px;
  color: #fff;
  background: var(--color-navy);
  font-weight: 950;
  font-size: 15px;
}

.brand strong,
.brand small {
  display: block;
}

.brand small {
  color: var(--color-text-secondary);
  font-size: 12px;
}

.nav-list {
  display: grid;
  gap: 8px;
}

.nav-list button {
  min-height: 42px;
  display: flex;
  align-items: center;
  gap: 10px;
  border: none;
  border-radius: 16px;
  padding: 0 14px;
  color: var(--color-text-secondary);
  background: transparent;
  text-align: left;
  font-weight: 800;
  transition: background 0.15s ease, color 0.15s ease;
}

.nav-list button:hover {
  background: rgba(196, 100, 74, 0.08);
  color: var(--color-terracotta);
}

.nav-list button span {
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  color: var(--color-terracotta);
  background: rgba(196, 100, 74, 0.1);
  font-size: 12px;
}

.nav-list button.active {
  color: #fff;
  background: var(--color-terracotta);
}

.nav-list button.active span {
  color: #fff;
  background: rgba(255,255,255,0.2);
}

.page-area {
  min-width: 0;
  padding: 28px;
}

.topbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 18px;
}

.eyebrow {
  margin-bottom: 8px;
  color: var(--color-terracotta);
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.topbar h1 {
  margin-bottom: 8px;
  color: var(--color-navy);
  font-size: 34px;
  font-family: var(--font-display);
}

.topbar p {
  color: var(--color-text-secondary);
  line-height: 1.65;
}

.dashboard-grid,
.content-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.template-page {
  display: grid;
  grid-template-columns: 280px 330px minmax(0, 1fr);
  gap: 16px;
  align-items: start;
}

.panel,
.hero-panel,
.metric-card,
.resume-preview-wrap {
  border: none;
  border-radius: 24px;
  background: var(--color-surface);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.6), 0 2px 8px rgba(15,26,46,0.06);
}

.panel,
.hero-panel,
.metric-card {
  padding: 18px;
}

.metric-card {
  display: flex;
  flex-direction: column;
}

.panel > .primary-btn {
  margin-bottom: 14px;
}

.hero-panel {
  grid-column: span 2;
  min-height: 240px;
  display: grid;
  align-content: center;
}

.hero-panel h2 {
  max-width: 780px;
  color: var(--color-navy);
  font-family: var(--font-display);
  font-size: 28px;
  line-height: 1.25;
}

.hero-panel p,
.muted,
.form-note {
  color: var(--color-text-secondary);
  line-height: 1.7;
}

.hero-actions,
.flow-steps,
.action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.planning-actions {
  align-items: center;
  margin-bottom: 14px;
}

.planning-hint {
  margin: 0;
  flex: 1 1 260px;
}

.panel-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.panel-heading .form-note {
  margin: 6px 0 0;
}

.primary-btn,
.secondary-btn {
  min-height: 40px;
  border-radius: 999px;
  padding: 0 20px;
  font-weight: 900;
  transition: transform 0.15s ease, box-shadow 0.15s ease, background 0.15s ease;
}

.primary-btn {
  border: none;
  color: #fff;
  background: var(--color-terracotta);
  box-shadow: 0 2px 6px rgba(196, 100, 74, 0.25);
}

.primary-btn:hover:not(:disabled) {
  background: var(--color-terracotta-light);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(196, 100, 74, 0.3);
}

.secondary-btn {
  border: 1.5px solid var(--color-border);
  color: var(--color-text-secondary);
  background: transparent;
}

.secondary-btn:hover:not(:disabled) {
  border-color: var(--color-terracotta);
  color: var(--color-terracotta);
}

.primary-btn:disabled,
.secondary-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.metric-card span,
.metric-card small {
  color: var(--color-text-secondary);
  font-size: 13px;
}

.metric-card strong {
  display: block;
  margin: 8px 0;
  color: var(--color-navy);
  font-family: var(--font-display);
  font-size: 34px;
}

.journey-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.journey-card {
  min-height: 148px;
  display: grid;
  align-content: start;
  gap: 10px;
  padding: 18px;
  border: none;
  border-radius: 20px;
  color: var(--color-navy);
  background: var(--color-bg);
  text-align: left;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.6), 0 2px 8px rgba(15,26,46,0.06);
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}

.journey-card:hover {
  transform: translateY(-2px);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.6), 0 8px 24px rgba(15,26,46,0.1);
}

.journey-card:focus-visible {
  outline: 3px solid rgba(196, 100, 74, 0.2);
  outline-offset: 2px;
}

.journey-card strong {
  font-size: 24px;
  font-weight: 900;
}

.journey-card small {
  color: var(--color-text-secondary);
  line-height: 1.7;
}

.journey-card--primary {
  background: linear-gradient(135deg, var(--color-bg) 0%, rgba(196, 100, 74, 0.06) 100%);
}

.journey-icon {
  width: 48px;
  height: 48px;
  display: grid;
  place-items: center;
  border-radius: 16px;
  color: var(--color-terracotta);
  background: rgba(196, 100, 74, 0.1);
  font-size: 20px;
  font-weight: 900;
}

.full-span,
.wide-panel {
  grid-column: span 2;
}

.flow-steps span {
  min-height: 38px;
  display: inline-flex;
  align-items: center;
  border: none;
  border-radius: 999px;
  padding: 0 14px;
  color: var(--color-text-secondary);
  background: var(--color-surface);
  font-weight: 900;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.6), 0 2px 8px rgba(15,26,46,0.06);
}

.field {
  display: grid;
  gap: 8px;
  margin-bottom: 14px;
}

.field span {
  color: var(--color-text-primary);
  font-size: 13px;
  font-weight: 900;
}

input,
textarea,
select {
  width: 100%;
  border: none;
  border-radius: 20px;
  padding: 11px 14px;
  color: var(--color-text-primary);
  background: var(--color-bg);
  line-height: 1.55;
  outline: none;
  box-shadow: inset 0 1px 3px rgba(15,26,46,0.06);
  transition: box-shadow 0.15s ease;
}

textarea {
  resize: vertical;
}

input:focus,
textarea:focus,
select:focus {
  box-shadow: inset 0 1px 3px rgba(15,26,46,0.06), 0 0 0 3px rgba(196, 100, 74, 0.15);
}

.direction-list,
.resume-list,
.template-list,
.compare-list,
.source-list,
.question-list {
  display: grid;
  gap: 10px;
}

.direction-list div,
.compare-card,
.source-list article,
.question-list article {
  border: none;
  border-radius: 24px;
  padding: 14px;
  background: var(--color-surface);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.6), 0 2px 8px rgba(15,26,46,0.06);
}

.direction-list strong {
  color: var(--color-terracotta);
  font-size: 24px;
}

.action-list {
  margin: 0;
  padding-left: 20px;
  color: var(--color-text-primary);
  line-height: 1.75;
}

.panel-subtitle {
  margin-bottom: 10px;
  color: var(--color-text-primary);
  font-size: 13px;
  font-weight: 900;
}

.upload-zone {
  position: relative;
  min-height: 160px;
  display: grid;
  place-content: center;
  gap: 8px;
  border: 2px dashed var(--color-border);
  border-radius: 28px;
  padding: 22px;
  color: var(--color-text-secondary);
  background: var(--color-bg);
  text-align: center;
  cursor: pointer;
  transition: border-color 0.15s ease;
}

.upload-zone:hover {
  border-color: var(--color-terracotta);
}

.upload-input {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

.metric-card--upload {
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
}

.metric-card--upload:hover,
.metric-card--upload:focus-visible {
  transform: translateY(-2px);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.6), 0 8px 24px rgba(15,26,46,0.1);
  outline: none;
}

.upload-zone.dragging {
  border-color: var(--color-terracotta);
  background: rgba(196, 100, 74, 0.04);
}

.upload-zone.success {
  border-color: var(--color-teal);
  background: rgba(45, 125, 122, 0.04);
}

.upload-trigger {
  justify-self: center;
  margin-top: 6px;
}

.file-list {
  display: grid;
  gap: 8px;
  margin: 12px 0;
}

.file-list div {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  border: none;
  border-radius: 16px;
  padding: 10px 14px;
  color: var(--color-text-primary);
  background: var(--color-bg);
  font-size: 13px;
}

.alert {
  color: #b42318;
  font-size: 13px;
  line-height: 1.6;
}

.resume-list button,
.template-list button {
  min-height: 54px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border: none;
  border-radius: 20px;
  padding: 10px 14px;
  color: var(--color-text-secondary);
  background: var(--color-bg);
  text-align: left;
  transition: background 0.15s ease, box-shadow 0.15s ease;
}

.resume-list button:hover,
.template-list button:hover {
  background: rgba(196, 100, 74, 0.04);
}

.resume-list button.active,
.template-list button.active {
  background: rgba(196, 100, 74, 0.08);
  color: var(--color-terracotta);
  box-shadow: inset 3px 0 0 var(--color-terracotta);
}

.resume-list button span {
  display: grid;
  gap: 4px;
}

.candidate-stage {
  color: var(--color-text-secondary);
  font-size: 12px;
  font-weight: 700;
}

.status-card {
  border: none;
  border-radius: 20px;
  padding: 14px;
  background: var(--color-bg);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.6), 0 2px 8px rgba(15,26,46,0.06);
}

.status-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.status-head strong {
  color: var(--color-navy);
  font-size: 18px;
}

.status-head span {
  color: var(--color-terracotta);
  font-size: 13px;
  font-weight: 900;
}

.timeline {
  display: grid;
  gap: 10px;
  margin-bottom: 12px;
}

.timeline-step {
  display: grid;
  grid-template-columns: 16px minmax(0, 1fr);
  gap: 10px;
  align-items: center;
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: 800;
}

.timeline-step i {
  width: 16px;
  height: 16px;
  border: none;
  border-radius: 999px;
  background: var(--color-border);
  transition: background 0.15s ease, box-shadow 0.15s ease;
}

.timeline-step.done,
.timeline-step.active {
  color: var(--color-text-primary);
}

.timeline-step.done i {
  background: var(--color-teal);
}

.timeline-step.active i {
  background: var(--color-terracotta);
  box-shadow: 0 0 0 4px rgba(196, 100, 74, 0.15);
}

.decision-summary {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  margin-bottom: 14px;
}

.decision-summary div,
.priority-card,
.script-box {
  border: none;
  border-radius: 20px;
  padding: 14px;
  background: var(--color-surface);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.6), 0 2px 8px rgba(15,26,46,0.06);
}

.decision-summary span {
  display: block;
  color: var(--color-text-secondary);
  font-size: 12px;
  font-weight: 900;
}

.decision-summary strong,
.priority-card strong {
  display: block;
  margin-top: 8px;
  color: var(--color-navy);
  font-family: var(--font-display);
  font-size: 24px;
}

.bar-chart {
  display: grid;
  gap: 11px;
  margin-bottom: 14px;
}

.bar-chart div {
  display: grid;
  grid-template-columns: 70px minmax(0, 1fr) 40px;
  gap: 10px;
  align-items: center;
  color: var(--color-text-primary);
  font-size: 12px;
  font-weight: 900;
}

.bar-chart b {
  height: 10px;
  border-radius: 999px;
  background: var(--color-border);
  overflow: hidden;
}

.bar-chart i {
  display: block;
  height: 100%;
  background: var(--color-terracotta);
}

.bar-chart em {
  color: var(--color-text-secondary);
  font-style: normal;
  text-align: right;
}

.explain-list {
  display: grid;
  gap: 8px;
  margin: 0;
}

.explain-list dt {
  color: var(--color-navy);
  font-size: 13px;
  font-weight: 950;
}

.explain-list dd,
.compare-card p,
.source-list p,
.script-box {
  margin: 0 0 8px;
  color: var(--color-text-primary);
  font-size: 13px;
  line-height: 1.65;
}

.script-box {
  white-space: pre-line;
}

.draft-preview {
  display: grid;
  gap: 12px;
  margin-bottom: 16px;
}

.recognition-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.recognition-card {
  padding: 14px;
  border: none;
  border-radius: 20px;
  background: var(--color-bg);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.6), 0 2px 8px rgba(15,26,46,0.06);
}

.recognition-card header,
.compare-card-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.recognition-card header {
  margin-bottom: 10px;
}

.recognition-card header strong {
  color: var(--color-navy);
  font-size: 14px;
}

.recognition-card header span {
  color: var(--color-text-secondary);
  font-size: 12px;
  font-weight: 700;
}

.recognition-items {
  margin: 0;
  padding-left: 18px;
  color: var(--color-text-primary);
  display: grid;
  gap: 8px;
}

.recognition-items li {
  line-height: 1.6;
}

.recognition-items b {
  display: block;
  margin-bottom: 2px;
  color: var(--color-navy);
  font-size: 12px;
}

.draft-section {
  padding: 14px;
  border: none;
  border-radius: 20px;
  background: var(--color-bg);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.6), 0 2px 8px rgba(15,26,46,0.06);
}

.draft-section h3 {
  margin: 0 0 8px;
  color: var(--color-navy);
  font-size: 16px;
}

.draft-section p {
  margin: 0;
  color: var(--color-text-primary);
  font-size: 13px;
  line-height: 1.7;
  white-space: pre-line;
}

.draft-preview-text {
  margin-bottom: 16px;
  border-radius: 20px;
  background: var(--color-bg);
  border: none;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.6), 0 2px 8px rgba(15,26,46,0.06);
}

.compare-card header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.compare-card header span {
  color: var(--color-text-secondary);
  font-size: 12px;
  font-weight: 800;
}

.chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 0 0 12px;
}

.info-chip,
.status-pill {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 5px 10px;
  font-size: 12px;
  font-weight: 700;
}

.info-chip {
  color: var(--color-navy);
  background: rgba(15, 26, 46, 0.06);
  border: none;
}

.info-chip--light {
  color: var(--color-teal);
  background: rgba(45, 125, 122, 0.08);
  border: none;
}

.status-pill--success {
  color: #0a7a5b;
  background: rgba(45, 125, 122, 0.1);
  border: none;
}

.status-pill--muted {
  color: var(--color-text-muted);
  background: var(--color-bg);
  border: none;
}

.optimize-overview {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 14px;
}

.optimize-metric {
  padding: 14px 16px;
  border: none;
  border-radius: 20px;
  background: var(--color-surface);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.6), 0 2px 8px rgba(15,26,46,0.06);
}

.optimize-metric span {
  display: block;
  color: var(--color-text-secondary);
  font-size: 12px;
  margin-bottom: 6px;
}

.optimize-metric strong {
  color: var(--color-navy);
  font-family: var(--font-display);
  font-size: 22px;
}

.skipped-module-list {
  display: grid;
  gap: 10px;
  margin-bottom: 14px;
}

.skipped-module-card {
  padding: 12px 14px;
  border-radius: 20px;
  border: none;
  background: rgba(196, 100, 74, 0.04);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.6), 0 2px 8px rgba(15,26,46,0.06);
}

.skipped-module-card strong {
  display: block;
  margin-bottom: 6px;
}

.skipped-module-card p,
.skipped-module-card small {
  margin: 0;
  color: var(--color-text-secondary);
}

.multiline-content {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.75;
  color: var(--color-text-primary);
}

.compare-columns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-bottom: 12px;
}

.compare-columns div {
  min-height: 150px;
  border: none;
  border-radius: 16px;
  padding: 12px;
  background: var(--color-bg);
}

.empty-state {
  min-height: 180px;
  display: grid;
  place-content: center;
  border: 1.5px dashed var(--color-border);
  border-radius: 20px;
  color: var(--color-text-muted);
  background: var(--color-bg);
  text-align: center;
}

.template-sidebar,
.resume-editor {
  position: sticky;
  top: 28px;
}

.source-box {
  margin-top: 14px;
  border: none;
  border-radius: 20px;
  padding: 12px;
  background: var(--color-bg);
  color: var(--color-text-secondary);
  font-size: 12px;
  line-height: 1.6;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.6), 0 2px 8px rgba(15,26,46,0.06);
}

.source-box a,
.source-list a {
  color: var(--color-terracotta);
  word-break: break-all;
}

.resume-preview-wrap {
  padding: 0;
  overflow: hidden;
}

.template-page {
  grid-template-columns: 1fr;
  gap: 18px;
}

.template-panel-shell,
.template-editor-shell,
.template-style-shell,
.resume-preview-wrap {
  border-radius: 24px;
}

.template-panel-title {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 14px;
}

.template-panel-title h2,
.template-editor-shell h2,
.template-style-shell h2 {
  margin: 0;
  font-size: 28px;
}

.template-panel-title--compact h2 {
  font-size: 24px;
}

.template-chip {
  border: none;
  background: rgba(196, 100, 74, 0.1);
  color: var(--color-terracotta);
  border-radius: 999px;
  padding: 8px 12px;
  font-size: 12px;
  font-weight: 700;
}

.template-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.template-card {
  position: relative;
  min-height: 120px;
  padding: 14px;
  border: none;
  border-radius: 20px;
  background: var(--color-surface);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.6), 0 2px 8px rgba(15,26,46,0.06);
  text-align: left;
  transition: transform 160ms ease, box-shadow 160ms ease;
}

.template-card:hover,
.template-card.is-selected {
  transform: translateY(-2px);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.6), 0 8px 24px rgba(15,26,46,0.1);
}

.template-swatch {
  display: block;
  width: 36px;
  height: 10px;
  margin-bottom: 14px;
  border-radius: 999px;
}

.template-name,
.template-scene,
.template-tone {
  display: block;
}

.template-name {
  font-size: 18px;
  color: var(--color-navy);
  font-family: var(--font-display);
  margin-bottom: 6px;
}

.template-scene {
  color: var(--color-text-secondary);
  margin-bottom: 4px;
}

.template-tone {
  color: var(--color-text-muted);
  font-size: 13px;
  line-height: 1.5;
}

.template-meta-box {
  margin-top: 16px;
}

.template-meta-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px 18px;
}

.template-meta-grid p {
  margin: 0;
}

.template-workspace {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(320px, 0.75fr) minmax(0, 1fr);
  gap: 18px;
  align-items: start;
}

.template-style-shell {
  display: grid;
  gap: 14px;
}

.preview-stage {
  display: grid;
  gap: 12px;
}

.preview-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 0 18px;
  color: var(--color-text-muted);
  font-size: 12px;
  text-transform: uppercase;
}

.paper-stage {
  overflow: auto;
  display: grid;
  justify-items: center;
  align-items: start;
  min-height: 0;
  padding: 20px 16px 28px;
  background: linear-gradient(180deg, rgba(247, 245, 240, 0.9), rgba(226, 221, 214, 0.94));
  border-top: 1px solid var(--color-border);
}

.resume-page {
  width: 210mm;
  min-height: 297mm;
  padding: 17mm var(--resume-page-padding, 18mm);
  background: #fff;
  color: #20231f;
  box-shadow: 0 15px 45px rgba(33, 30, 24, 0.2);
  font-size: var(--resume-base-size, 12px);
  line-height: var(--resume-line-height, 1.62);
  font-family: var(--resume-font-family, "Noto Serif SC", "Microsoft YaHei", "PingFang SC", Georgia, serif);
}

.resume-cn-campus-single,
.resume-cn-campus-double {
  color: #1f1f1f;
  background: #ffffff;
  box-shadow: 0 15px 45px rgba(33, 30, 24, 0.16);
}

.resume-cn-campus-single {
  border-top: 2px solid rgba(0, 0, 0, 0.08);
}

.resume-cn-header {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: end;
  gap: 16px;
  margin-bottom: 14px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.2);
}

.resume-cn-header-main h1,
.resume-cn-double-head h1 {
  margin: 0;
  font-size: var(--resume-name-size, 31px);
  line-height: 1.05;
  font-weight: 800;
  letter-spacing: 0.03em;
}

.resume-cn-header-main p,
.resume-cn-double-head p {
  margin: 6px 0 0;
  color: #454545;
  font-size: 14px;
  font-weight: 600;
}

.resume-contact-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 20px;
  margin-top: 12px;
  color: #333;
}

.resume-contact-stack {
  display: grid;
  gap: 6px;
  color: #2f3742;
}

.resume-cn-header-photo {
  display: flex;
  align-items: flex-end;
}

.resume-photo-block {
  display: flex;
  justify-content: center;
  margin-bottom: 18px;
}

.resume-photo {
  width: 92px;
  height: 116px;
  border: 1px solid rgba(0, 0, 0, 0.18);
  object-fit: cover;
  background: #f2f2f2;
}

.resume-photo--placeholder {
  display: grid;
  place-items: center;
  color: #777;
  font-size: 12px;
}

.resume-photo-block--empty .resume-photo--placeholder {
  border-style: dashed;
}

.resume-cn-campus-single .resume-section h2,
.resume-cn-campus-double .resume-section h2 {
  color: #111;
  font-size: var(--resume-section-title-size, 15px);
  font-weight: 800;
  border-bottom: 1px solid rgba(0, 0, 0, 0.28);
  padding-bottom: 4px;
  margin-bottom: 8px;
}

.resume-cn-campus-single .entry-head,
.resume-cn-campus-double .entry-head {
  align-items: flex-start;
}

.resume-cn-campus-single .entry-head strong,
.resume-cn-campus-double .entry-head strong {
  font-size: 13px;
  font-weight: 800;
}

.resume-cn-campus-single .entry-head span,
.resume-cn-campus-double .entry-head span {
  color: #353535;
  font-weight: 700;
}

.resume-coursework {
  margin: 4px 0 0;
  color: #444;
}

.resume-entry--compact {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 6px;
}

.resume-cn-double-shell {
  display: grid;
  grid-template-columns: minmax(120px, 0.34fr) minmax(0, 0.66fr);
  gap: 16px;
}

.resume-cn-double-sidebar {
  padding: 10px 12px 10px 0;
  border-right: 1px solid rgba(0, 0, 0, 0.18);
}

.resume-cn-double-main {
  min-width: 0;
}

.resume-cn-campus-single .skill-tags span,
.resume-cn-campus-double .skill-tags span {
  border-radius: 999px;
  padding: 2px 8px;
  font-size: 11px;
  border-color: color-mix(in srgb, var(--accent) 28%, #cfd6de);
  background: color-mix(in srgb, var(--accent) 7%, #ffffff);
}

.resume-variant-clean {
  --resume-font-family: "Noto Serif SC", "Songti SC", "SimSun", serif;
}

.resume-variant-tech {
  --resume-font-family: "Noto Sans SC", "Microsoft YaHei", "PingFang SC", sans-serif;
}

.resume-variant-ops {
  --resume-font-family: "Noto Serif SC", "Microsoft YaHei", "PingFang SC", serif;
  --resume-section-title-size: 16px;
}

.resume-variant-research {
  --resume-font-family: "Times New Roman", "Noto Serif SC", "Songti SC", serif;
}

.resume-variant-formal {
  --resume-font-family: "SimSun", "Songti SC", serif;
}

.resume-variant-double {
  --resume-font-family: "Noto Serif SC", "Microsoft YaHei", "PingFang SC", serif;
}

.resume-header {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  border-bottom: 2px solid var(--accent);
  padding-bottom: 12px;
  margin-bottom: 14px;
}

.resume-header--compact {
  display: block;
  border-bottom: 0;
}

.resume-header h1 {
  margin: 0;
  font-size: var(--resume-name-size, 31px);
  line-height: 1.08;
}

.resume-header p {
  margin: 6px 0 0;
  color: var(--accent);
  font-size: 14px;
  font-weight: 700;
}

.resume-contact {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 6px 12px;
  max-width: 320px;
  color: #56564d;
}

.resume-contact--stack {
  display: block;
  max-width: none;
}

.resume-contact span {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.resume-contact--stack span {
  display: block;
  margin-bottom: 6px;
}

.resume-section {
  margin: 0 0 var(--resume-section-gap, 12px);
  break-inside: avoid;
}

.resume-section h2 {
  margin: 0 0 6px;
  color: var(--accent);
  font-size: var(--resume-section-title-size, 15px);
  line-height: 1.25;
  border-bottom: 1px solid rgba(32, 35, 31, 0.16);
  padding-bottom: 3px;
}

.resume-entry {
  margin-bottom: var(--resume-entry-gap, 8px);
  break-inside: avoid;
}

.entry-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: baseline;
}

.entry-head strong {
  font-size: 13px;
}

.entry-head span {
  color: #6f6b61;
  white-space: nowrap;
}

.resume-lines {
  margin: 4px 0 0;
  padding-left: 18px;
}

.resume-lines li {
  margin-bottom: 3px;
}

.skill-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.skill-tags span {
  border: 1px solid color-mix(in srgb, var(--accent) 42%, #d8d8d8);
  color: #23251f;
  background: color-mix(in srgb, var(--accent) 9%, #ffffff);
  border-radius: 5px;
  padding: 3px 7px;
}

.resume-two-col {
  display: grid;
  grid-template-columns: 0.34fr 0.66fr;
  gap: 16px;
}

.resume-two-col aside {
  background: color-mix(in srgb, var(--accent) 10%, #ffffff);
  padding: 13px;
  border-right: 4px solid var(--accent);
}

.resume-center-header .resume-header {
  text-align: center;
  display: block;
}

.resume-center-header .resume-contact {
  max-width: none;
  justify-content: center;
}

.resume-dense .resume-section {
  margin-bottom: calc(var(--resume-section-gap, 12px) * 0.72);
}

.resume-dense .resume-entry {
  margin-bottom: calc(var(--resume-entry-gap, 8px) * 0.72);
}

.resume-compact {
  padding: 13mm 15mm;
  font-size: 11px;
  line-height: 1.48;
}

.resume-academic {
  font-family: "Times New Roman", "Noto Serif SC", "Songti SC", "SimSun", serif;
}

.resume-academic .resume-header {
  text-align: center;
  display: block;
  border-bottom: 1px solid #222;
}

.resume-academic .resume-contact {
  max-width: none;
  justify-content: center;
}

.resume-creative {
  border-top: 9mm solid var(--accent);
}

.creative-banner {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: var(--color-navy);
  color: var(--color-surface);
  padding: 6px 10px;
  margin-bottom: 11px;
}

.resume-creative .resume-section h2 {
  border: 0;
  background: color-mix(in srgb, var(--accent) 13%, #fff);
  padding: 4px 7px;
}

.resume-classic {
  font-family: "Noto Serif SC", "Songti SC", "SimSun", serif;
  border: 1.5mm double var(--accent);
}

.resume-classic .resume-header {
  text-align: center;
  display: block;
}

.resume-classic .resume-contact {
  justify-content: center;
  max-width: none;
}

.style-theme-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.style-theme-card {
  min-height: 82px;
  padding: 10px;
  border: 1.5px solid var(--color-border);
  border-radius: 16px;
  background: var(--color-surface);
  color: var(--color-text-primary);
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 10px;
  text-align: left;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.style-theme-card:hover {
  border-color: var(--color-terracotta);
}

.style-theme-card.is-selected {
  border-color: var(--color-terracotta);
  box-shadow: 0 4px 12px rgba(196, 100, 74, 0.15);
}

.style-theme-card__swatch {
  width: 100%;
  height: 18px;
  border-radius: 999px;
}

.style-theme-card__label {
  font-size: 13px;
  font-weight: 700;
}

.style-color-field {
  display: grid;
  grid-template-columns: 56px minmax(0, 1fr);
  gap: 8px;
}

.style-color-field__picker {
  width: 56px;
  min-width: 56px;
  height: 42px;
  padding: 4px;
}

.style-panel-section {
  padding: 14px 0 2px;
  border-bottom: 1px solid var(--color-border);
}

.style-panel-section:last-child {
  border-bottom: 0;
  padding-bottom: 0;
}

.style-panel-section__title h3 {
  margin: 0 0 12px;
  font-size: 16px;
}

.segmented-control {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 6px;
  margin-bottom: 12px;
}

.segmented-control button {
  min-height: 42px;
  padding: 8px 10px;
  border: 1.5px solid var(--color-border);
  border-radius: 999px;
  background: transparent;
  color: var(--color-text-secondary);
  transition: border-color 0.15s ease, background 0.15s ease, color 0.15s ease;
}

.segmented-control button:hover {
  border-color: var(--color-terracotta);
  color: var(--color-terracotta);
}

.segmented-control button.is-active {
  border-color: var(--color-terracotta);
  background: rgba(196, 100, 74, 0.08);
  color: var(--color-terracotta);
}

.style-slider-list {
  display: grid;
  gap: 10px;
}

.style-range {
  display: grid;
  gap: 6px;
  padding: 11px 12px;
  border: 1.5px solid var(--color-border);
  border-radius: 16px;
  background: var(--color-surface);
}

.style-range__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.style-range__head strong {
  font-size: 13px;
}

.style-range__head em {
  color: var(--color-terracotta);
  font-style: normal;
  font-weight: 700;
}

.toggle-card {
  min-height: 88px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px;
  border: 1.5px solid var(--color-border);
  border-radius: 16px;
  background: var(--color-surface);
  transition: border-color 0.15s ease;
}

.toggle-card.is-checked {
  border-color: var(--color-terracotta);
}

.toggle-card__copy strong {
  display: block;
  margin-bottom: 4px;
}

.toggle-card__copy p {
  margin: 0;
  color: var(--color-text-muted);
  font-size: 12px;
}

.toggle-card__switch {
  position: relative;
  flex: 0 0 auto;
}

.toggle-card__switch input {
  position: absolute;
  inset: 0;
  opacity: 0;
}

.toggle-card__switch span {
  width: 42px;
  height: 24px;
  display: block;
  position: relative;
  border-radius: 999px;
  background: var(--color-border);
}

.toggle-card__switch span::after {
  content: "";
  position: absolute;
  top: 3px;
  left: 3px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--color-surface);
  transition: transform 160ms ease;
}

.toggle-card__switch input:checked + span {
  background: var(--accent);
}

.toggle-card__switch input:checked + span::after {
  transform: translateX(18px);
}

.question-list article span,
.question-list article b {
  display: inline-flex;
  margin: 0 6px 8px 0;
  padding: 4px 10px;
  border-radius: 999px;
  color: var(--color-navy);
  background: rgba(15, 26, 46, 0.06);
  font-size: 12px;
}

.question-note {
  color: var(--color-text-secondary);
  font-size: 12px;
}

.inner-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

@media (max-width: 1180px) {
  .app-shell,
  .dashboard-grid,
  .content-grid,
  .template-page {
    grid-template-columns: 1fr;
  }

  .template-workspace,
  .template-grid,
  .template-meta-grid {
    grid-template-columns: 1fr;
  }

  .optimize-overview {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .resume-cn-header,
  .resume-cn-double-shell {
    grid-template-columns: 1fr;
  }

  .resume-cn-double-sidebar {
    border-right: 0;
    border-bottom: 1px solid rgba(0, 0, 0, 0.18);
    padding-right: 0;
    padding-bottom: 12px;
  }

  .sidebar,
  .template-sidebar,
  .resume-editor {
    position: static;
    min-height: auto;
  }

  .nav-list {
    grid-template-columns: repeat(2, 1fr);
  }

  .hero-panel,
  .wide-panel,
  .full-span {
    grid-column: auto;
  }

  .journey-grid {
    grid-template-columns: 1fr;
  }
}

@media print {
  body * {
    visibility: hidden;
  }

  #resume-print-area,
  #resume-print-area * {
    visibility: visible;
  }

  #resume-print-area {
    position: absolute;
    left: 0;
    top: 0;
    width: 210mm;
    min-height: 297mm;
    box-shadow: none;
  }

  @page {
    size: A4;
    margin: 0;
  }
}
</style>











