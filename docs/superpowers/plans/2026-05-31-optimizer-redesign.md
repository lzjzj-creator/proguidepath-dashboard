# Resume Optimizer Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restyle the entire resume-optimizer Vue 3 app (4462-line single-file component) with the Future Academic design system: warm paper background, pill-shaped containers, terracotta accents, noise texture.

**Architecture:** Single Vue 3 SFC (`ResumeUpload.vue`) containing all pages. Redesign is CSS-only — no template/JS changes. New CSS custom properties replace hardcoded colors. All containers get large border-radius (>20px), borders replaced with shadows, inputs pill-ified.

**Tech Stack:** Vue 3, Vite 6, CSS custom properties

---

### Task 1: Add design system CSS variables and background

**Files:**
- Modify: `apps/resume-optimizer/src/components/ResumeUpload.vue` (style section)

- [ ] **Step 1: Read the current style section**

Run: `grep -n "<style" apps/resume-optimizer/src/components/ResumeUpload.vue`
Read from the `<style>` line to end of file to understand current CSS.

- [ ] **Step 2: Replace scoped style with CSS custom properties**

Add at the very beginning of the `<style scoped>` block (before any existing rules — or replace the first few lines):

```css
/* ===== Design Tokens ===== */
.app-shell {
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
  --color-bg-warm: #f7f5f0;
  --font-display: 'Bricolage Grotesque', 'PingFang SC', sans-serif;
  --font-body: 'Outfit', 'PingFang SC', 'Noto Sans SC', sans-serif;
}
```

- [ ] **Step 3: Update the app-shell background**

Find `.app-shell` rule and update:

```css
.app-shell {
  background: var(--color-bg);
  color: var(--color-text-primary);
  font-family: var(--font-body);
  min-height: 100vh;
  display: grid;
  grid-template-columns: 240px 1fr;
  position: relative;
}
```

Add noise texture overlay as a pseudo-element on `.app-shell`:

```css
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
```

- [ ] **Step 4: Restyle the sidebar**

Find the `.sidebar` rule and update to use pill/soft styling:

```css
.sidebar {
  background: var(--color-surface);
  padding: 1.75rem 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  position: sticky;
  top: 0;
  height: 100vh;
  z-index: 2;
  box-shadow: 4px 0 20px rgba(15,26,46,0.04);
}

.brand {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.brand span:first-child {
  width: 38px;
  height: 38px;
  border-radius: 12px;
  background: var(--color-navy);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 0.875rem;
}

.brand div strong {
  display: block;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-navy);
}

.brand div small {
  font-size: 0.75rem;
  color: var(--color-text-muted);
}
```

Update navigation buttons:

```css
.nav-list {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.nav-list button {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  width: 100%;
  padding: 0.75rem 1rem;
  border-radius: 16px;
  border: none;
  background: transparent;
  font-family: var(--font-body);
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: background 150ms, color 150ms;
  text-align: left;
}

.nav-list button:hover {
  background: rgba(196, 100, 74, 0.06);
  color: var(--color-terracotta);
}

.nav-list button.active {
  background: var(--color-terracotta);
  color: #fff;
}
```

- [ ] **Step 5: Restyle topbar**

Find the `.topbar` rule and update:

```css
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
  margin-bottom: 2rem;
}

.topbar .eyebrow {
  font-family: 'Outfit', monospace;
  font-size: 0.6875rem;
  text-transform: uppercase;
  letter-spacing: 0.2em;
  color: var(--color-text-muted);
  margin-bottom: 0.25rem;
}

.topbar h1 {
  font-family: var(--font-display);
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--color-navy);
}

.topbar p {
  color: var(--color-text-secondary);
  font-size: 0.875rem;
}
```

- [ ] **Step 6: Restyle panels and metric cards**

Find all `.panel` rules and update:

```css
.panel {
  background: var(--color-surface);
  border-radius: 24px;
  padding: 1.5rem;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.6), 0 2px 8px rgba(15,26,46,0.06);
  border: none;
}

.panel h2 {
  font-family: var(--font-display);
  font-size: 1.125rem;
  font-weight: 700;
  color: var(--color-navy);
  margin-bottom: 1rem;
}

.metric-card {
  background: var(--color-surface);
  border-radius: 24px;
  padding: 1.5rem;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.6), 0 2px 8px rgba(15,26,46,0.06);
  border: none;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.metric-card span {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--color-text-muted);
}

.metric-card strong {
  font-family: var(--font-display);
  font-size: 2rem;
  font-weight: 700;
  color: var(--color-navy);
}

.metric-card small {
  font-size: 0.75rem;
  color: var(--color-text-muted);
}
```

- [ ] **Step 7: Restyle buttons**

Find `.primary-btn` and `.secondary-btn`:

