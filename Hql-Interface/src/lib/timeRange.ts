// Per-tab search window for HaC and Sigma runs. Pure and node-testable.
//
// The backend only time-bounds queries that carry HaC (Sigma rules always
// do), so the window is ignored for plain Hql. It is sent with each run:
// - default:  nothing sent, the HaC schedule's interval up to now
// - lookback: { lookback: '1h' }, a timespan as ago() takes it
// - absolute: { start, end } as UTC ISO; the backend converts to its local time
import type { TimeRange } from '../types'

export const DEFAULT_TIME_RANGE: TimeRange = { mode: 'default' }

export const LOOKBACK_PRESETS = ['15m', '1h', '4h', '12h', '24h', '7d', '30d'] as const

// Mirrors parse_timespan in Hql/Functions/time.py (TIMESPANLITERAL units)
const TIMESPAN =
  /^(\d+(?:\.\d+)?)\s*(micro(?:s(?:(?:ec(?:ond)?)?s?)?)?|ms|milli(?:s(?:(?:ec(?:ond)?)?s?)?)?|m(?:in(?:ute)?s?)?|s(?:ec(?:ond)?s?)?|h(?:(?:our|r)s?)?|d(?:ays?)?)$/

/** A lookback the backend accepts: a positive timespan like 30m, 1h or 7d. */
export function isValidLookback(text: string): boolean {
  const match = TIMESPAN.exec(text.trim())
  return match !== null && Number(match[1]) > 0
}

/** `<input type="datetime-local">` value for a Date, in the viewer's local time. */
export function toLocalInput(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

/** Why a range can't be run, or '' when it can. */
export function validateTimeRange(range: TimeRange): string {
  if (range.mode === 'lookback' && !isValidLookback(range.lookback)) {
    return `Invalid lookback "${range.lookback}", expected e.g. 30m, 1h or 7d`
  }
  if (range.mode === 'absolute') {
    const start = new Date(range.start)
    const end = new Date(range.end)
    if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
      return 'Start and end must both be set'
    }
    if (!(start < end)) return 'Start must be before end'
  }
  return ''
}

/** Run request fields for a range; empty for the schedule default. */
export function timeRangeParams(
  range: TimeRange,
): { lookback: string } | { start: string; end: string } | Record<string, never> {
  switch (range.mode) {
    case 'lookback':
      return { lookback: range.lookback.trim() }
    case 'absolute':
      return {
        start: new Date(range.start).toISOString(),
        end: new Date(range.end).toISOString(),
      }
    default:
      return {}
  }
}

function shortDate(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

/** Toolbar label for a range. */
export function describeTimeRange(range: TimeRange): string {
  switch (range.mode) {
    case 'lookback':
      return `Last ${range.lookback.trim()}`
    case 'absolute':
      return `${shortDate(new Date(range.start))} → ${shortDate(new Date(range.end))}`
    default:
      return 'Schedule window'
  }
}

/**
 * Status-line text for the window a finished run searched. The backend sends
 * naive ISO in the server's local time, so show it verbatim rather than
 * reinterpret it in the browser's zone.
 */
export function describeSearched(window: { start: string; end: string }): string {
  const fmt = (s: string) => s.slice(0, 16).replace('T', ' ')
  return `${fmt(window.start)} → ${fmt(window.end)}`
}

/** A persisted value as a TimeRange, or the default when it is malformed. */
export function parseTimeRange(value: unknown): TimeRange {
  if (!value || typeof value !== 'object') return DEFAULT_TIME_RANGE
  const v = value as Record<string, unknown>
  if (v.mode === 'lookback' && typeof v.lookback === 'string') {
    return { mode: 'lookback', lookback: v.lookback }
  }
  if (v.mode === 'absolute' && typeof v.start === 'string' && typeof v.end === 'string') {
    return { mode: 'absolute', start: v.start, end: v.end }
  }
  return DEFAULT_TIME_RANGE
}
