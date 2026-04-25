# Frontend Changes

## Light/Dark Theme Toggle

### Summary
Added a light theme variant and a toggle button that lets users switch between dark (default) and light modes. The preference is persisted via `localStorage` so it survives page reloads.

---

### Files Modified

#### `frontend/style.css`
- Added `--code-bg` CSS variable to `:root` so inline/block code background adapts to the active theme.
- Added a `[data-theme="light"]` block that overrides all color variables with light-mode equivalents:
  - Background: `#f8fafc` (near-white)
  - Surface: `#ffffff`
  - Text primary: `#0f172a` (near-black, WCAG AA compliant against white)
  - Text secondary: `#64748b`
  - Border: `#e2e8f0`
  - Primary/hover blues are slightly deeper (`#1d4ed8` / `#1e40af`) to maintain contrast on light backgrounds.
- Added a `transition` rule on structural elements (`body`, `.sidebar`, `.chat-messages`, inputs, buttons, etc.) so color changes animate smoothly over `0.3s ease` when the theme switches.
- Replaced hardcoded `rgba(0,0,0,0.2)` on `.message-content code` and `pre` with `var(--code-bg)`.
- Added `.theme-toggle` button styles:
  - Fixed position, top-right corner (`top: 1rem; right: 1rem; z-index: 1000`)
  - 44×44 px circle (meets WCAG minimum touch target size)
  - Uses `var(--surface)`, `var(--border-color)`, and `var(--shadow)` so it adapts to both themes automatically.
  - Sun and moon SVGs are stacked (`position: absolute`) and cross-fade with a rotate+opacity transition when the theme changes.
  - `focus-visible` ring for keyboard navigation.

#### `frontend/index.html`
- Added the `<button class="theme-toggle" id="themeToggle">` element directly inside `<body>`, before `.container`, so it sits above all other content at a fixed position.
- Button contains two inline SVGs (`icon-sun`, `icon-moon`) with `aria-hidden="true"` so screen readers rely on the button's `aria-label` instead.
- Initial `aria-label` is "Switch to light mode" (updated dynamically by JS when the theme changes).

#### `frontend/script.js`
- Added `themeToggle` to the DOM element cache.
- Added `initThemeToggle()` called during `DOMContentLoaded`:
  - Reads `localStorage.getItem('theme')`, defaulting to `'dark'`.
  - Calls `applyTheme()` on load (without saving) to restore the user's preference.
  - Attaches a `click` listener and a `keydown` listener (`Enter`/`Space`) for full keyboard navigability.
- Added `applyTheme(theme, save)` helper:
  - Sets or removes `data-theme="light"` on `document.documentElement` (the `<html>` tag, matching the CSS selector).
  - Updates `aria-label` to accurately describe the action that clicking will perform.
  - Writes to `localStorage` only when `save` is `true` (skipped on the initial restore to avoid redundant writes).

---

# Frontend Code Quality Changes

## What was added

### Prettier (automatic code formatter)

Prettier is the frontend equivalent of Black — it enforces a single, opinionated style so all developers produce identical output regardless of editor settings.

| File | Purpose |
|---|---|
| `frontend/package.json` | Declares `prettier` as a dev dependency; defines `format`, `format:check`, and `quality` npm scripts |
| `frontend/.prettierrc` | Formatting rules: 4-space indent, single quotes, semicolons, 100-char line width, LF line endings |
| `frontend/.prettierignore` | Excludes `node_modules/` from formatting |

### Dev quality script

| File | Purpose |
|---|---|
| `frontend-quality.sh` | Root-level shell script to run Prettier in check or fix mode |

## How to use

**Check formatting (CI / pre-commit)**
```bash
./frontend-quality.sh
# or from the frontend/ directory:
npm run format:check
```

**Auto-fix formatting**
```bash
./frontend-quality.sh --fix
# or from the frontend/ directory:
npm run format
```

**First-time setup** (installs Prettier locally)
```bash
cd frontend && npm install
```

## Formatting applied to existing files

All three frontend source files were reformatted to match the Prettier config, so `npm run format:check` passes with zero diff on a clean checkout.

### `frontend/script.js`
- Removed stray blank lines (between event-listener registrations, after closing braces)
- Arrow-function parameters wrapped in parentheses consistently: `(e) =>`, `(s) =>`, `(title) =>`
- Multi-line method chains (`.map(...).join(...)`) broken onto separate lines
- Trailing commas added to multi-line object/array literals and function argument lists
- `addMessage(...)` call in `createNewSession` broken into a multi-line call to stay within print width

### `frontend/index.html`
- Doctype lowercased to `<!doctype html>` (Prettier standard)
- Void elements self-closed: `<meta ... />`, `<link ... />`, `<input ... />`
- Long `data-question` attributes and multi-attribute elements broken onto separate lines with consistent 4-space indentation
- SVG attributes each placed on their own line
- `<script>` tags moved inside `<body>` closing, indented consistently

### `frontend/style.css`
- Multi-selector rules each on their own line (`*,\n*::before,\n*::after`)
- Single-property shorthand heading rules expanded (`.message-content h1 { font-size: 1.5rem; }` → block form)
- `@keyframes bounce` selector list broken: `0%,\n80%,\n100%`
- Removed inline comment `/* Remove max-height to show all titles without scrolling */` (tracked in git history; no value at read time)
- Consistent blank lines between rule blocks throughout