```css
.primary-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.75rem 1.75rem;
  border-radius: 999px;
  border: none;
  font-family: var(--font-body);
  font-size: 0.875rem;
  font-weight: 600;
  color: #fff;
  background: var(--color-terracotta);
  cursor: pointer;
  transition: background 200ms, transform 200ms, box-shadow 200ms;
  box-shadow: 0 4px 12px rgba(196, 100, 74, 0.2);
}

.primary-btn:hover:not(:disabled) {
  background: var(--color-terracotta-light);
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(196, 100, 74, 0.25);
}

.primary-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.secondary-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.75rem 1.75rem;
  border-radius: 999px;
  border: 1.5px solid var(--color-border);
  background: transparent;
  font-family: var(--font-body);
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: border-color 200ms, color 200ms, background 200ms;
}

.secondary-btn:hover:not(:disabled) {
  border-color: var(--color-terracotta);
  color: var(--color-terracotta);
  background: rgba(196, 100, 74, 0.04);
}

.secondary-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
```

- [ ] **Step 8: Restyle form fields**

Find the `.field` rules (these are used extensively throughout the component templates). They are NOT scoped since the template uses `<label class="field">`. Since CSS is scoped in Vue SFC, these will work. Update:

```css
.field {
  display: grid;
  gap: 0.5rem;
}

.field span {
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: var(--color-text-secondary);
}

.field input,
.field textarea,
.field select {
  width: 100%;
  border-radius: 20px;
  border: none;
  background: var(--color-bg);
  padding: 0.875rem 1.125rem;
  color: var(--color-text-primary);
  font-family: var(--font-body);
  font-size: 0.875rem;
  outline: none;
  box-shadow: inset 0 1px 3px rgba(15,26,46,0.06);
  transition: box-shadow 200ms, background 200ms;
}

.field textarea {
  min-height: 7rem;
  resize: vertical;
}

.field input:focus,
.field textarea:focus,
.field select:focus {
  box-shadow: 0 0 0 3px rgba(196, 100, 74, 0.12), inset 0 1px 3px rgba(15,26,46,0.06);
  background: var(--color-surface);
}
```

- [ ] **Step 9: Restyle upload zone, journey cards, comparison cards**

Find the `.upload-zone` rule:

```css
.upload-zone {
  border-radius: 28px;
  border: 2px dashed var(--color-border);
  padding: 2.5rem 2rem;
  text-align: center;
  background: var(--color-bg);
  cursor: pointer;
  transition: border-color 200ms, background 200ms;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}

.upload-zone:hover,
.upload-zone.dragging {
  border-color: var(--color-terracotta);
  background: rgba(196, 100, 74, 0.04);
}

.upload-zone.success {
  border-color: var(--color-teal);
  background: rgba(45, 125, 122, 0.04);
}

.upload-zone strong {
  font-size: 1rem;
  color: var(--color-navy);
}

.upload-zone span {
  font-size: 0.8125rem;
  color: var(--color-text-muted);
}
```

Find journey cards:

```css
.journey-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 0.75rem;
}

.journey-card {
  background: var(--color-bg);
  border-radius: 20px;
  padding: 1.25rem;
  border: none;
  cursor: pointer;
  text-align: left;
  font-family: var(--font-body);
  transition: box-shadow 200ms, transform 200ms;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.6);
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.journey-card:hover {
  box-shadow: 0 4px 16px rgba(15,26,46,0.08);
  transform: translateY(-1px);
}

.journey-card--primary {
  background: rgba(196, 100, 74, 0.08);
}
```

Update comparison/optimize cards:

```css
.compare-card {
  background: var(--color-surface);
  border-radius: 24px;
  padding: 1.5rem;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.6), 0 2px 8px rgba(15,26,46,0.06);
  margin-bottom: 1rem;
}
```

- [ ] **Step 10: Restyle timeline steps and status pills**

```css
.timeline {
  display: flex;
  gap: 0.5rem;
  margin: 1rem 0;
}

.timeline-step {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.75rem;
  border-radius: 999px;
  font-size: 0.75rem;
  background: var(--color-bg);
  color: var(--color-text-muted);
}

.timeline-step.done {
  background: rgba(45, 125, 122, 0.1);
  color: var(--color-teal);
}

.timeline-step.active {
  background: rgba(196, 100, 74, 0.1);
  color: var(--color-terracotta);
}

.status-pill {
  display: inline-flex;
  align-items: center;
  padding: 0.25rem 0.75rem;
  border-radius: 999px;
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.status-pill--success {
  background: rgba(45, 125, 122, 0.1);
  color: var(--color-teal);
}

.status-pill--muted {
  background: var(--color-bg);
  color: var(--color-text-muted);
}
```

- [ ] **Step 11: Run dev server to verify**

The dev server should be running at http://localhost:5173. Check:
- Warm paper background with subtle noise texture
- Sidebar is pill-styled with terracotta active state
- All panels have 24px border-radius, no visible borders
- Buttons are pill-shaped (999px radius)
- Form inputs have 20px radius with no borders
- No hard rectangles anywhere

Run: Open http://localhost:5173 in browser
Expected: The full optimizer app with new warm styling, all containers pill-shaped

- [ ] **Step 12: Commit**

```bash
git add apps/resume-optimizer/src/components/ResumeUpload.vue
git commit -m "feat: restyle resume optimizer with Future Academic design system"
```
