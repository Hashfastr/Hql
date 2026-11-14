# Hql-Interface — Design Notes

Reference notes for the July 2026 rewrite of the web interface. Read this before
making structural changes; it records the decisions and the non-obvious constraints
that shaped them.

## What this is

A SIEM-style query interface in the spirit of Azure Data Explorer: multiline
grammar-aware editor on top, results below, collapsible detections panel on the
right. Intentionally minimal: no auth (deferred to a dedicated audited session),
no routing, no state library, no table library, no JSON-viewer dependency.

## Stack

- **Vite + React 18 + TypeScript + Tailwind** (Gruvbox palette in
  `tailwind.config.js`, `darkMode: 'class'`)
- **CodeMirror 6** (chosen over Monaco for bundle weight; the six
  `@codemirror/*` packages are used directly — deliberately not the
  `codemirror` meta-package or a React wrapper)
- **antlr4ng** runtime + **antlr4-c3** completion engine + **antlr-ng**
  (dev-only) for parser generation

## Grammar pipeline

- `npm run gen:parser` regenerates `src/hql/generated/HqlLexer.ts` +
  `HqlParser.ts` from `../Hql/Parser/grammar/Hql.g4` (+ `HqlTokens.g4` via
  `--lib`). Rerun whenever the .g4 files change.
- **antlr-ng is pure TypeScript — no Java needed.** It implements ANTLR
  4.13.2 semantics, matching the grammar's era. Fallback if it ever breaks:
  `antlr4ng-cli` (Java jar), which emits code for the same antlr4ng runtime.
- Generated files are **committed** and get `// @ts-nocheck` prepended by the
  npm script (they trip `noUnusedLocals`; never hand-edit them, fix the script).
  They're also excluded in `eslint.config.js`.
- The grammar contains no embedded actions or predicates (verified), so it's
  target-agnostic. Keep it that way or TS generation breaks.
- `tsconfig` must stay at **ES2022+**: antlr4ng uses static class-init blocks.
- Intra-project imports use explicit `.ts` extensions
  (`allowImportingTsExtensions`). This keeps modules runnable under plain
  `node --input-type=module` for quick smoke tests (Node 22 type-stripping),
  which is how the parser/completion logic was verified headlessly.

## Editor architecture (`src/hql/`, `src/components/Editor.tsx`)

The ~1 MB parser lives in a **lazy chunk**: `Editor.tsx` does a dynamic
`import('../hql')` and swaps the extensions into a `Compartment` when the
chunk lands. The app shell paints immediately with a plain editor that
upgrades in place. Don't import anything from `src/hql/index.ts`,
`highlight.ts`, `lint.ts`, `complete.ts`, or `generated/` eagerly —
`src/hql/theme.ts` is the only file in that directory safe to import eagerly
(it depends only on @codemirror/view).

- **Highlighting** (`highlight.ts`): no Lezer grammar, no StreamLanguage. A
  ViewPlugin re-lexes the whole document with the real `HqlLexer`
  (`getAllTokens()` includes the hidden channel, so comments highlight) and
  emits `Decoration.mark` spans. Token → category is derived from the
  generated vocabulary at module init (symbolic names ending in `LITERAL`,
  `COMMENT`/`MULTILINECOMMENT`, alphabetic literal names = keywords, a
  hardcoded set of type words, everything else punctuation/operator), so new
  grammar keywords are picked up automatically on regeneration.
- **Linting** (`lint.ts`): `@codemirror/lint` `linter()` with a collecting
  error listener on lexer+parser, `parser.top()`, ANTLR line/col mapped to doc
  offsets. The linter's built-in delay is the debounce.
- **Completion** (`complete.ts`): antlr4-c3 `CodeCompletionCore` against a
  fresh parse; ignored-token set (punctuation, literals, identifiers) also
  derived from the vocabulary. `validFor: /^[\w-]*$/` makes CM filter by
  prefix client-side instead of re-invoking the (150 ms cold / fast warm)
  source per keystroke. `preferredRules` is intentionally empty — that's the
  seam for column/table-name completion from run schemas later.
- **Main thread on purpose**: queries are small; `parse.ts` is the single
  entry point so moving behind a web worker is a mechanical refactor if ever
  needed.
- **Editor state quirks**: `EditorState`s are cached per tab id
  (module-level map) so undo history survives tab switches. Because cached
  states keep their original extension closures, onChange/onRun callbacks
  live in a module-level `live` object — safe because exactly one Editor
  mounts at a time. The theme and hql Compartments are module-level for the
  same reason. If you ever render two editors simultaneously, this needs
  rework.
- **NEVER sync the editor document from the `value` prop.** While the user
  types, the CM document is the source of truth and `tab.query` is only its
  state echo. `useEffect` runs post-paint, so a value-keyed sync effect races
  real input (held backspace + lint-parse jank) and silently rewrites text the
  user just edited — this shipped once as a serious bug. External writes
  (Init HaC, Sigma convert) must go through the `replaceQuery` action, which
  bumps `tab.editRev`; the editor syncs only on `editRev` changes. Parser
  exceptions in lint/completion sources are caught and degrade to
  no-diagnostics/no-completions for the same "never break the editor" reason.
  `window.__hqlEditorView` exposes the mounted view for browser-driven tests.

## State model (`src/state/store.tsx`)

One context + `useReducer`. Key invariants:

- **Global run lock**: any tab with `run.status === 'running'` disables Run
  everywhere and shows lain.gif (spec: cannot start a query while one runs).
