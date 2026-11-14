export type Row = Record<string, unknown>

export interface HqlResults {
  data: Record<string, Row[]>
  schema: Record<string, Record<string, string>>
}

// GET /api/hql/runs/{id} — note the backend key is run_id, not id
export interface HqlRun {
  run_id: string
  run_date?: string
  started: boolean
  failed: boolean
  completed: boolean
  num_results?: number
  duration?: number
  results?: Partial<HqlResults>
  str_out?: string
  hac?: unknown
  /** Window the run searched; only present for HaC/Sigma (time-bounded) runs */
  timerange?: { start: string; end: string }
}

// GET /api/detections returns HAC asm dicts; every field is author-supplied
export interface DetectionMeta {
  id?: string
  title?: string
  author?: string
  status?: string
  level?: string
  schedule?: string
  description?: string
  tags?: string[]
}

export interface DetectionDetail {
  id: string
  hql: string
  history: unknown[]
  schedule?: string
}

export interface RunState {
  status: 'idle' | 'running' | 'done' | 'failed'
  runId?: string
  results?: HqlResults
  strOut?: string
  duration?: number
  numResults?: number
  timerange?: { start: string; end: string }
}

/**
 * Search window for HaC and Sigma runs (plain Hql isn't time-bounded).
 * Absolute start/end are `datetime-local` values in the viewer's local time.
 */
export type TimeRange =
  | { mode: 'default' }
  | { mode: 'lookback'; lookback: string }
  | { mode: 'absolute'; start: string; end: string }

export interface QueryTab {
  id: string
  title: string
  query: string
  /**
   * Bumped ONLY by external query replacement (Init HaC, Sigma convert).
   * The editor syncs its document on this — never on `query` itself, which
   * lags the document during typing and would overwrite user input.
   */
  editRev: number
  timeRange: TimeRange
  run: RunState
  activeResultTable?: string
}

export type RightPanelState =
  | { mode: 'detections' }
  | { mode: 'row'; tabId: string; table: string; rowIndex: number }

export interface DetectionsState {
  status: 'loading' | 'ready' | 'error'
  items: DetectionMeta[]
  error?: string
}

export interface AppState {
  tabs: QueryTab[]
  activeTabId: string
  theme: 'dark' | 'light'
  sidebarCollapsed: boolean
  rightPanel: RightPanelState
  detections: DetectionsState
}
