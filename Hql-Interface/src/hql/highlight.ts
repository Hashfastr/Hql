import { RangeSetBuilder } from '@codemirror/state'
import {
  Decoration,
  ViewPlugin,
  type DecorationSet,
  type EditorView,
  type ViewUpdate,
} from '@codemirror/view'
import { Token } from 'antlr4ng'
import { tokenCategory, type Category } from './categories.ts'
import { createLexer, lexAll } from './parse.ts'
import { codePointBoundaries, codeUnitOffset, lineRanges } from './positions.ts'

// Highlighting runs the real HqlLexer over the whole document and marks each
// token with a CSS class (colors live in theme.ts). Chosen over a Lezer port
// (1600-line grammar, would drift) and StreamLanguage (line-oriented; breaks
// on multi-line strings/comments). Multi-line marks are split at every line
// boundary below so they cannot disturb CodeMirror's blank-line rendering.

// Derive token categories from the generated vocabulary once, so keywords
// added to the grammar are picked up automatically on regeneration.
const categories: Map<number, Category> = (() => {
  const map = new Map<number, Category>()
  const vocab = createLexer('').vocabulary
  for (let t = 1; t <= vocab.maxTokenType; t++) {
    const symbolic = vocab.getSymbolicName(t) ?? ''
    const literal = vocab.getLiteralName(t)?.replace(/^'|'$/g, '')
    const category = tokenCategory(symbolic, literal)
    if (category) map.set(t, category)
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
    const mark = Decoration.mark({ class: `hql-${cat}` })
    for (const range of lineRanges(doc, from, to)) {
      builder.add(range.from, range.to, mark)
    }
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
