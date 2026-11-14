import { useState } from 'react'
import { useActiveTab, useAppDispatch, useAppState, useIsRunning } from '../state/store'
import { useRunner } from '../hooks/useRunner'
import { useDetections } from '../hooks/useDetections'
import { useTheme } from '../hooks/useTheme'
import * as api from '../services/api'
import { QueryTabs } from './QueryTabs'
import { RetroHuntModal } from './RetroHuntModal'
import { TimeRangePicker } from './TimeRangePicker'
// Must be a bundler import: the backend statically serves ONLY /assets and
// index.html, so any asset referenced by absolute URL 404s in production.
import lainGif from '../../lain.gif'

export function TopBar() {
  const state = useAppState()
  const tab = useActiveTab()
  const dispatch = useAppDispatch()
  const isRunning = useIsRunning()
  const { run, stop } = useRunner()
  const { reload } = useDetections()
  const { theme, toggle } = useTheme()
  const [retroOpen, setRetroOpen] = useState(false)
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)

  const flash = (msg: string) => {
    setNotice(msg)
    setTimeout(() => setNotice(''), 5000)
  }

  const withBusy = async (fn: () => Promise<void>) => {
    setBusy(true)
    try {
      await fn()
    } catch (e) {
      flash(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  const canAct = tab.query.trim().length > 0 && !busy

  return (
    <div className="flex flex-col border-b border-gruvbox-light-bg2 dark:border-gruvbox-dark-bg2">
      <div className="flex items-center gap-2 px-2 pt-2 pb-1">
        <button
          className="btn btn-run"
          disabled={isRunning || !canAct}
          onClick={() => void run(tab.id, tab.query, tab.timeRange)}
          title="Run query (active tab)"
        >
          ▶ Run
        </button>
        <button
          className="btn btn-stop"
          disabled={tab.run.status !== 'running'}
          onClick={() => stop(tab.id)}
          title="Stop waiting for the running query"
        >
          ■ Stop
        </button>
        <TimeRangePicker
          value={tab.timeRange}
          onChange={(timeRange) => dispatch({ type: 'setTimeRange', tabId: tab.id, timeRange })}
        />
        {/* Always mounted, toggled via visibility: reserves the slot so the
            toolbar doesn't shift when a run starts, and pre-loads the gif */}
        <img
          src={lainGif}
          alt="running..."
          className={`h-8 w-8 rounded ${isRunning ? '' : 'invisible'}`}
        />

        <div className="mx-2 h-5 w-px bg-gruvbox-light-bg3 dark:bg-gruvbox-dark-bg3" />

        <button
          className="btn"
          disabled={!canAct}
          title="Save the query as a detection"
          onClick={() =>
            void withBusy(async () => {
              const { id } = await api.saveDetection(tab.query)
              flash(`Saved detection ${id}`)
              void reload()
            })
          }
        >
          Save Detection
        </button>
        <button
          className="btn"
          disabled={!canAct}
          title="Prepend HaC metadata comment"
          onClick={() =>
            void withBusy(async () => {
              const { hql } = await api.initHac(tab.query)
              dispatch({ type: 'replaceQuery', tabId: tab.id, query: hql })
            })
          }
        >
          Init HaC
        </button>
        <button
          className="btn"
          disabled={!canAct}
          title="Convert a Sigma rule to Hql"
          onClick={() =>
            void withBusy(async () => {
              const { hql } = await api.convertSigma(tab.query)
              dispatch({ type: 'replaceQuery', tabId: tab.id, query: hql })
            })
          }
        >
          Sigma → Hql
        </button>
        <button className="btn" disabled={!canAct} onClick={() => setRetroOpen(true)}>
          Retro Hunt
        </button>

        {notice && (
          <span className="text-sm text-gruvbox-light-yellow dark:text-gruvbox-dark-yellow truncate">
            {notice}
          </span>
        )}

        <div className="flex-1" />

        <button className="btn" onClick={toggle} title="Toggle theme">
          {theme === 'dark' ? '☀' : '🌙'}
        </button>
        <button
          className="btn"
          onClick={() => dispatch({ type: 'toggleSidebar' })}
          title={state.sidebarCollapsed ? 'Show side panel' : 'Hide side panel'}
        >
          {state.sidebarCollapsed ? '⟨' : '⟩'}
        </button>
      </div>
      <div className="px-2">
        <QueryTabs />
      </div>
      {retroOpen && (
        <RetroHuntModal
          initial={tab.timeRange.mode === 'absolute' ? tab.timeRange : undefined}
          onClose={() => setRetroOpen(false)}
          onSubmit={(start, end) =>
            void withBusy(async () => {
              const { ids } = await api.retroHunt(tab.query, start, end)
              setRetroOpen(false)
              flash(`Retro hunt started: ${ids.length} run${ids.length === 1 ? '' : 's'}`)
            })
          }
        />
      )}
    </div>
  )
}
