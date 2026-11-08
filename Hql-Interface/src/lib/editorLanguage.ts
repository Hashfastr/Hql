export type EditorLanguage = 'hql' | 'yaml'

// Only the head of the document is inspected: a Sigma rule declares its
// top-level keys up front, and the check runs on (debounced) edits.
const SCAN_CHARS = 4096
const SCAN_LINES = 40

const TOP_LEVEL_KEY = /^([A-Za-z_][\w.-]*):(?:\s|$)/
// Keys that only a Sigma rule would put at column 0; one is conclusive
const SIGMA_KEYS = new Set(['logsource', 'detection', 'falsepositives', 'correlation'])

/**
 * Cheap heuristic for Sigma/YAML pasted into the query editor. A tab named
 * *.yml / *.yaml is always YAML. Otherwise the first significant line must be
 * a document marker (`---`), a directive (`%YAML`), or a column-0 `key:`, and
 * the head must hold two such keys or one Sigma-specific key. Hql queries
 * start with a table/expression and only use `name: type` inside parens or
 * after keywords, so they never satisfy this.
 */
export function detectEditorLanguage(text: string, title = ''): EditorLanguage {
  if (/\.ya?ml$/i.test(title.trim())) return 'yaml'

  const head = text.slice(0, SCAN_CHARS)
  let keys = 0
  let seenSignificant = false
  let start = 0
  for (let n = 0; n < SCAN_LINES && start <= head.length; n++) {
    let end = head.indexOf('\n', start)
    if (end === -1) end = head.length
    const line = head.slice(start, end).replace(/\r$/, '')
    start = end + 1

    // '#' is a YAML comment and not valid Hql, so it is safe to skip
    if (!line.trim() || line.startsWith('#')) continue

    const key = TOP_LEVEL_KEY.exec(line)
    if (!seenSignificant) {
      seenSignificant = true
      if (/^---\s*$/.test(line) || line.startsWith('%YAML')) return 'yaml'
      if (!key) return 'hql'
    }
    if (key) {
      if (SIGMA_KEYS.has(key[1])) return 'yaml'
      if (++keys >= 2) return 'yaml'
    }
  }
  return 'hql'
}
