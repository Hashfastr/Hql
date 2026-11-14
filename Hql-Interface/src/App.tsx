import { useEffect } from 'react'
import { Editor } from './components/Editor'
import { ResultsPane } from './components/ResultsPane'
import { RightPanel } from './components/RightPanel'
import { TopBar } from './components/TopBar'
import { useDragResize } from './hooks/useDragResize'
import { useRunner } from './hooks/useRunner'
import { persist } from './lib/persist'
import { useActiveTab, useAppDispatch, useAppState, useIsRunning } from './state/store'

export default function App() {
  const state = useAppState()
  const tab = useActiveTab()
  const dispatch = useAppDispatch()
  const isRunning = useIsRunning()
  const { run } = useRunner()

  useEffect(() => {
    persist(state)
  }, [state])

  // Editor height in px; the results pane takes the rest. The splitter div
  // below the editor is the drag target.
  const { size: editorHeight, startDrag: startSplitDrag } = useDragResize({
    storageKey: 'hql-interface:editor-height',
    defaultSize: Math.round(window.innerHeight * 0.45),
    min: 120,
    max: () => Math.round(window.innerHeight * 0.75),
    axis: 'y',
    direction: 1, // dragging down grows the editor
  })

  return (
    <div className="flex h-full flex-col bg-gruvbox-light-bg0 text-gruvbox-light-fg dark:bg-gruvbox-dark-bg0 dark:text-gruvbox-dark-fg">
      <TopBar />
      <div className="flex min-h-0 flex-1">
        <main className="flex min-w-0 flex-1 flex-col">
          <div style={{ height: editorHeight }} className="shrink-0">
            <Editor
              tabId={tab.id}
              title={tab.title}
              value={tab.query}
              editRev={tab.editRev}
              isDark={state.theme === 'dark'}
              onChange={(query) => dispatch({ type: 'setQuery', tabId: tab.id, query })}
              onRun={() => {
                if (!isRunning && tab.query.trim()) void run(tab.id, tab.query, tab.timeRange)
              }}
            />
          </div>
          <div
            onPointerDown={startSplitDrag}
            title="Drag to resize"
            className="relative z-10 -my-1 h-2 shrink-0 cursor-row-resize hover:bg-gruvbox-light-bg3/50 dark:hover:bg-gruvbox-dark-bg3/50"
          />
          <div className="min-h-0 flex-1 border-t border-gruvbox-light-bg2 dark:border-gruvbox-dark-bg2">
            <ResultsPane />
          </div>
        </main>
        <RightPanel />
      </div>
    </div>
  )
}
