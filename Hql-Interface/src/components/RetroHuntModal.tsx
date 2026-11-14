import { useState } from 'react'
import { toLocalInput } from '../lib/timeRange'

export function RetroHuntModal({
  initial,
  onClose,
  onSubmit,
}: {
  /** Seeds the fields, e.g. from the tab's absolute time range */
  initial?: { start: string; end: string }
  onClose: () => void
  onSubmit: (startIso: string, endIso: string) => void
}) {
  const [start, setStart] = useState(
    () => initial?.start ?? toLocalInput(new Date(Date.now() - 3600_000)),
  )
  const [end, setEnd] = useState(() => initial?.end ?? toLocalInput(new Date()))
  const [error, setError] = useState('')

  const submit = () => {
    const s = new Date(start)
    const e = new Date(end)
    if (!(s < e)) {
      setError('Start must be before end')
      return
    }
    onSubmit(s.toISOString(), e.toISOString())
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={onClose}
      onKeyDown={(e) => e.key === 'Escape' && onClose()}
    >
      <div
        className="w-96 rounded border border-gruvbox-light-bg3 dark:border-gruvbox-dark-bg3 bg-gruvbox-light-bg0 dark:bg-gruvbox-dark-bg0 p-4 shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="mb-3 font-semibold">Retro Hunt</h2>
        <label className="block text-sm mb-2">
          Start
          <input
            type="datetime-local"
            className="mt-1 w-full rounded bg-gruvbox-light-bg1 dark:bg-gruvbox-dark-bg1 px-2 py-1"
            value={start}
            onChange={(e) => setStart(e.target.value)}
          />
        </label>
        <label className="block text-sm mb-2">
          End
          <input
            type="datetime-local"
            className="mt-1 w-full rounded bg-gruvbox-light-bg1 dark:bg-gruvbox-dark-bg1 px-2 py-1"
            value={end}
            onChange={(e) => setEnd(e.target.value)}
          />
        </label>
        {error && (
          <p className="text-sm text-gruvbox-light-red dark:text-gruvbox-dark-red">{error}</p>
        )}
        <div className="mt-3 flex justify-end gap-2">
          <button className="btn" onClick={onClose}>
            Cancel
          </button>
          <button className="btn btn-run" onClick={submit}>
            Hunt
          </button>
        </div>
      </div>
    </div>
  )
}
