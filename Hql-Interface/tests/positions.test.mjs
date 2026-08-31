import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'
import ts from 'typescript'

const source = await readFile(new URL('../src/hql/positions.ts', import.meta.url), 'utf8')
const javascript = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.ES2022,
    target: ts.ScriptTarget.ES2022,
  },
}).outputText
const positions = await import(
  `data:text/javascript;base64,${Buffer.from(javascript).toString('base64')}`
)

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
