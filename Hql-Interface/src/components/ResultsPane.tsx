import { useActiveTab, useAppDispatch } from '../state/store'
import { ResultsTable } from './ResultsTable'
import { describeSearched } from '../lib/timeRange'

export function ResultsPane() {
  const tab = useActiveTab()
  const dispatch = useAppDispatch()
  const { run } = tab

  if (run.status === 'idle') {
    return (
      <div className="flex h-full items-center justify-center text-sm text-gruvbox-light-gray dark:text-gruvbox-dark-gray">
        Run a query to see results
      </div>
    )
  }

  if (run.status === 'running') {
    return (
      <div className="flex h-full items-center justify-center text-sm text-gruvbox-light-gray dark:text-gruvbox-dark-gray">
        Running…
      </div>
    )
  }

  if (run.status === 'failed') {
    return (
      <div className="h-full overflow-auto p-3">
        <pre className="whitespace-pre-wrap text-xs text-gruvbox-light-red dark:text-gruvbox-dark-red">
          {run.strOut}
        </pre>
      </div>
    )
  }

  const tables = Object.keys(run.results?.data ?? {})
  if (tables.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-gruvbox-light-gray dark:text-gruvbox-dark-gray">
        Query completed with no results
        {run.timerange && ` between ${describeSearched(run.timerange).replace(' → ', ' and ')}`}
      </div>
    )
  }

  const active = tab.activeResultTable && tables.includes(tab.activeResultTable)
    ? tab.activeResultTable
    : tables[0]
  const rows = run.results!.data[active] ?? []

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-1 border-b border-gruvbox-light-bg2 dark:border-gruvbox-dark-bg2 px-2 pt-1">
        {tables.map((t) => (
          <button
            key={t}
            className={`px-2 py-1 text-sm rounded-t border-b-2 ${
              t === active
                ? 'border-gruvbox-light-aqua dark:border-gruvbox-dark-aqua bg-gruvbox-light-bg1 dark:bg-gruvbox-dark-bg1'
                : 'border-transparent hover:bg-gruvbox-light-bg1 dark:hover:bg-gruvbox-dark-bg1'
            }`}
            onClick={() => dispatch({ type: 'setActiveResultTable', tabId: tab.id, table: t })}
          >
            {t}
            <span className="ml-1 text-xs text-gruvbox-light-gray dark:text-gruvbox-dark-gray">
              {run.results!.data[t]?.length ?? 0}
            </span>
          </button>
        ))}
        <div className="flex-1" />
        <span className="text-xs text-gruvbox-light-gray dark:text-gruvbox-dark-gray pb-1">
          {/* num_results is 0 for plain (non-detection) runs; fall back to counting rows */}
          {run.numResults || tables.reduce((n, t) => n + (run.results!.data[t]?.length ?? 0), 0)}{' '}
          results
          {run.duration !== undefined && ` · ${run.duration.toFixed(2)}s`}
          {run.timerange ? (
            <span title="Window the run searched (server local time)">
              {' · '}
              {describeSearched(run.timerange)}
            </span>
          ) : (
            <span title="Only HaC and Sigma queries are time-bounded">{' · not time-bounded'}</span>
          )}
        </span>
      </div>
      <div className="min-h-0 flex-1">
        <ResultsTable
          tabId={tab.id}
          table={active}
          rows={rows}
          schema={run.results!.schema[active]}
        />
      </div>
    </div>
  )
}
