import { useEffect, useRef, type ReactNode } from 'react'
import '../css/GroupDialog.css'

interface GroupDialogProps {
  title: string
  children: ReactNode
  onClose: () => void
  busy?: boolean
}

export function GroupDialog({ title, children, onClose, busy = false }: GroupDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null)

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
      onCancel={event => {
        event.preventDefault()
        if (!busy) onClose()
      }}
    >
      <div className="group-dialog-heading">
        <h2>{title}</h2>
        <button className="group-dialog-close" onClick={onClose} disabled={busy}>
          &times;
        </button>
      </div>
      {children}
    </dialog>
  )
}
