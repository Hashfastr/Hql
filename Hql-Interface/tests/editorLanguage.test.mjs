import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'
import ts from 'typescript'

const source = await readFile(new URL('../src/lib/editorLanguage.ts', import.meta.url), 'utf8')
const javascript = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ES2022, target: ts.ScriptTarget.ES2022 },
}).outputText
const { detectEditorLanguage } = await import(
  `data:text/javascript;base64,${Buffer.from(javascript).toString('base64')}`
)

const sigma = `title: Suspicious PowerShell
id: 1234
logsource:
  product: windows
detection:
  selection:
    Image|endswith: '\\\\powershell.exe'
  condition: selection
level: high
`

test('detects Sigma rules and YAML documents', () => {
  assert.equal(detectEditorLanguage(sigma), 'yaml')
  assert.equal(detectEditorLanguage('---\nfoo: bar\n'), 'yaml')
  assert.equal(detectEditorLanguage('# comment\r\n\r\ntitle: x\r\nstatus: test\r\n'), 'yaml')
  assert.equal(detectEditorLanguage('detection:\n'), 'yaml')
})

test('keeps Hql queries as Hql', () => {
  assert.equal(detectEditorLanguage(''), 'hql')
  assert.equal(detectEditorLanguage('title: x'), 'hql')
  assert.equal(
    detectEditorLanguage('// title: x\ndatabase("tf").index\n| where title: "x"\n| take 10'),
    'hql',
  )
  assert.equal(detectEditorLanguage('let f = (a: string) { a };\nfoo: bar\nbaz: qux'), 'hql')
})

test('tab names ending in .yml/.yaml force YAML', () => {
  assert.equal(detectEditorLanguage('database("x")', 'rule.yml'), 'yaml')
  assert.equal(detectEditorLanguage('database("x")', 'Rule.YAML '), 'yaml')
  assert.equal(detectEditorLanguage(sigma, 'Query 1'), 'yaml')
})
