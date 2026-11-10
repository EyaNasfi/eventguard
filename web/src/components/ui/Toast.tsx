import { X } from 'lucide-react';
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { cn } from '../../lib/cn';
import { TONE_CLASS, type StatusSpec } from './status';

interface ToastItem {
  id: number;
  spec: StatusSpec;
  title: string;
  body?: ReactNode;
}

interface ToastApi {
  show: (spec: StatusSpec, title: string, body?: ReactNode) => void;
}

const ToastContext = createContext<ToastApi | null>(null);

export function useToast(): ToastApi {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast outside ToastProvider');
  return ctx;
}

const TTL = 5200;

/** Toasts announce outcomes of actions the user took elsewhere on screen (polite live region). */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const seq = useRef(0);

  const dismiss = useCallback((id: number) => setItems((xs) => xs.filter((x) => x.id !== id)), []);
  const show = useCallback<ToastApi['show']>((spec, title, body) => {
    seq.current += 1;
    const id = seq.current;
    setItems((xs) => [...xs.slice(-3), { id, spec, title, ...(body ? { body } : {}) }]);
  }, []);
  const value = useMemo(() => ({ show }), [show]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <section aria-label="Notifications" className="pointer-events-none fixed right-4 bottom-4 z-50 flex w-[22rem] max-w-[calc(100vw-2rem)] flex-col gap-2">
        <div role="status" aria-live="polite" className="contents">
          {items.map((t) => (
            <Toast key={t.id} item={t} onDismiss={() => dismiss(t.id)} />
          ))}
        </div>
      </section>
    </ToastContext.Provider>
  );
}

function Toast({ item, onDismiss }: { item: ToastItem; onDismiss: () => void }) {
  const [paused, setPaused] = useState(false);
  useEffect(() => {
    if (paused) return;
    const t = window.setTimeout(onDismiss, TTL);
    return () => window.clearTimeout(t);
  }, [paused, onDismiss]);
  const tone = TONE_CLASS[item.spec.tone];
  const Icon = item.spec.icon;
  return (
    // Hover pause mirrors the focus pause below; it adds no action of its own.
    // eslint-disable-next-line jsx-a11y/no-static-element-interactions
    <div
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocus={() => setPaused(true)}
      onBlur={() => setPaused(false)}
      className="eg-toast pointer-events-auto flex items-start gap-3 rounded-sm border border-line-strong bg-surface-2 px-3.5 py-3"
    >
      <Icon aria-hidden className={cn('mt-0.5 size-4 shrink-0', tone.text)} strokeWidth={2.4} />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold">
          <span className={cn('mr-1.5', tone.text)}>{item.spec.label}:</span>
          {item.title}
        </p>
        {item.body ? <div className="mt-0.5 text-xs text-muted">{item.body}</div> : null}
      </div>
      <button type="button" onClick={onDismiss} aria-label="Dismiss notification" className="-mr-1.5 -mt-0.5 rounded-xs p-1.5 text-muted hover:text-text">
        <X aria-hidden className="size-3.5" />
      </button>
    </div>
  );
}
