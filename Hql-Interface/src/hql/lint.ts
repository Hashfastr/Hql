import type { Diagnostic } from '@codemirror/lint'
import type { EditorView } from '@codemirror/view'
import { parseWithErrors } from './parse.ts'
import { codePointBoundaries, codeUnitOffset } from './positions.ts'

// Full lexer+parser pass per lint; the linter()'s delay option (index.ts) is
// the only debounce and has proven sufficient — don't add more machinery.
export function hqlLintSource(view: EditorView): Diagnostic[] {
  const doc = view.state.doc
  const text = doc.toString()
  if (!text.trim()) return []

  // Never let a parser exception escape into CM's update cycle — a broken
  // lint pass must degrade to "no diagnostics", not a broken editor.
  try {
    return parseWithErrors(text).errors.map((err) => {
      const line = doc.line(Math.max(1, Math.min(err.line, doc.lines)))
      const column = codeUnitOffset(codePointBoundaries(line.text), err.column)
      const from = Math.min(line.from + column, line.to)
      const to = Math.max(from, Math.min(from + Math.max(err.length, 1), doc.length))
      return { from, to, severity: 'error' as const, message: err.message }
    })
  } catch {
    return []
  }
}
