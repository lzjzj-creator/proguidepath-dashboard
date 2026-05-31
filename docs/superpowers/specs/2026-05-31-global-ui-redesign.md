# Global UI Redesign — Future Academic

**Goal:** Replace all three frontend UIs (landing page, resume optimizer, resume generator) with a cohesive "Future Academic" visual identity that feels distinctive, warm, and professional for Chinese Gen Z job seekers.

**Core directive:** Eliminate obvious rectangular blocks. All containers use large border-radius (24px–40px), pill-like forms, organic curves, and asymmetrical composition.

---

## 1. Design System

### 1.1 Color Palette

```css
--color-bg:            #f7f5f0    /* 暖白纸色基底 */
--color-surface:       #ffffff    /* 卡片/表单背景 */
--color-navy:          #0f1a2e    /* 深海蓝（主色）*/
--color-navy-light:    #1a2d4a    /* 深海蓝浅一度 */
--color-terracotta:    #c4644a    /* 赤陶橙（强调色）*/
--color-terracotta-light:#e0896e  /* 赤陶橙悬停 */
--color-teal:          #2d7d7a    /* 松石绿（辅助）*/
--color-amber:         #d4944a    /* 琥珀色（辅助）*/

--color-text-primary:   #1a1a1a
--color-text-secondary: #6b6560
--color-text-muted:     #a09890
--color-border:         #e2ddd6
--color-border-hover:   #c9c2b8
```

### 1.2 Typography

| Usage | Latin | Chinese |
|---|---|---|
| Hero / Display (40px+) | Cabinet Grotesk Bold, -0.03em tracking | PingFang SC Bold |
| Section Heading (24–32px) | Satoshi Bold | PingFang SC Semibold |
| Subheading (16–20px) | Satoshi Medium | PingFang SC Medium |
| Body (14–16px) | Satoshi Regular | PingFang SC / Noto Sans SC |
| Labels / Mono (10–12px) | JetBrains Mono, +0.2em tracking | — |

Chinese fonts use system stack (`PingFang SC, "Microsoft YaHei", sans-serif`) to avoid CJK font file loading.

### 1.3 Component Tokens

- **Card**: `background: var(--color-surface)`, `border-radius: 24px`, `box-shadow: inset 0 1px 0 rgba(255,255,255,0.6), 0 2px 8px rgba(15,26,46,0.06)`. No visible border line; use shadow depth for hierarchy.
- **Button Primary**: `background: var(--color-terracotta)`, `border-radius: 999px`, `padding: 12px 28px`. Hover: shift to `var(--color-terracotta-light)`.
- **Button Secondary**: `background: transparent`, `border: 1.5px solid var(--color-border)`, `border-radius: 999px`. Hover: border shifts to `var(--color-terracotta)`.
- **Input / Textarea**: `background: var(--color-surface)`, `border: none`, `border-radius: 20px`, `padding: 14px 20px`, subtle inset shadow. Focus: `box-shadow: 0 0 0 3px rgba(196, 100, 74, 0.15)`.
- **Divider**: Use spacing or background shift instead of `<hr>` lines. When a line is needed, use a soft gradient fade rather than a solid stroke.
- **Status indicator**: Pill badge with `border-radius: 999px`, small dot + label.

### 1.4 Texture & Atmosphere

- **Background noise**: Subtle grain/noise overlay on the page background (`#f7f5f0` base + noise) to give a paper-like texture.
- **Decorative ghost text**: Large, low-opacity typography as background watermark (e.g., "RESUME" or "2026") for visual depth.
- **Transitions**: All interactive elements use `200ms ease-out` for color/shadow transitions.
- **Shadows**: Use warm-toned shadows (`rgba(15,26,46, 0.06)`) instead of cool/blue shadows to match the warm palette.

---

## 2. Landing Page Redesign

### 2.1 Layout

