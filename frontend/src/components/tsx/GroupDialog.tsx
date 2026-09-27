import { useEffect, useId, useRef, type ReactNode } from 'react'
import '../css/GroupDialog.css'

interface GroupDialogProps {
  title: string
  children: ReactNode
  onClose: () => void
  busy?: boolean
}

export function GroupDialog({ title, children, onClose, busy = false }: GroupDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const titleId = useId()

  useEffect(() => {
    const dialog = dialogRef.current
    const previousFocus = document.activeElement
    dialog?.showModal()
    dialog?.querySelector<HTMLElement>('[data-dialog-autofocus]')?.focus()
    return () => {
      dialog?.close()
      if (previousFocus instanceof HTMLElement) previousFocus.focus()
    }
  }, [])

  return (
    <dialog
      ref={dialogRef}
      className="group-dialog"
      aria-labelledby={titleId}
      aria-busy={busy}
      onCancel={event => {
        event.preventDefault()
        if (!busy) onClose()
      }}
    >
      <div className="group-dialog-heading">
        <h2 id={titleId}>{title}</h2>
        <button className="group-dialog-close" aria-label="Close dialog" onClick={onClose} disabled={busy}>
          &times;
        </button>
      </div>
      {children}
    </dialog>
  )
}
