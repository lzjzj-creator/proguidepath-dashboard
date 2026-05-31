# Resume Generator Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restyle the resume generator (Next.js 16 + React 19 + Tailwind CSS 4) with the Future Academic design system. Updates CSS variables, fonts, and all component classNames. Replaces all blue/sky color palette with warm/terracotta/navy. Eliminates rectangular blocks.

**Architecture:** Tailwind CSS 4 theme customization in globals.css + font imports in layout.tsx + bulk className replacements in resume-studio.tsx and resume-preview.tsx. The three-column layout structure stays intact; styling and visual language change completely.

**Tech Stack:** Next.js 16.2.6, React 19, Tailwind CSS 4, Bricolage Grotesque + Outfit fonts

---

### Task 1: Update globals.css with Future Academic design tokens

**Files:**
- Modify: `apps/resume-generator/src/app/globals.css`

- [ ] **Step 1: Read current globals.css**

Run: `cat apps/resume-generator/src/app/globals.css`

- [ ] **Step 2: Replace entire globals.css content**

```css
@import "tailwindcss";

:root {
  --color-bg: #f7f5f0;
  --color-surface: #ffffff;
  --color-navy: #0f1a2e;
  --color-navy-light: #1a2d4a;
  --color-terracotta: #c4644a;
  --color-terracotta-light: #d47a5e;
  --color-teal: #2d7d7a;
  --color-text-primary: #1a1a1a;
  --color-text-secondary: #6b6560;
  --color-text-muted: #a09890;
  --color-border: #e2ddd6;
  --color-border-hover: #c9c2b8;
}

@theme inline {
  --color-background: var(--color-bg);
  --color-foreground: var(--color-text-primary);
  --font-sans: var(--font-outfit), 'PingFang SC', 'Noto Sans SC', sans-serif;
  --font-mono: var(--font-plex-mono), monospace;
  --font-display: var(--font-bricolage), 'PingFang SC', sans-serif;
  /* Custom tokens */
  --color-navy: var(--color-navy);
  --color-navy-light: var(--color-navy-light);
  --color-terracotta: var(--color-terracotta);
  --color-terracotta-light: var(--color-terracotta-light);
  --color-teal: var(--color-teal);
  --color-border: var(--color-border);
  --color-border-hover: var(--color-border-hover);
  --color-muted: var(--color-text-muted);
}

/* Remove the old blue-tinted body background — set from globals */
body {
  background: var(--color-bg);
  color: var(--color-text-primary);
  font-family: var(--font-sans);
}

/* Keep existing utility classes that are neutral (field, toast, animations) */
.field {
  display: grid;
  gap: 0.65rem;
}

.field span {
  font-size: 0.8rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--color-text-muted);
  font-weight: 600;
}

.field input,
.field textarea,
.field select {
  width: 100%;
  border-radius: 20px;
  border: none;
  background: #f7f5f0;
  padding: 0.95rem 1rem;
  color: var(--color-text-primary);
  font-family: var(--font-sans);
  outline: none;
  box-shadow: inset 0 1px 3px rgba(15,26,46,0.06);
  transition: box-shadow 0.2s ease, background 0.2s ease;
}

.field textarea {
  min-height: 7.5rem;
  resize: vertical;
}

.field input:focus,
.field textarea:focus,
.field select:focus {
  box-shadow: 0 0 0 3px rgba(196, 100, 74, 0.12), inset 0 1px 3px rgba(15,26,46,0.06);
  background: #ffffff;
}

/* Keep toast and animation utilities unchanged */
.toast-enter { animation: toast-in 0.3s ease-out forwards; }
@keyframes toast-in {
  from { opacity: 0; transform: translateY(-12px) scale(0.96); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}
@keyframes flash-pulse {
  0% { box-shadow: 0 0 0 0 rgba(196, 100, 74, 0.25); }
  50% { box-shadow: 0 0 0 4px rgba(196, 100, 74, 0.1); }
  100% { box-shadow: 0 0 0 0 rgba(196, 100, 74, 0); }
}
.field-flash { animation: flash-pulse 1.5s ease-out; }
.stream-cursor::after {
  content: "|";
  animation: blink 0.7s step-end infinite;
  color: var(--color-terracotta);
  font-weight: 300;
}
@keyframes blink { 50% { opacity: 0; } }
.message-enter { animation: msg-in 0.25s ease-out forwards; }
@keyframes msg-in {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
.thinking-block {
  background: #edeae4;
  border-radius: 16px;
  padding: 12px 16px;
  font-size: 0.85rem;
  color: var(--color-text-secondary);
  line-height: 1.6;
}

.ai-sidebar::-webkit-scrollbar { width: 4px; }
.ai-sidebar::-webkit-scrollbar-track { background: transparent; }
.ai-sidebar::-webkit-scrollbar-thumb { background: var(--color-border); border-radius: 8px; }
.ai-sidebar::-webkit-scrollbar-thumb:hover { background: var(--color-border-hover); }
```