```
┌────────────────────────────────────────────────────┐
│ [▦] 简历工作台                    [● 就绪]          │ ← slim header
│                                                    │
│   ┌───────────────────────────┐                     │
│   │ 你的下一份简历，             │                     │
│   │ 从这里开始                  │                     │ ← hero, left-aligned
│   │ ─────────────              │                     │
│   │ 面向校招的 AI 简历工作台     │                     │
│   │                           │                     │
│   │        [开始使用 →]        │                     │ ← terracotta CTA
│   └───────────────────────────┘                     │
│                                                    │
│    ┌──────────────┐    ┌──────────┐                │
│    │  ✦ 我有简历    │    │ ✦ 从零开始│               │ ← asymmetrical cards
│    │              │    │          │                │
│    │ AI 分析优化    │    │ 逐步创建  │                │
│    │ 排版 匹配 导出 │    │ 专业简历  │                │
│    └──────────────┘    └──────────┘                │
│                                                    │
│    ┌──────────────────────────────────────┐         │
│    │ 支持 PDF/DOCX · 安全加密 · 免费使用   │         │ ← pill footer
│    └──────────────────────────────────────┘         │
└────────────────────────────────────────────────────┘
```

### 2.2 Key Changes from Current

- **No centered hero**: Headline left-aligned, large bold Cabinet Grotesk display text (48px+). A terracotta accent bar (short, thick) under the headline, not a full gradient strip.
- **Navigation cards asymmetrical**: Left card (已有一份简历) slightly wider, right card (从零开始) slightly smaller and offset vertically. No footer/divider inside cards — content flows freely.
- **Ghost watermark**: A large faded "RESUME" or "OFFER" text in the background, 200px+, opacity 0.03, angled slightly.
- **Background grain**: CSS noise texture overlay via pseudo-element.
- **Responsive**: At <768px, cards stack and hero shrinks but remains left-aligned.

---

## 3. Resume Optimizer Redesign

### 3.1 Layout

```
┌─────────────────────────────────────────────────────┐
│ ← 返回首页                                           │
│                                                     │
│  ┌──────────────┐    ┌────────────────────────┐     │
│  │ 上传简历区     │    │ 分析总览                │     │
│  │              │    │                        │     │
│  │ [dash-border │    │ ● 综合评分  8.5/10     │     │
│  │  drop zone]  │    │ ● 排版问题  3项        │     │
│  │              │    │ ● 内容建议  5项        │     │
│  │ 拖拽或点击    │    │ ● 岗位匹配  72%       │     │
│  │ 上传 PDF     │    │                        │     │
│  │              │    │ [查看详细分析 →]       │     │
│  └──────────────┘    └────────────────────────┘     │
│                                                     │
│  ┌────────────────────────────────────────────┐     │
│  │  简历预览 / 编辑器                          │     │
│  │  ┌──────────────────────────────────┐      │     │
│  │  │  (渲染的简历内容)                   │      │     │
│  │  │  点击右侧建议项 → 此处高亮          │      │     │
│  │  │  可原地编辑                        │      │     │
│  │  └──────────────────────────────────┘      │     │
│  └────────────────────────────────────────────┘     │
│                                                     │
│  [导出优化版]  [重新上传]                             │
└─────────────────────────────────────────────────────┘
```

### 3.2 Key Design Points

- **Drop zone**: Large pill-shaped area (border-radius: 32px), dashed terracotta border, centered icon + "拖拽简历到此处" text. On drag-over: border becomes solid + subtle glow animation.
- **Upload progress**: Circular ring progress indicator (not a linear bar). Uses terracotta-to-teal gradient arc.
- **Analysis pills**: Each issue category rendered as a pill/tag (border-radius: 999px) with icon + count. Click to expand details in a slide-down panel.
- **Preview area**: Full-width, bordered only by subtle shadow, large rounded corners (24px). Rendered resume content inside.
- **Highlight linking**: Clicking an analysis pill scrolls the preview to the relevant section and highlights it with a warm glow.

### 3.3 States

