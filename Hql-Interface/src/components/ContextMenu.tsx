import { useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'

export interface MenuItem {
  label: string
  action: () => void
}

export function ContextMenu({
  x,
  y,
  items,
  onClose,
}: {
  x: number
  y: number
  items: MenuItem[]
  onClose: () => void
}) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const close = () => onClose()
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    // Defer so the opening click doesn't immediately close it
    const t = setTimeout(() => {
      window.addEventListener('click', close)
      window.addEventListener('scroll', close, true)
      window.addEventListener('keydown', onKey)
    }, 0)
    return () => {
      clearTimeout(t)
      window.removeEventListener('click', close)
      window.removeEventListener('scroll', close, true)
      window.removeEventListener('keydown', onKey)
    }
  }, [onClose])

  // Clamp to viewport
  const style: React.CSSProperties = {
    left: Math.min(x, window.innerWidth - 200),
    top: Math.min(y, window.innerHeight - items.length * 32 - 8),
  }

  // Portaled to <body>, outside the app root that sets the text color, so set it here too
  return createPortal(
    <div
      ref={ref}
      style={style}
      className="fixed z-50 min-w-[180px] rounded border border-gruvbox-light-bg3 dark:border-gruvbox-dark-bg3 bg-gruvbox-light-bg0 dark:bg-gruvbox-dark-bg0 text-gruvbox-light-fg dark:text-gruvbox-dark-fg font-sans py-1 shadow-lg text-sm"
    >
      {items.map((item) => (
        <button
          key={item.label}
          className="block w-full px-3 py-1 text-left hover:bg-gruvbox-light-bg2 dark:hover:bg-gruvbox-dark-bg2"
          onClick={() => {
            item.action()
            onClose()
          }}
        >
          {item.label}
        </button>
      ))}
    </div>,
    document.body,
  )
}
