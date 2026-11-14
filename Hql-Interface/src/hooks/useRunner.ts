import { useCallback, useRef } from 'react'
import * as api from '../services/api'
import { useAppDispatch } from '../state/store'
import type { HqlResults, TimeRange } from '../types'

/**
 * Owns the client side of a run: submit, poll, abort.
 * Stop aborts the polling only — the backend has no cancel, so
 * "stop" means "stop waiting for this run".
 */
export function useRunner() {
  const dispatch = useAppDispatch()
  const controllers = useRef(new Map<string, AbortController>())

  const run = useCallback(
    async (tabId: string, hql: string, timeRange: TimeRange) => {
      const controller = new AbortController()
      controllers.current.set(tabId, controller)
      dispatch({ type: 'runStarted', tabId, runId: '' })
      try {
        const { id } = await api.startRun(hql, timeRange, controller.signal)
        dispatch({ type: 'runStarted', tabId, runId: id })
        const result = await api.pollRun(id, controller.signal)
        if (result.failed) {
          dispatch({ type: 'runFailed', tabId, strOut: result.str_out || 'Run failed' })
        } else {
          const results: HqlResults = {
            data: result.results?.data ?? {},
            schema: result.results?.schema ?? {},
          }
          dispatch({
            type: 'runDone',
            tabId,
            results,
            duration: result.duration,
            numResults: result.num_results,
            timerange: result.timerange,
          })
        }
      } catch (e) {
        if (e instanceof DOMException && e.name === 'AbortError') {
          dispatch({ type: 'runStopped', tabId })
        } else {
          dispatch({ type: 'runFailed', tabId, strOut: e instanceof Error ? e.message : String(e) })
        }
      } finally {
        controllers.current.delete(tabId)
      }
    },
    [dispatch],
  )

  const stop = useCallback((tabId: string) => {
    controllers.current.get(tabId)?.abort()
  }, [])

  return { run, stop }
}