- **Empty state**: Large pill drop zone centered, ghost text "拖拽或点击上传" in the background
- **Uploading**: Pulsing ring animation, percentage text in center
- **Analyzing**: Skeleton pills (3 shimmering rounded bars) in right panel
- **Error**: Drop zone turns terracotta border with shake animation, error message in a pill below
- **Complete**: Preview renders, analysis pills populate, export button appears

---

## 4. Resume Generator Redesign

### 4.1 Layout (unchanged three-column, organic styling)

```
┌─────────────────────────────────────────────────────────┐
│ [◁ 新建草稿]   面向校招的 AI 简历工作台     [状态] [导出]  │
│                                                         │
│  ┌──────┐    ┌──────────────────┐    ┌──────────────┐   │
│  │ 步骤  │    │   表单/编辑区      │    │  AI 助手     │   │
│  │      │    │                  │    │              │   │
│  │ ⬤─╲   │    │   [pill inputs]  │    │  [chat       │   │
│  │ ⬤──╲  │    │                  │    │   bubbles]   │   │
│  │ ⬤───╲ │    │   [experience    │    │              │   │
│  │ ⬤────╲│    │    cards]        │    │  [suggestion │   │
│  │ ⬤─────╲│   │                  │    │   pills]     │   │
│  └──────┘    └──────────────────┘    └──────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### 4.2 Key Changes from Current

**Left sidebar — Step Navigation:**
- Replace rectangular step buttons with a **vertical serpentine path**: circular nodes (36px) connected by an S-curve line. Completed nodes filled with teal, current node filled with terracotta, future nodes outlined in warm gray.
- Step labels placed to the right of each node, not inside. Summary text below label in muted color.
- Container: border-radius 32px, warm surface background, no visible border.

**Center — Form Area:**
- All `<input>`, `<select>`, `<textarea>` use the pill input token (border-radius: 20px, no border, subtle inset shadow).
- **Experience cards**: Replace the current bordered card with a floating pill (border-radius: 28px), inset shadow, no visible border line. Active state: terracotta side accent (a small bar on the left edge, rounded).
- Form layout uses natural vertical rhythm with generous padding rather than dense grid.
- The "step X of Y" indicator becomes a small pill in the top-right corner of the form area.

**Right — AI Chat Sidebar:**
- Chat messages: assistant messages in warm white pills (border-radius: 24px), user messages in terracotta pills.
- The "thinking..." state renders as a subtle pulsing three-dot animation in a ghost pill.
- **Suggestion cards**: Terracotta-border pills with a "apply" tag. Hover shifts the entire card slightly up (+ translateY(-2px)).
- Scrollbar styled to match the warm palette (thin, rounded thumb).
- Input area: pill input at the bottom of the sidebar, flush with bottom, no visible container border.

**Top Header Bar:**
- "新建草稿" becomes a small ghost button (no border, just text + icon, hover shows underline).
- Title: Cabinet Grotesk semibold, dark navy, left-aligned.
- Status + export button: right-aligned. Status rendered as a small pill.

**Edit Mode (post-generation):**
- Block selector (summary, education, skills tabs): pill-shaped tab bar, selected tab has terracotta underline accent.
- Preview renders on a simulated paper background (slight off-white with subtle shadow edges).
- Rewrite intent input: collapsed into a small pill that expands on click.

### 4.3 States

- **Intake mode**: Steps visible, form shows current step, AI sidebar shows step-specific assistant
- **Generating**: Center area shows a pulsing skeleton with step-by-step status text below
- **Edit mode**: Left sidebar collapses to show only step checkmarks (compact), preview dominates center
- **Loading draft**: Centered skeleton pill with pulse animation
- **Error**: Inline terracotta pill notification, non-blocking

---

## 5. Shared Patterns

- **Navigation between apps**: Landing page cards link to each tool. Each tool has a subtle "← 返回首页" link in the top bar.
- **Toast/notification**: Slide-in from top-right, pill-shaped (border-radius: 999px), terracotta for errors, teal for success.
- **Skeleton loading**: Rounded pill shapes (not rectangular blocks) with shimmer animation.
- **Scrollbar global style**: Thin (6px), rounded (3px), warm gray thumb.
