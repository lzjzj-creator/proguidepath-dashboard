# 技能证书板块重构

## 概述
技能标签板块更名为"技能证书"，用户填写的内容原文直接进入生成的简历（无 AI 改写），并以网格多列布局展示。

## 改动范围

涉及 5 个文件：

| # | 文件 | 改动 |
|---|---|---|
| 1 | `resume-studio.tsx` | 步骤名"技能标签"→"技能证书" |
| 2 | `resume-preview.tsx` | 区块标题"技能标签"→"技能证书"；items grid 多列布局 |
| 3 | `resume-html.ts` | PDF 模板标题"技能标签"→"技能证书" |
| 4 | `mock-ai.ts` | `generateResumeHeuristics.skills.groups` 直接映射用户输入 |
| 5 | `server-ai.ts` | prompt 指令禁止 AI 改写技能区 |
| 6 | `resume-studio.tsx` | 多处用户可见文本："技能标签"→"技能证书"（步骤导航、表单标签、Agent 面板标题、提示文案） |
| 7 | 测试文件 | 如有标题断言需更新 |

## 数据映射

| 用户字段 | 生成到简历 | Skill Group |
|---|---|---|
| `skillTags` | ✅ 原文放入 | `{ title: "技能", items: skillTags }` |
| `certificates` | ✅ 原文放入 | `{ title: "证书", items: [certificates + 语言] }` |
| `languages` | ✅ 放入"证书"组 | 与 certificates 合并为一个 group |
| `extraNotes` | ✅ 有内容时 | `{ title: "补充备注", items: [extraNotes] }` |

## 布局样式

参考图样式——网格多列布局：

```
技能证书

  技能                     证书
    Python    SQL            阿里云 ACA       英语六级
    Tableau  数据分析         人工智能证书

  补充备注（如有）
    ...
```

skills.groups 保持现有数据结构不变，`resume-preview.tsx` 将 items 从单列改为 grid 网格渲染。

## 不改写规则

- **mock-ai.ts** (`generateResumeHeuristics`)：直接将用户输入映射为 groups，不做任何合并、分词、去重等处理
- **server-ai.ts** (`generateResume`)：prompt 中明确指令要求 AI 直接使用用户原文作为技能区，不改写、不润色、不新增内容
- **resume-studio.tsx**：选中技能区块时禁用改写按钮（技能板块不支持 AI 润写）

## 不受影响的部分

- 目标岗位、教育经历、校园/社会经历的 AI 生成流程不变
- 简历头部个人信息不变
- PDF 导出整体流程不变
- `generateResume` 的 hasContent 校验逻辑保留
