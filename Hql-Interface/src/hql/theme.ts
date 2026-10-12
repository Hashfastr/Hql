import { EditorView } from '@codemirror/view'
import type { Extension } from '@codemirror/state'

// This is the ONLY file in src/hql/ that may be imported eagerly: everything
// else in this directory pulls in the ~1 MB generated parser and must stay
// behind Editor.tsx's dynamic import('../hql') so it lands in a lazy chunk.
// Keep this file free of imports from ./parse, ./generated, antlr4ng, etc.

// Gruvbox, mirroring tailwind.config.js
const dark = {
  bg: '#282828',
  bg1: '#3c3836',
  bg2: '#504945',
  fg: '#ebdbb2',
  gray: '#928374',
  red: '#fb4934',
  green: '#b8bb26',
  yellow: '#fabd2f',
  blue: '#83a598',
  purple: '#d3869b',
  aqua: '#8ec07c',
  orange: '#fe8019',
}
const light = {
  bg: '#fbf1c7',
  bg1: '#ebdbb2',
  bg2: '#d5c4a1',
  fg: '#3c3836',
  gray: '#7c6f64',
  red: '#cc241d',
  green: '#98971a',
  yellow: '#d79921',
  blue: '#458588',
  purple: '#b16286',
  aqua: '#689d6a',
  orange: '#d65d0e',
}

export function gruvboxTheme(isDark: boolean): Extension {
  const c = isDark ? dark : light
  return EditorView.theme(
    {
      '&': { backgroundColor: c.bg, color: c.fg, height: '100%' },
      '.cm-content': { caretColor: c.fg, fontFamily: 'monospace', fontSize: '14px' },
      '.cm-cursor, .cm-dropCursor': { borderLeftColor: c.fg },
      '&.cm-focused': { outline: 'none' },
      '&.cm-focused > .cm-scroller > .cm-selectionLayer .cm-selectionBackground, ::selection': {
        backgroundColor: c.bg2,
      },
      '.cm-selectionBackground': { backgroundColor: c.bg2 },
      '.cm-activeLine': { backgroundColor: c.bg1 + '80' },
      '.cm-gutters': { backgroundColor: c.bg, color: c.gray, borderRight: `1px solid ${c.bg1}` },
      '.cm-activeLineGutter': { backgroundColor: c.bg1 },
      '.cm-tooltip': { backgroundColor: c.bg1, color: c.fg, border: `1px solid ${c.bg2}` },
      '.cm-tooltip-autocomplete ul li[aria-selected]': { backgroundColor: c.bg2, color: c.fg },
      // Token classes applied by the hql highlighter
      '.hql-keyword': { color: c.red },
      '.hql-type': { color: c.yellow },
      '.hql-literal': { color: c.purple },
      '.hql-string': { color: c.green },
      '.hql-comment': { color: c.gray },
      '.hql-operator': { color: c.aqua },
      '.hql-identifier': { color: c.fg },
      '.hql-error': { textDecoration: `underline wavy ${c.red}` },
    },
    { dark: isDark },
  )
}
