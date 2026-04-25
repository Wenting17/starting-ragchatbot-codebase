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
