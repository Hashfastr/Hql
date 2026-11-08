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
import { HighlightStyle, bracketMatching, syntaxHighlighting } from '@codemirror/language'
import { yaml } from '@codemirror/lang-yaml'
import { tags } from '@lezer/highlight'
import {
  acceptCompletion,
  closeBrackets,
  closeBracketsKeymap,
  completionKeymap,
} from '@codemirror/autocomplete'
import { lintKeymap } from '@codemirror/lint'
import { gruvboxTheme } from '../hql/theme'
import { detectEditorLanguage, type EditorLanguage } from '../lib/editorLanguage'

// Everything below is module-level on the assumption that EXACTLY ONE Editor
// is mounted at a time (one editor, keyed by tab id, remounted on tab switch).
// If two editors ever render simultaneously, all three of these need to move
// to per-instance ownership.

// Compartments must be the same instances across remounts, or cached
// EditorStates from a previous mount can't be reconfigured.
const themeConf = new Compartment()
// Holds either the Hql extensions or the YAML ones (Sigma rules pasted in)
const langConf = new Compartment()

// EditorStates cached per tab id so undo history survives tab switches.
// Deliberately unbounded: states are cheap and tabs are few.
const stateCache = new Map<string, EditorState>()

// Cached EditorStates keep the extension closures they were created with, so
// a restored state's updateListener/keymap would call a stale render's props.
// Routing through this module-level object keeps callbacks always-current.
const live = {
  onChange: (_v: string) => {},
  onRun: () => {},
  title: '',
}

// How long typing must pause before the language is re-detected, so the
// highlighting doesn't flip back and forth mid-keystroke.
const DETECT_DELAY_MS = 300
let detectTimer: ReturnType<typeof setTimeout> | undefined

// The ANTLR parser is ~1 MB; load it as a lazy chunk and upgrade the editor when ready
let hqlExtensions: Extension | null = null
const hqlLoaded = import('../hql')
  .then((m) => {
    hqlExtensions = m.hqlExtensions()
    return hqlExtensions
  })
  .catch(() => null)

// YAML tokens reuse the theme's token classes so both modes share one palette
const yamlExtensions: Extension = [
  yaml(),
  syntaxHighlighting(
    HighlightStyle.define([
      { tag: tags.definition(tags.propertyName), class: 'hql-keyword' },
      { tag: tags.string, class: 'hql-string' },
      { tag: tags.content, class: 'hql-identifier' },
      { tag: tags.lineComment, class: 'hql-comment' },
      { tag: [tags.meta, tags.keyword, tags.labelName, tags.typeName], class: 'hql-literal' },
      { tag: [tags.attributeValue, tags.special(tags.string)], class: 'hql-type' },
      {
        tag: [tags.separator, tags.punctuation, tags.squareBracket, tags.brace],
        class: 'hql-operator',
      },
    ]),
  ),
]

function isYamlMode(state: EditorState): boolean {
  return langConf.get(state) === yamlExtensions
}

function languageExtensions(lang: EditorLanguage): Extension {
  return lang === 'yaml' ? yamlExtensions : (hqlExtensions ?? [])
}

// Swap the language compartment only when detection disagrees with it
function syncLanguage(view: EditorView) {
  clearTimeout(detectTimer)
  const lang = detectEditorLanguage(view.state.doc.toString(), live.title)
  if ((lang === 'yaml') !== isYamlMode(view.state)) {
    view.dispatch({ effects: langConf.reconfigure(languageExtensions(lang)) })
  }
}

export function Editor({
  tabId,
  title,
  value,
  editRev,
  isDark,
  onChange,
  onRun,
}: {
  tabId: string
  title: string
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
  live.title = title

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
        if (!update.docChanged) return
        live.onChange(update.state.doc.toString())
        clearTimeout(detectTimer)
        detectTimer = setTimeout(() => syncLanguage(update.view), DETECT_DELAY_MS)
      }),
      themeConf.of(gruvboxTheme(isDark)),
      langConf.of(languageExtensions(detectEditorLanguage(value, title))),
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
    // A cached state keeps the language it was left in; the title may have changed
    if (state === cached) syncLanguage(view)

    if (!hqlExtensions) {
      void hqlLoaded.then((ext) => {
        if (ext && viewRef.current === view && !isYamlMode(view.state)) {
          view.dispatch({ effects: langConf.reconfigure(ext) })
        }
      })
    }

    return () => {
      clearTimeout(detectTimer)
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
      // Replacement is deliberate (e.g. Sigma YAML -> Hql): switch without delay
      syncLanguage(view)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [editRev])

  // Renaming a tab to/from *.yml / *.yaml switches the mode immediately
  useEffect(() => {
    const view = viewRef.current
    if (view) syncLanguage(view)
  }, [title])

  useEffect(() => {
    viewRef.current?.dispatch({ effects: themeConf.reconfigure(gruvboxTheme(isDark)) })
  }, [isDark])

  return <div ref={container} className="h-full min-h-0 overflow-hidden" />
}