- **Stop = stop waiting.** The backend has no cancel endpoint; Stop aborts the
  client-side `AbortController` (see `hooks/useRunner.ts`) and marks the tab
  idle. If the backend grows a cancel API, wire it there.
- **The right panel is modal**: `rightPanel.mode` is either `detections` or a
  `row` inspector. Expanding a row replaces the detections list (per spec) and
  force-uncollapses the panel; Esc/×/re-run/tab-close restores detections
  (`resetInspectorFor` in the reducer).
- **Resizable regions share one hook** (`hooks/useDragResize.ts`): the right
  panel (drag its left edge; width per mode under
  `hql-interface:inspector-width` / `hql-interface:detections-width`) and the
  editor/results splitter in `App.tsx` (drag the divider; editor height under
  `hql-interface:editor-height`). Pointer-capture drag, clamped to
  [min, fraction-of-window], sizes stored under their own localStorage keys —
  outside the versioned persist blob on purpose, so a schema bump doesn't
  reset panel layout. Add any future resizable region through this hook.
- **Persistence** (`lib/persist.ts`): debounced localStorage under
  `hql-interface:v1` — theme, collapse, active tab, tab titles+queries.
  Results are deliberately never persisted. Bump the key version if the shape
  changes.

## Results rendering

- Backend result shape is inherently multi-table:
  `results.data = {TableName: [rows]}`, `results.schema = {TableName: {field: type}}`.
  Table tabs come straight from `Object.keys(data)`.
- **Single-path flattening** (`lib/columns.ts`, pure + node-testable): a
  column whose sampled values (≤50 rows) are all single-key objects with the
  same key collapses recursively; the header becomes the dot path
  (`winlog.computer_name`) and cells render the leaf. Detection is
  data-driven, not schema-driven, because the schema just says `dynamic`.
- Other nested cells render `JSON.stringify` truncated to ~120 chars; the full
  value is reachable via the row inspector or right-click copy.
- Hand-rolled `<table>` — no tanstack. Needed features (sticky header, custom
  cells, external expansion target, context menu) are trivial without it, and
  its expansion model fights the replace-the-sidebar requirement.
- 500-row render cap with "Load more" instead of virtualization.
- Context menu: portal + `preventDefault` on `contextmenu`; copies use
  `navigator.clipboard` (fine on localhost = secure context; silently fails
  on plain-http non-localhost origins).

## Backend contract gotchas (verified against `Hql/Apiserver/__init__.py`)

- `GET /api/hql/runs/{id}` returns **`run_id`**, not `id`
  (`Threading.py` `to_dict`). Types in `src/types/index.ts` encode this.
- `POST /api/detections` takes a **raw text body** (`text/plain`), not JSON.
- Failed runs carry the Python traceback in `str_out`; the UI shows it
  verbatim in a red `<pre>`.
- Polling is 1 s interval, AbortSignal-driven, 10-minute soft ceiling
  (the old UI's 60-attempt cap broke long retro hunts).
- The backend serves `dist/index.html` at `/` and mounts **only** `/assets` —
  every asset must go through the bundler (`import lainGif from
  '../../lain.gif'`), never absolute URLs. The favicon is an inline data URI
  for the same reason.
- **Time windows** (`lib/timeRange.ts`, `components/TimeRangePicker.tsx`):
  each tab carries a `timeRange` — `default` (send nothing: the HaC
  schedule's interval up to now), `lookback` (`{lookback: '7d'}`, parsed by
  `parse_timespan` like `ago()`), or `absolute` (`{start, end}` as UTC ISO;
  the backend converts zoned datetimes to its local naive time, Hql's
  convention). Bad values 400 with a readable `detail`. Only queries with
  HaC are time-bounded (the compiler bounds via `hac.get_timerange()`; Sigma
  rules always generate HaC), so the window is a no-op for plain Hql. Run
  dicts carry `timerange: {start, end}` (server-local naive ISO, shown
  verbatim in the results status line) only when HaC bounded the run.
  `timeRange` is persisted per tab as an optional field inside the v1 blob
  (validated by `parseTimeRange` on load) — no version bump, so saved tabs
  survive.
- `vite.config.ts`: dev server on **5173** proxying `/api` → 8080. (It used
  to be 8080→8080, which proxied to itself and collided with the backend.)

## Verification setup

- Production check: `npm run build`, then run the backend
  (`uv run python -m Hql -eng -d ./examples/interface` from the repo root)
  and open `:8080`. Dev loop: backend up + `npm run dev` on `:5173`.
- There's a mock backend + Playwright drive script from the rewrite
  verification in the session scratchpad pattern: a ~150-line node http
  server implementing the API contract (including the 3-poll completion
  delay and a `FAIL` keyword to trigger the failure path) plus a headless
  Chromium script asserting highlight/lint/autocomplete/run-lock/flattening/
  inspector/clipboard/persistence. If regressions become a worry, recreate
  that pair as committed `test/` scripts — the API surface is small.

## Known limits / future seams

- Autocomplete offers keywords only; column/table suggestions want
  `preferredRules` + schema data from prior runs (seam noted in
  `complete.ts`).
- No query cancel on the backend; Stop is client-side only.
- SchemaExplorer from the old UI was dropped (not in spec); `GET /api/schema`
  is unused.
- Wide tables rely on horizontal scroll; no column resize/pin.
- The live backend returns `num_results: 0` for plain (non-detection) runs
  even when rows come back, so the status line falls back to summing row
  counts across tables (`ResultsPane.tsx`). Per-tab badges are always raw row
  counts.
