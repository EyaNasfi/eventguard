import { X } from 'lucide-react';
import { useEffect, useId, useRef, type ReactNode } from 'react';
import { cn } from '../../lib/cn';

interface DialogProps {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: ReactNode;
  children?: ReactNode;
  footer?: ReactNode;
  size?: 'sm' | 'md' | 'lg';
}

/**
 * Native <dialog> with showModal(): focus trap, Esc and inert background come from
 * the platform. Reserved for protected focus (tamper simulation, destructive confirm).
 */
export function Dialog({ open, onClose, title, description, children, footer, size = 'md' }: DialogProps) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  const descId = useId();

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (open && !el.open) el.showModal();
    if (!open && el.open) el.close();
  }, [open]);

  return (
    // Backdrop click is a mouse convenience; Esc and the close button are the keyboard paths.
    // eslint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/no-noninteractive-element-interactions
    <dialog
      ref={ref}
      aria-labelledby={titleId}
      aria-describedby={description ? descId : undefined}
      onClose={onClose}
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
      onClick={(e) => {
        if (e.target === ref.current) onClose();
      }}
      className={cn(
        'eg-dialog m-auto max-h-[85vh] w-[calc(100vw-2rem)] overflow-hidden rounded-sm border border-line-strong bg-surface-1 p-0 text-text',
        size === 'sm' ? 'max-w-md' : size === 'md' ? 'max-w-xl' : 'max-w-3xl',
      )}
    >
      <div className="flex max-h-[85vh] flex-col">
        <header className="flex items-start gap-3 border-b border-line px-5 py-4">
          <div className="min-w-0">
            <h2 id={titleId} className="text-md font-semibold">
              {title}
            </h2>
            {description ? (
              <p id={descId} className="mt-1 text-sm text-muted">
                {description}
              </p>
            ) : null}
          </div>
          <button type="button" onClick={onClose} className="-mr-1 ml-auto rounded-xs p-1 text-muted hover:bg-surface-2 hover:text-text" aria-label="Close dialog">
            <X aria-hidden className="size-4" />
          </button>
        </header>
        {children ? <div className="min-h-0 overflow-auto px-5 py-4">{children}</div> : null}
        {footer ? <footer className="flex items-center justify-end gap-2 border-t border-line px-5 py-3">{footer}</footer> : null}
      </div>
    </dialog>
  );
}
