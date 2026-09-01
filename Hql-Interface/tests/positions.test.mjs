import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'
import ts from 'typescript'

async function loadTypeScriptModule(path) {
  const source = await readFile(new URL(path, import.meta.url), 'utf8')
  const javascript = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.ES2022,
      target: ts.ScriptTarget.ES2022,
    },
  }).outputText
  return import(`data:text/javascript;base64,${Buffer.from(javascript).toString('base64')}`)
}

const positions = await loadTypeScriptModule('../src/hql/positions.ts')
const categories = await loadTypeScriptModule('../src/hql/categories.ts')

test('maps ANTLR code-point offsets to CodeMirror UTF-16 offsets', () => {
  const text = '😀/* first\nsecond */'
  const boundaries = positions.codePointBoundaries(text)
  const commentEnd = [...text].length

  assert.equal(positions.codeUnitOffset(boundaries, 0), 0)
  assert.equal(positions.codeUnitOffset(boundaries, 1), 2)
  assert.equal(positions.codeUnitOffset(boundaries, 3), 4)
  assert.deepEqual(
    [
      positions.codeUnitOffset(boundaries, 1),
      positions.codeUnitOffset(boundaries, commentEnd),
    ],
    [2, text.length],
  )
  assert.equal(positions.codeUnitOffset(boundaries, Number.POSITIVE_INFINITY), text.length)
})

test('preserves offsets for text made only of single UTF-16 units', () => {
  const text = '/* first\nsecond */'
  const boundaries = positions.codePointBoundaries(text)

  for (let offset = 0; offset <= text.length; offset += 1) {
    assert.equal(positions.codeUnitOffset(boundaries, offset), offset)
  }
})

test('splits multiline decorations around line breaks and blank lines', () => {
  const text = "let x = 1\n/*\n\n*/\nlet y = 2"
  const from = text.indexOf('/*')
  const to = text.indexOf('*/') + 2

  assert.deepEqual(positions.lineRanges(text, from, to), [
    { from, to: from + 2 },
    { from: to - 2, to },
  ])
})

test('highlights both comment tokens', () => {
  assert.equal(categories.tokenCategory('COMMENT'), 'comment')
  assert.equal(categories.tokenCategory('MULTILINECOMMENT'), 'comment')
})
