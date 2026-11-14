import { useEffect, useRef, useState } from 'react'
import type { TimeRange } from '../types'
import {
  LOOKBACK_PRESETS,
  describeTimeRange,
  isValidLookback,
  toLocalInput,
  validateTimeRange,
} from '../lib/timeRange'

const inputCls =
  'w-full rounded bg-gruvbox-light-bg1 dark:bg-gruvbox-dark-bg1 px-2 py-1 text-sm ' +
  'border border-transparent focus:outline-none focus:border-gruvbox-light-aqua dark:focus:border-gruvbox-dark-aqua'

const chipCls = (active: boolean) =>
  `rounded px-2 py-0.5 text-xs font-medium ${
    active
      ? 'bg-gruvbox-light-aqua text-gruvbox-light-bg0 dark:bg-gruvbox-dark-aqua dark:text-gruvbox-dark-bg0'
      : 'bg-gruvbox-light-bg2 hover:bg-gruvbox-light-bg3 dark:bg-gruvbox-dark-bg2 dark:hover:bg-gruvbox-dark-bg3'
  }`

const sectionCls =
  'mb-1 text-xs font-semibold uppercase tracking-wide text-gruvbox-light-gray dark:text-gruvbox-dark-gray'

/**
 * Per-tab search window for HaC and Sigma runs: the schedule's interval
 * (backend default), a relative lookback, or an absolute start/end. Only
 * valid ranges are ever applied, so the stored range is always runnable.
 */
export function TimeRangePicker({
  value,
  onChange,
  disabled,
}: {
  value: TimeRange
  onChange: (range: TimeRange) => void
  disabled?: boolean
}) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const onDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false)
    window.addEventListener('mousedown', onDown)
    window.addEventListener('keydown', onKey)
    return () => {
      window.removeEventListener('mousedown', onDown)
      window.removeEventListener('keydown', onKey)
    }
  }, [open])

  const apply = (range: TimeRange) => {
    onChange(range)
    setOpen(false)
  }

  return (
    <div ref={ref} className="relative">
      <button
        className="btn flex items-center gap-1.5"
        disabled={disabled}
        onClick={() => setOpen((o) => !o)}
        title="Search window for HaC and Sigma queries"
        aria-haspopup="dialog"
        aria-expanded={open}
      >
        <span aria-hidden>🕒</span>
        <span className="max-w-[22rem] truncate">{describeTimeRange(value)}</span>
        <span aria-hidden className="text-xs opacity-70">▾</span>
      </button>
      {open && <Popover value={value} onApply={apply} />}
    </div>
  )
}

// Mounted only while open, so drafts re-seed from the applied range each time
function Popover({ value, onApply }: { value: TimeRange; onApply: (range: TimeRange) => void }) {
  const [custom, setCustom] = useState(
    value.mode === 'lookback' && !(LOOKBACK_PRESETS as readonly string[]).includes(value.lookback)
      ? value.lookback
      : '',
  )
  const [start, setStart] = useState(() =>
    value.mode === 'absolute' ? value.start : toLocalInput(new Date(Date.now() - 3600_000)),
  )
  const [end, setEnd] = useState(() =>
    value.mode === 'absolute' ? value.end : toLocalInput(new Date()),
  )
  const [error, setError] = useState('')

  const tryApply = (range: TimeRange) => {
    const err = validateTimeRange(range)
    if (err) setError(err)
    else onApply(range)
  }

  return (
    <div
      role="dialog"
      aria-label="Search window"
      className="absolute left-0 top-full z-50 mt-1 w-80 rounded border border-gruvbox-light-bg3 dark:border-gruvbox-dark-bg3 bg-gruvbox-light-bg0 dark:bg-gruvbox-dark-bg0 p-3 shadow-lg text-sm"
    >
      <p className="mb-3 text-xs text-gruvbox-light-gray dark:text-gruvbox-dark-gray">
        Bounds HaC and Sigma queries. Plain Hql without a HaC header isn't time-bounded.
      </p>

      <div className="mb-3">
        <button
          className={chipCls(value.mode === 'default')}
          onClick={() => onApply({ mode: 'default' })}
          title="Look back one schedule interval from now (the backend default)"
        >
          Schedule window
        </button>
      </div>

      <div className="mb-3">
        <div className={sectionCls}>Lookback</div>
        <div className="mb-2 flex flex-wrap gap-1">
          {LOOKBACK_PRESETS.map((p) => (
            <button
              key={p}
              className={chipCls(value.mode === 'lookback' && value.lookback === p)}
              onClick={() => onApply({ mode: 'lookback', lookback: p })}
            >
              {p}
            </button>
          ))}
        </div>
        <form
          className="flex gap-1"
          onSubmit={(e) => {
            e.preventDefault()
            tryApply({ mode: 'lookback', lookback: custom.trim() })
          }}
        >
          <input
            className={inputCls}
            placeholder="Custom, e.g. 90m, 2d"
            value={custom}
            onChange={(e) => {
              setCustom(e.target.value)
              setError('')
            }}
            aria-invalid={custom.trim() !== '' && !isValidLookback(custom)}
          />
          <button type="submit" className="btn" disabled={!custom.trim()}>
            Apply
          </button>
        </form>
      </div>

      <div>
        <div className={sectionCls}>Absolute range</div>
        <label className="mb-1 block text-xs">
          Start
          <input
            type="datetime-local"
            className={`${inputCls} mt-0.5`}
            value={start}
            onChange={(e) => {
              setStart(e.target.value)
              setError('')
            }}
          />
        </label>
        <label className="mb-2 block text-xs">
          End
          <input
            type="datetime-local"
            className={`${inputCls} mt-0.5`}
            value={end}
            onChange={(e) => {
              setEnd(e.target.value)
              setError('')
            }}
          />
        </label>
        <div className="flex justify-end">
          <button className="btn" onClick={() => tryApply({ mode: 'absolute', start, end })}>
            Apply range
          </button>
        </div>
      </div>

      {error && (
        <p className="mt-2 text-xs text-gruvbox-light-red dark:text-gruvbox-dark-red">{error}</p>
      )}
    </div>
  )
}
