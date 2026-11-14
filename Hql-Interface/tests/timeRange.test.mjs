import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'
import ts from 'typescript'

// timeRange.ts only has type imports, which transpile away
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

const tr = await loadTypeScriptModule('../src/lib/timeRange.ts')

test('lookbacks match what the backend parse_timespan accepts', () => {
  for (const ok of ['15m', '1h', '7d', '1.5days', '90 min', '2hrs', '30s', '500ms']) {
    assert.ok(tr.isValidLookback(ok), ok)
  }
  for (const bad of ['', 'h', '0h', '-1h', 'soon', '1w', '1h30m']) {
    assert.ok(!tr.isValidLookback(bad), bad)
  }
  for (const p of tr.LOOKBACK_PRESETS) assert.ok(tr.isValidLookback(p), p)
})

test('request params per mode', () => {
  assert.deepEqual(tr.timeRangeParams({ mode: 'default' }), {})
  assert.deepEqual(tr.timeRangeParams({ mode: 'lookback', lookback: ' 7d ' }), { lookback: '7d' })

  const start = '2026-11-14T09:00'
  const end = '2026-11-14T17:30'
  assert.deepEqual(tr.timeRangeParams({ mode: 'absolute', start, end }), {
    start: new Date(start).toISOString(),
    end: new Date(end).toISOString(),
  })
})

test('validation', () => {
  assert.equal(tr.validateTimeRange({ mode: 'default' }), '')
  assert.equal(tr.validateTimeRange({ mode: 'lookback', lookback: '1h' }), '')
  assert.match(tr.validateTimeRange({ mode: 'lookback', lookback: 'nope' }), /Invalid lookback/)
  const range = (start, end) => tr.validateTimeRange({ mode: 'absolute', start, end })
  assert.equal(range('2026-11-14T09:00', '2026-11-14T10:00'), '')
  assert.match(range('2026-11-14T10:00', '2026-11-14T09:00'), /before/)
  assert.match(range('2026-11-14T10:00', '2026-11-14T10:00'), /before/)
  assert.match(range('', '2026-11-14T10:00'), /both/)
})

test('labels', () => {
  assert.equal(tr.describeTimeRange({ mode: 'default' }), 'Schedule window')
  assert.equal(tr.describeTimeRange({ mode: 'lookback', lookback: '24h' }), 'Last 24h')
  assert.equal(
    tr.describeTimeRange({ mode: 'absolute', start: '2026-11-14T09:00', end: '2026-11-15T17:05' }),
    '2026-11-14 09:00 → 2026-11-15 17:05',
  )
  assert.equal(
    tr.describeSearched({ start: '2026-11-14T11:30:00', end: '2026-11-14T12:00:00.123456' }),
    '2026-11-14 11:30 → 2026-11-14 12:00',
  )
})

test('toLocalInput round-trips through Date', () => {
  const d = new Date(2026, 10, 14, 9, 5)
  assert.equal(tr.toLocalInput(d), '2026-11-14T09:05')
  assert.equal(new Date(tr.toLocalInput(d)).getTime(), d.getTime())
})

test('persisted ranges are validated on load', () => {
  assert.deepEqual(tr.parseTimeRange(undefined), { mode: 'default' })
  assert.deepEqual(tr.parseTimeRange({ mode: 'lookback' }), { mode: 'default' })
  assert.deepEqual(tr.parseTimeRange({ mode: 'weird' }), { mode: 'default' })
  assert.deepEqual(tr.parseTimeRange({ mode: 'lookback', lookback: '7d' }), {
    mode: 'lookback',
    lookback: '7d',
  })
  const abs = { mode: 'absolute', start: '2026-11-14T09:00', end: '2026-11-14T10:00' }
  assert.deepEqual(tr.parseTimeRange({ ...abs, extra: 1 }), abs)
})
