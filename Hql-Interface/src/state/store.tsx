// Single context + useReducer store — the whole state layer, on purpose.
// Key invariants the UI depends on:
// - "Is anything running?" is DERIVED (useIsRunning scans tabs), never stored;
//   the spec's one-query-at-a-time rule hangs off it, so keep it derived.
// - The right panel is modal (detections XOR row inspector); anything that
//   invalidates the inspected row must route through resetInspectorFor.
// - Results live only in memory; persist.ts saves tab titles/queries only.
import { createContext, useContext, useReducer, type Dispatch, type ReactNode } from 'react'
import type { AppState, DetectionMeta, HqlResults, QueryTab, TimeRange } from '../types'
import { loadPersisted } from '../lib/persist'
import { DEFAULT_TIME_RANGE } from '../lib/timeRange'

export type Action =
  | { type: 'addTab'; query?: string; title?: string }
  | { type: 'closeTab'; tabId: string }
  | { type: 'renameTab'; tabId: string; title: string }
  | { type: 'setActiveTab'; tabId: string }
  | { type: 'setQuery'; tabId: string; query: string }
  | { type: 'replaceQuery'; tabId: string; query: string }
  | { type: 'setTimeRange'; tabId: string; timeRange: TimeRange }
  | { type: 'runStarted'; tabId: string; runId: string }
  | {
      type: 'runDone'
      tabId: string
      results: HqlResults
      duration?: number
      numResults?: number
      timerange?: { start: string; end: string }
    }
  | { type: 'runFailed'; tabId: string; strOut: string }
  | { type: 'runStopped'; tabId: string }
  | { type: 'setActiveResultTable'; tabId: string; table: string }
  | { type: 'expandRow'; tabId: string; table: string; rowIndex: number }
  | { type: 'closeInspector' }
  | { type: 'toggleSidebar' }
  | { type: 'setTheme'; theme: 'dark' | 'light' }
  | { type: 'detectionsLoading' }
  | { type: 'detectionsLoaded'; items: DetectionMeta[] }
  | { type: 'detectionsError'; error: string }

let tabCounter = 0
export function newTab(query = '', title?: string, timeRange: TimeRange = DEFAULT_TIME_RANGE): QueryTab {
  tabCounter += 1
  return {
    id: `tab-${Date.now()}-${tabCounter}`,
    title: title ?? `Query ${tabCounter}`,
    query,
    editRev: 0,
    timeRange,
    run: { status: 'idle' },
  }
}

function updateTab(state: AppState, tabId: string, patch: Partial<QueryTab>): AppState {
  return {
    ...state,
    tabs: state.tabs.map((t) => (t.id === tabId ? { ...t, ...patch } : t)),
  }
}

// Row inspector follows the data it shows: any change to a tab's results
// closes an inspector pointed at that tab.
function resetInspectorFor(state: AppState, tabId: string): AppState {
  if (state.rightPanel.mode === 'row' && state.rightPanel.tabId === tabId) {
    return { ...state, rightPanel: { mode: 'detections' } }
  }
  return state
}

