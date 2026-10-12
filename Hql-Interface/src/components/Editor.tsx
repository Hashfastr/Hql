import { useEffect, useRef } from 'react'
import { Compartment, EditorState, type Extension } from '@codemirror/state'
import {
  EditorView,
  drawSelection,
  highlightActiveLine,
  highlightActiveLineGutter,
  keymap,
  lineNumbers,
  scrollPastEnd,
} from '@codemirror/view'
import { defaultKeymap, history, historyKeymap, indentWithTab } from '@codemirror/commands'
import { bracketMatching } from '@codemirror/language'
import {
  acceptCompletion,
  closeBrackets,
  closeBracketsKeymap,
  completionKeymap,
} from '@codemirror/autocomplete'
import { lintKeymap } from '@codemirror/lint'
import { gruvboxTheme } from '../hql/theme'

// Everything below is module-level on the assumption that EXACTLY ONE Editor
// is mounted at a time (one editor, keyed by tab id, remounted on tab switch).
// If two editors ever render simultaneously, all three of these need to move
// to per-instance ownership.

// Compartments must be the same instances across remounts, or cached
// EditorStates from a previous mount can't be reconfigured.
const themeConf = new Compartment()
const hqlConf = new Compartment()

// EditorStates cached per tab id so undo history survives tab switches.
// Deliberately unbounded: states are cheap and tabs are few.
const stateCache = new Map<string, EditorState>()

// Cached EditorStates keep the extension closures they were created with, so
// a restored state's updateListener/keymap would call a stale render's props.
// Routing through this module-level object keeps callbacks always-current.
const live = {
  onChange: (_v: string) => {},
  onRun: () => {},
}

// The ANTLR parser is ~1 MB; load it as a lazy chunk and upgrade the editor when ready
let hqlExtensions: Extension | null = null
const hqlLoaded = import('../hql')
  .then((m) => {
    hqlExtensions = m.hqlExtensions()
    return hqlExtensions
  })
  .catch(() => null)

export function Editor({
  tabId,
  value,
  editRev,
  isDark,
  onChange,
  onRun,
}: {
  tabId: string
  value: string
  editRev: number
  isDark: boolean
  onChange: (value: string) => void
  onRun: () => void
}) {
  const container = useRef<HTMLDivElement>(null)
  const viewRef = useRef<EditorView | null>(null)
  live.onChange = onChange
  live.onRun = onRun

  useEffect(() => {
    if (!container.current) return

    const extensions: Extension = [
      lineNumbers(),
      scrollPastEnd(),
      highlightActiveLineGutter(),
      highlightActiveLine(),
      drawSelection(),
      history(),
      bracketMatching(),
      closeBrackets(),
      keymap.of([
        {
          key: 'Mod-Enter',
          run: () => {
            live.onRun()
            return true
          },
        },
        // Tab accepts the selected completion when the popup is open;
        // acceptCompletion returns false otherwise, falling through to indent
        { key: 'Tab', run: acceptCompletion },
        ...closeBracketsKeymap,
        ...defaultKeymap,
        ...historyKeymap,
        ...completionKeymap,
        ...lintKeymap,
        indentWithTab,
      ]),
      EditorView.updateListener.of((update) => {
        if (update.docChanged) live.onChange(update.state.doc.toString())
      }),
      themeConf.of(gruvboxTheme(isDark)),
      hqlConf.of(hqlExtensions ?? []),
    ]

    const cached = stateCache.get(tabId)
    const state =
      cached && cached.doc.toString() === value
        ? cached
        : EditorState.create({ doc: value, extensions })
    const view = new EditorView({ state, parent: container.current })
    viewRef.current = view
    // Debug/test handle; also documents that exactly one view exists at a time
    ;(window as unknown as Record<string, unknown>).__hqlEditorView = view

    if (!hqlExtensions) {
      void hqlLoaded.then((ext) => {
        if (ext && viewRef.current === view) {
          view.dispatch({ effects: hqlConf.reconfigure(ext) })
        }
      })
    }

    return () => {
      stateCache.set(tabId, view.state)
      viewRef.current = null
      view.destroy()
    }
    // Recreate only per tab; value/theme handled by the effects below
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tabId])

  // External query replacement (Init HaC, Sigma convert). Keyed by editRev,
  // NEVER by value: useEffect runs after paint, so a value-keyed sync races
  // user input — a stale value from a lagging render would silently rewrite
  // text the user just typed/deleted (and then fight every correction).
  // While the user types, the editor document is the source of truth and
  // `value` is only the state echo of it.
  useEffect(() => {
    const view = viewRef.current
    if (!view) return
    const current = view.state.doc.toString()
    if (current !== value) {
      view.dispatch({ changes: { from: 0, to: current.length, insert: value } })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [editRev])

  useEffect(() => {
    viewRef.current?.dispatch({ effects: themeConf.reconfigure(gruvboxTheme(isDark)) })
  }, [isDark])

  return <div ref={container} className="h-full min-h-0 overflow-hidden" />
}