- [ ] **Step 3: Run build check**

Run: `cd apps/resume-generator && npx tailwindcss --help` (verify tailwind is available)
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add apps/resume-generator/src/app/globals.css
git commit -m "feat(globals): add Future Academic design tokens"
```

---

### Task 2: Update layout.tsx fonts

**Files:**
- Modify: `apps/resume-generator/src/app/layout.tsx`

- [ ] **Step 1: Replace font imports**

Replace the existing `Cormorant_Garamond`, `IBM_Plex_Mono`, `Manrope` imports with `Bricolage_Grotesque` and `Outfit`:

```tsx
import type { Metadata } from "next";
import { Bricolage_Grotesque, Outfit, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";

const display = Bricolage_Grotesque({
  variable: "--font-bricolage",
  subsets: ["latin"],
  weight: ["600", "700", "800"],
});

const sans = Outfit({
  variable: "--font-outfit",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

const mono = IBM_Plex_Mono({
  variable: "--font-plex-mono",
  subsets: ["latin"],
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: "OfferLab 校招简历工作台",
  description: "面向校招场景的 AI 简历工作台",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="zh-CN"
      suppressHydrationWarning
      className={`${display.variable} ${sans.variable} ${mono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col" suppressHydrationWarning>{children}</body>
    </html>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add apps/resume-generator/src/app/layout.tsx
git commit -m "feat(layout): replace fonts with Bricolage Grotesque + Outfit"
```

---

### Task 3: Restyle resume-studio.tsx — background, header, sidebar

**Files:**
- Modify: `apps/resume-generator/src/components/resume-studio.tsx`

- [ ] **Step 1: Read the file and plan replacements**

Run: `wc -l apps/resume-generator/src/components/resume-studio.tsx`
This file is ~1550 lines. All visual styling is via Tailwind classNames.

- [ ] **Step 2: Replace outer background and container**

Find the outer `<div>` class (line 763) and replace:

```tsx
// OLD:
className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(56,189,248,0.18),_transparent_30%),radial-gradient(circle_at_bottom_right,_rgba(59,130,246,0.16),_transparent_36%),linear-gradient(180deg,#f6fbff_0%,#eef6ff_44%,#f8fbff_100%)] text-slate-800"

// NEW:
className="min-h-screen bg-background text-[var(--color-text-primary)]"
```

Replace the inner container card (the `rounded-[40px] border border-white/70 bg-white/80 p-6 shadow-[0_32px_120px_rgba(37,99,235,0.10)] backdrop-blur` div):

```tsx
// OLD:
className="rounded-[40px] border border-white/70 bg-white/80 p-6 shadow-[0_32px_120px_rgba(37,99,235,0.10)] backdrop-blur"

// NEW:
className="rounded-[40px] bg-surface p-6 shadow-[0_2px_16px_rgba(15,26,46,0.06)]"
```

- [ ] **Step 3: Replace header area**

Replace the info panel (the `rounded-[32px] border border-sky-100 bg-[linear-gradient(180deg,#f9fcff_0%,#eef6ff_100%)] p-5 ...` div near the header):

```tsx
// OLD (header info grid):
className="grid gap-4 rounded-[32px] border border-sky-100 bg-[linear-gradient(180deg,#f9fcff_0%,#eef6ff_100%)] p-5 text-sm text-slate-600 md:w-[360px]"

// NEW:
className="grid gap-4 rounded-[32px] bg-surface p-5 text-sm text-[var(--color-text-secondary)] shadow-[inset_0_1px_0_rgba(255,255,255,0.6),0_2px_8px_rgba(15,26,46,0.06)] md:w-[360px]"
```

Replace the "当前模式" / "编辑" badge:
```tsx
// OLD:
<span className="rounded-full bg-blue-700 px-3 py-1 text-xs uppercase tracking-[0.24em] text-white">

// NEW:
<span className="rounded-full bg-[var(--color-terracotta)] px-3 py-1 text-xs uppercase tracking-[0.24em] text-white">
```

Replace the status indicator dot class:
```tsx
// OLD:
text-emerald-600 / bg-emerald-500
// NEW:
text-[var(--color-teal)] / bg-[var(--color-teal)]
```

Replace AI status:
```tsx
// OLD:
<span className={`flex items-center gap-1.5 ${aiConfigured ? "text-emerald-600" : "text-amber-600"}`}>
// NEW:
<span className={`flex items-center gap-1.5 ${aiConfigured ? "text-[var(--color-teal)]" : "text-[var(--color-terracotta)]"}`}>
```

Replace "border-b border-sky-100" divider lines in headers:
```tsx
// OLD:
"border-b border-sky-100"
// NEW:
"border-b border-[var(--color-border)]"
```

- [ ] **Step 4: Replace left sidebar step navigation**

Replace the sidebar container:
```tsx
// OLD:
className="rounded-[32px] border border-sky-100 bg-[linear-gradient(180deg,#fcfeff_0%,#f5faff_100%)] p-5 shadow-[0_18px_60px_rgba(59,130,246,0.08)]"

// NEW:
className="rounded-[32px] bg-surface p-5 shadow-[inset_0_1px_0_rgba(255,255,255,0.6),0_2px_8px_rgba(15,26,46,0.06)]"
```

Replace step button active state (the step with the blue-700 background):
```tsx
// OLD:
className={cn(
  "w-full rounded-[24px] border px-4 py-4 text-left transition",
  currentStep === index
    ? "border-blue-700 bg-blue-700 text-white shadow-[0_18px_50px_rgba(37,99,235,0.22)]"
    : "border-sky-100 bg-white hover:border-blue-200",
)}

// NEW:
className={cn(
  "w-full rounded-[24px] px-4 py-4 text-left transition",
  currentStep === index
    ? "bg-[var(--color-navy)] text-white shadow-[0_8px_24px_rgba(15,26,46,0.15)]"
    : "bg-surface hover:shadow-[inset_0_1px_0_rgba(255,255,255,0.6),0_4px_12px_rgba(15,26,46,0.06)] shadow-[inset_0_1px_0_rgba(255,255,255,0.6),0_2px_8px_rgba(15,26,46,0.04)]",
)}
```

Replace step text colors:
```tsx
// OLD:
className={cn(
  "font-mono text-[10px] uppercase tracking-[0.26em]",
  currentStep === index ? "text-blue-100" : "text-sky-400",
)}
// NEW:
className={cn(
  "font-mono text-[10px] uppercase tracking-[0.26em]",
  currentStep === index ? "text-[var(--color-text-muted)]/70" : "text-[var(--color-text-muted)]",
)}
```

Replace the completion dot:
```tsx
// OLD:
className={cn("mt-1 h-3 w-3 rounded-full", completion[index] ? "bg-emerald-400" : "bg-sky-100")}
// NEW:
className={cn("mt-1 h-3 w-3 rounded-full", completion[index] ? "bg-[var(--color-teal)]" : "bg-[var(--color-border)]")}
```

Replace the "新建草稿" button:
```tsx
// OLD:
className="rounded-full border border-sky-100 px-3 py-2 text-xs text-slate-500 transition hover:border-blue-600 hover:text-blue-700"
// NEW:
className="rounded-full border border-[var(--color-border)] px-3 py-2 text-xs text-[var(--color-text-secondary)] transition hover:border-[var(--color-terracotta)] hover:text-[var(--color-terracotta)]"
```

- [ ] **Step 5: Replace center form area styling**

Replace the main content container:
```tsx
// OLD:
className="rounded-[32px] border border-sky-100 bg-white p-6 shadow-[0_24px_80px_rgba(59,130,246,0.08)]"
// NEW:
className="rounded-[32px] bg-surface p-6 shadow-[inset_0_1px_0_rgba(255,255,255,0.6),0_2px_8px_rgba(15,26,46,0.06)]"
```

Replace form section header labels:
```tsx
// OLD everywhere:
"font-mono text-[11px] uppercase tracking-[0.3em] text-sky-600"
// NEW:
"font-mono text-[11px] uppercase tracking-[0.3em] text-[var(--color-text-muted)]"
```

Replace "步骤 X / N" pill:
```tsx
// OLD:
className="rounded-full bg-sky-50 px-4 py-2 text-xs text-slate-600"
// NEW:
className="rounded-full bg-[var(--color-bg)] px-4 py-2 text-xs text-[var(--color-text-secondary)]"
```

Replace "上一步" / "下一步" buttons:
```tsx
// OLD (prev):
className="rounded-full border border-sky-100 px-5 py-3 text-sm transition hover:border-blue-700 hover:text-blue-700 disabled:cursor-not-allowed disabled:opacity-40"
// NEW (prev):
className="rounded-full border border-[var(--color-border)] px-5 py-3 text-sm text-[var(--color-text-secondary)] transition hover:border-[var(--color-terracotta)] hover:text-[var(--color-terracotta)] disabled:cursor-not-allowed disabled:opacity-40"

// OLD (next):
className="rounded-full bg-blue-700 px-5 py-3 text-sm text-white transition hover:bg-blue-600"
// NEW (next):
className="rounded-full bg-[var(--color-terracotta)] px-5 py-3 text-sm text-white transition hover:bg-[var(--color-terracotta-light)]"
```

Replace "生成简历" button:
```tsx
// OLD:
className="rounded-full bg-blue-700 px-5 py-3 text-sm text-white transition hover:bg-blue-600 disabled:cursor-not-allowed disabled:opacity-60"
// NEW:
className="rounded-full bg-[var(--color-terracotta)] px-5 py-3 text-sm text-white transition hover:bg-[var(--color-terracotta-light)] disabled:cursor-not-allowed disabled:opacity-60"
```

Replace "返回采集" button:
```tsx
// OLD:
className="rounded-full border border-sky-100 px-4 py-3 text-sm transition hover:border-blue-700 hover:text-blue-700"
// NEW:
className="rounded-full border border-[var(--color-border)] px-4 py-3 text-sm text-[var(--color-text-secondary)] transition hover:border-[var(--color-terracotta)] hover:text-[var(--color-terracotta)]"
```

- [ ] **Step 6: Replace experience cards inside the form**

Find the ExperienceCard component's container style:
```tsx
// OLD:
className={cn(
  "rounded-[28px] border bg-[linear-gradient(180deg,#fcfeff_0%,#f3f9ff_100%)] p-5 transition",
  isActive
    ? "border-blue-500 shadow-[0_18px_50px_rgba(37,99,235,0.12)]"
    : "border-sky-100",
)}
// NEW:
className={cn(
  "rounded-[28px] bg-surface p-5 transition shadow-[inset_0_1px_0_rgba(255,255,255,0.6)]",
  isActive
    ? "shadow-[0_8px_24px_rgba(15,26,46,0.08)] ring-2 ring-[var(--color-terracotta)]/20"
    : "shadow-[0_2px_8px_rgba(15,26,46,0.04)]",
)}
```

Replace the "AI 当前作用于此" badge:
```tsx
// OLD:
className="rounded-full bg-blue-700 px-3 py-2 text-[10px] uppercase tracking-[0.22em] text-white"
// NEW:
className="rounded-full bg-[var(--color-terracotta)] px-3 py-2 text-[10px] uppercase tracking-[0.22em] text-white"
```

Replace the experience "删除" button:
```tsx
// OLD:
className="rounded-full border border-sky-100 px-3 py-2 text-xs text-slate-500 transition hover:border-blue-600 hover:text-blue-700"
// NEW:
className="rounded-full border border-[var(--color-border)] px-3 py-2 text-xs text-[var(--color-text-secondary)] transition hover:border-[var(--color-terracotta)] hover:text-[var(--color-terracotta)]"
```

Replace "新增社会经历" button:
```tsx
// OLD:
className="rounded-full border border-dashed border-blue-300 px-4 py-3 text-sm text-blue-700 transition hover:border-blue-700"
// NEW:
className="rounded-full border border-dashed border-[var(--color-border)] px-4 py-3 text-sm text-[var(--color-terracotta)] transition hover:border-[var(--color-terracotta)]"
```

- [ ] **Step 7: Replace right AI sidebar styling**

Replace the AI sidebar container:
```tsx
// OLD:
className="ai-sidebar max-h-[calc(100vh-10rem)] overflow-y-auto rounded-[32px] border border-sky-100 bg-[linear-gradient(180deg,#fcfeff_0%,#f2f8ff_100%)] p-5 shadow-[0_20px_70px_rgba(59,130,246,0.08)]"
// NEW:
className="ai-sidebar max-h-[calc(100vh-10rem)] overflow-y-auto rounded-[32px] bg-surface p-5 shadow-[inset_0_1px_0_rgba(255,255,255,0.6),0_2px_8px_rgba(15,26,46,0.06)]"
```

Replace chat message bubbles:
```tsx
// OLD (assistant):
className={cn(
  "rounded-[24px] px-4 py-4 text-sm leading-7",
  message.role === "assistant"
    ? "bg-white text-slate-700"
    : "bg-blue-700 text-white",
)}
// NEW:
className={cn(
  "rounded-[24px] px-4 py-4 text-sm leading-7",
  message.role === "assistant"
    ? "bg-[var(--color-bg)] text-[var(--color-text-primary)]"
    : "bg-[var(--color-terracotta)] text-white",
)}
```

Replace suggestion card button:
```tsx
// OLD:
className="w-full rounded-[22px] border border-sky-100 bg-white px-4 py-3 text-left text-sm transition hover:border-blue-600 hover:text-blue-700"
// NEW:
className="w-full rounded-[22px] border border-[var(--color-border)] bg-[var(--color-bg)] px-4 py-3 text-left text-sm transition hover:border-[var(--color-terracotta)] hover:text-[var(--color-terracotta)]"
```

Replace "一键应用" badge:
```tsx
// OLD:
className="rounded-full bg-sky-50 px-3 py-1 text-[10px] uppercase tracking-[0.22em] text-sky-700"
// NEW:
className="rounded-full bg-[var(--color-terracotta)]/10 px-3 py-1 text-[10px] uppercase tracking-[0.22em] text-[var(--color-terracotta)]"
```

Replace "当前选中" section in edit mode:
```tsx
// OLD:
className="mt-5 rounded-[24px] border border-sky-100 bg-white p-4"
// NEW:
className="mt-5 rounded-[24px] bg-[var(--color-bg)] p-4"

// OLD:
className="mt-4 w-full rounded-full bg-blue-700 px-4 py-3 text-sm text-white transition hover:bg-blue-600 disabled:cursor-not-allowed disabled:opacity-60"
// NEW:
className="mt-4 w-full rounded-full bg-[var(--color-terracotta)] px-4 py-3 text-sm text-white transition hover:bg-[var(--color-terracotta-light)] disabled:cursor-not-allowed disabled:opacity-60"
```

Replace the "正在思考..." loading state:
```tsx
// OLD:
className="mt-4 rounded-[24px] bg-white px-4 py-4 text-sm leading-7 text-slate-500"
// NEW:
className="mt-4 rounded-[24px] bg-[var(--color-bg)] px-4 py-4 text-sm leading-7 text-[var(--color-text-muted)]"
```

Replace the bottom status bar:
```tsx
// OLD:
className="mt-5 rounded-[24px] bg-blue-700 px-4 py-4 text-sm leading-7 text-white"
// NEW:
className="mt-5 rounded-[24px] bg-[var(--color-navy)] px-4 py-4 text-sm leading-7 text-white"
```

Replace the "border border-dashed border-blue-200" in edit mode hint:
```tsx
// OLD:
className="mt-5 rounded-[24px] border border-dashed border-blue-200 px-4 py-4 text-sm leading-7 text-slate-500"
// NEW:
className="mt-5 rounded-[24px] border border-dashed border-[var(--color-border)] px-4 py-4 text-sm leading-7 text-[var(--color-text-muted)]"
```

Replace the "✎ 简历优化 / A4 / ↗ 投递" labels:
```tsx
// OLD:
className="font-mono text-[11px] uppercase tracking-[0.26em] text-sky-600"
// NEW:
className="font-mono text-[11px] uppercase tracking-[0.26em] text-[var(--color-text-muted)]"
```

- [ ] **Step 8: Run dev server to verify**

The dev server should be running at http://localhost:3000. Check:
- Warm paper background, no blue gradients
- Three-column layout preserved but with warm surface cards
- Step navigation buttons: active state in navy blue, not blue-700
- All action buttons: terracotta instead of blue
- All borders: warm gray (#e2ddd6) instead of sky blue
- Chat bubbles: assistant in warm gray bg, user in terracotta
- Form inputs: 20px border-radius, no border, warm bg
- Experience cards: ring highlight instead of blue border

Run: Open http://localhost:3000 in browser
Expected: Full restyled generator with cohesive warm theme

- [ ] **Step 9: Commit**

```bash
git add apps/resume-generator/src/components/resume-studio.tsx
git commit -m "feat(studio): restyle with Future Academic color palette"
```

---

### Task 4: Restyle resume-preview.tsx

**Files:**
- Modify: `apps/resume-generator/src/components/resume-preview.tsx`

- [ ] **Step 1: Replace preview container**

```tsx
// OLD:
className="rounded-[36px] border border-sky-100 bg-[linear-gradient(180deg,#fcfeff_0%,#f2f8ff_100%)] p-8 shadow-[0_24px_90px_rgba(59,130,246,0.10)]"
// NEW:
className="rounded-[36px] bg-surface p-8 shadow-[inset_0_1px_0_rgba(255,255,255,0.6),0_2px_8px_rgba(15,26,46,0.06)]"
```

- [ ] **Step 2: Replace BlockButton component styling**

```tsx
// OLD:
className={cn(
  "w-full rounded-[28px] border p-5 text-left transition",
  active
    ? "border-blue-700 bg-blue-700 text-white shadow-[0_20px_70px_rgba(37,99,235,0.18)]"
    : "border-sky-100 bg-[linear-gradient(180deg,#fcfeff_0%,#f7fbff_100%)] text-slate-700 hover:border-blue-200 hover:bg-white",
)}
// NEW:
className={cn(
  "w-full rounded-[28px] p-5 text-left transition shadow-[inset_0_1px_0_rgba(255,255,255,0.6)]",
  active
    ? "bg-[var(--color-navy)] text-white shadow-[0_8px_24px_rgba(15,26,46,0.15)]"
    : "bg-[var(--color-bg)] text-[var(--color-text-primary)] hover:shadow-[0_4px_12px_rgba(15,26,46,0.06)]",
)}
```

- [ ] **Step 3: Replace label text colors**

```tsx
// OLD:
className="text-[11px] uppercase tracking-[0.28em] text-sky-600"
// NEW:
className="text-[11px] uppercase tracking-[0.28em] text-[var(--color-text-muted)]"

// OLD:
className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-sm text-slate-500"
// NEW:
className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-sm text-[var(--color-text-secondary)]"
```

- [ ] **Step 4: Run dev server to verify**

Check http://localhost:3000 in edit mode (after generating a resume):
- Preview has warm surface background, no blue
- Block buttons show navy styling for active state
- Text labels in muted warm gray

- [ ] **Step 5: Commit**

```bash
git add apps/resume-generator/src/components/resume-preview.tsx
git commit -m "feat(preview): restyle with Future Academic palette"
```
