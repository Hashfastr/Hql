import { RangeSetBuilder } from '@codemirror/state'
import {
  Decoration,
  ViewPlugin,
  type DecorationSet,
  type EditorView,
  type ViewUpdate,
} from '@codemirror/view'
import { Token } from 'antlr4ng'
import { createLexer, lexAll } from './parse.ts'
import { codePointBoundaries, codeUnitOffset } from './positions.ts'

const TYPE_WORDS = new Set([
  'bool', 'boolean', 'date', 'datetime', 'decimal', 'double', 'dynamic', 'float',
  'guid', 'int', 'int8', 'int16', 'int32', 'int64', 'long', 'real', 'string',
  'time', 'timespan', 'uint', 'uint8', 'uint16', 'uint32', 'uint64', 'ulong',
  'uniqueid', 'ip4', 'ip6',
])

type Category = 'keyword' | 'type' | 'string' | 'literal' | 'comment' | 'operator'

// Highlighting runs the real HqlLexer over the whole document and marks each
// token with a CSS class (colors live in theme.ts). Chosen over a Lezer port
// (1600-line grammar, would drift) and StreamLanguage (line-oriented; breaks
// on multi-line strings/comments). getAllTokens() includes the hidden channel,
// which is what makes comments highlight.

// Derive token categories from the generated vocabulary once, so keywords
// added to the grammar are picked up automatically on regeneration.
const categories: Map<number, Category> = (() => {
  const map = new Map<number, Category>()
  const vocab = createLexer('').vocabulary
  for (let t = 1; t <= vocab.maxTokenType; t++) {
    const symbolic = vocab.getSymbolicName(t) ?? ''
    const literal = vocab.getLiteralName(t)?.replace(/^'|'$/g, '')

    if (symbolic === 'COMMENT' || symbolic === 'MULTILINECOMMENT') {
      map.set(t, 'comment')
    } else if (symbolic === 'WHITESPACE' || symbolic === 'IDENTIFIER') {
      continue
    } else if (symbolic.includes('STRINGLITERAL')) {
      map.set(t, 'string')
    } else if (symbolic.endsWith('LITERAL')) {
      map.set(t, 'literal')
    } else if (literal && /^[a-zA-Z]/.test(literal)) {
      map.set(t, TYPE_WORDS.has(literal) ? 'type' : 'keyword')
    } else if (literal) {
      map.set(t, 'operator')
    }
  }
  return map
})()

function buildDecorations(view: EditorView): DecorationSet {
  const builder = new RangeSetBuilder<Decoration>()
  const doc = view.state.doc.toString()
  const boundaries = codePointBoundaries(doc)
  let tokens: Token[]

  try {
    tokens = lexAll(doc)
  } catch {
    // Highlighting is cosmetic. An incomplete token must never interrupt a
    // CodeMirror update and leave its state ahead of the rendered document.
    return Decoration.none
  }

  for (const token of tokens) {
    if (token.type === Token.EOF) break
    const cat = categories.get(token.type)
    if (!cat) continue
    const from = codeUnitOffset(boundaries, token.start)
    const to = codeUnitOffset(boundaries, token.stop + 1)
    if (to <= from) continue
    builder.add(from, to, Decoration.mark({ class: `hql-${cat}` }))
  }
  return builder.finish()
}

export const hqlHighlighter = ViewPlugin.fromClass(
  class {
    decorations: DecorationSet

    constructor(view: EditorView) {
      this.decorations = buildDecorations(view)
    }

    update(update: ViewUpdate) {
      if (update.docChanged) this.decorations = buildDecorations(update.view)
    }
  },
  { decorations: (v) => v.decorations },
)
