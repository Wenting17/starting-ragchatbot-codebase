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