export function reducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    case 'addTab': {
      const tab = newTab(action.query, action.title)
      return { ...state, tabs: [...state.tabs, tab], activeTabId: tab.id }
    }
    case 'closeTab': {
      if (state.tabs.length <= 1) return state
      const idx = state.tabs.findIndex((t) => t.id === action.tabId)
      if (idx === -1) return state
      const tabs = state.tabs.filter((t) => t.id !== action.tabId)
      const activeTabId =
        state.activeTabId === action.tabId
          ? tabs[Math.max(0, idx - 1)].id
          : state.activeTabId
      return resetInspectorFor({ ...state, tabs, activeTabId }, action.tabId)
    }
    case 'renameTab':
      return updateTab(state, action.tabId, { title: action.title })
    case 'setActiveTab':
      return { ...state, activeTabId: action.tabId }
    case 'setQuery':
      // Editor -> state echo of user typing; must NOT touch editRev (the
      // editor document is the source of truth while the user types)
      return updateTab(state, action.tabId, { query: action.query })
    case 'replaceQuery':
      // External write (Init HaC, Sigma convert): bump editRev so the
      // mounted editor replaces its document
      return {
        ...state,
        tabs: state.tabs.map((t) =>
          t.id === action.tabId
            ? { ...t, query: action.query, editRev: t.editRev + 1 }
            : t,
        ),
      }
    case 'setTimeRange':
      return updateTab(state, action.tabId, { timeRange: action.timeRange })
    case 'runStarted':
      return resetInspectorFor(
        updateTab(state, action.tabId, { run: { status: 'running', runId: action.runId } }),
        action.tabId,
      )
    case 'runDone': {
      const tables = Object.keys(action.results.data)
      return updateTab(state, action.tabId, {
        run: {
          status: 'done',
          results: action.results,
          duration: action.duration,
          numResults: action.numResults,
          timerange: action.timerange,
        },
        activeResultTable: tables[0],
      })
    }
    case 'runFailed':
      return updateTab(state, action.tabId, { run: { status: 'failed', strOut: action.strOut } })
    case 'runStopped':
      return updateTab(state, action.tabId, { run: { status: 'idle' } })
    case 'setActiveResultTable':
      return updateTab(state, action.tabId, { activeResultTable: action.table })
    case 'expandRow':
      return {
        ...state,
        sidebarCollapsed: false,
        rightPanel: {
          mode: 'row',
          tabId: action.tabId,
          table: action.table,
          rowIndex: action.rowIndex,
        },
      }
    case 'closeInspector':
      return { ...state, rightPanel: { mode: 'detections' } }
    case 'toggleSidebar':
      return { ...state, sidebarCollapsed: !state.sidebarCollapsed }
    case 'setTheme':
      return { ...state, theme: action.theme }
    case 'detectionsLoading':
      return { ...state, detections: { status: 'loading', items: state.detections.items } }
    case 'detectionsLoaded':
      return { ...state, detections: { status: 'ready', items: action.items } }
    case 'detectionsError':
      return {
        ...state,
        detections: { status: 'error', items: state.detections.items, error: action.error },
      }
  }
}

export function initialState(): AppState {
  const persisted = loadPersisted()
  const tabs = persisted?.tabs?.length
    ? persisted.tabs.map((t) => ({ ...newTab(t.query, t.title, t.timeRange), id: t.id }))
    : [newTab()]
  const activeTabId = tabs.some((t) => t.id === persisted?.activeTabId)
    ? (persisted?.activeTabId as string)
    : tabs[0].id
  return {
    tabs,
    activeTabId,
    theme: persisted?.theme ?? 'dark',
    sidebarCollapsed: persisted?.sidebarCollapsed ?? false,
    rightPanel: { mode: 'detections' },
    detections: { status: 'loading', items: [] },
  }
}

const StateContext = createContext<AppState | null>(null)
const DispatchContext = createContext<Dispatch<Action> | null>(null)

export function StoreProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, undefined, initialState)
  return (
    <StateContext.Provider value={state}>
      <DispatchContext.Provider value={dispatch}>{children}</DispatchContext.Provider>
    </StateContext.Provider>
  )
}

export function useAppState(): AppState {
  const state = useContext(StateContext)
  if (!state) throw new Error('useAppState outside StoreProvider')
  return state
}

export function useAppDispatch(): Dispatch<Action> {
  const dispatch = useContext(DispatchContext)
  if (!dispatch) throw new Error('useAppDispatch outside StoreProvider')
  return dispatch
}

export function useActiveTab(): QueryTab {
  const state = useAppState()
  return state.tabs.find((t) => t.id === state.activeTabId) ?? state.tabs[0]
}

// Global run lock: the spec forbids starting a query while one runs, in ANY
// tab. Every Run button and Mod-Enter binding must gate on this.
export function useIsRunning(): boolean {
  return useAppState().tabs.some((t) => t.run.status === 'running')
}
