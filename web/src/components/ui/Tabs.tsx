import { useRef, type KeyboardEvent, type ReactNode } from 'react';
import { cn } from '../../lib/cn';

export interface TabItem<T extends string> {
  id: T;
  label: ReactNode;
  count?: number;
  /** Count in the meaning colour, e.g. 'hold' for items needing approval (same as the nav badge). */
  countTone?: 'hold';
}

interface TabsProps<T extends string> {
  /** Shared with tabPanelProps(idBase, id). */
  idBase: string;
  label: string;
  items: TabItem<T>[];
  value: T;
  onChange: (id: T) => void;
  className?: string;
}

/** WAI-ARIA tabs with roving focus (arrows, Home, End). Panels use tabPanelProps(). */
export function Tabs<T extends string>({ idBase: base, label, items, value, onChange, className }: TabsProps<T>) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);

  const onKey = (e: KeyboardEvent<HTMLButtonElement>, i: number) => {
    const last = items.length - 1;
    const next = e.key === 'ArrowRight' ? (i === last ? 0 : i + 1) : e.key === 'ArrowLeft' ? (i === 0 ? last : i - 1) : e.key === 'Home' ? 0 : e.key === 'End' ? last : -1;
    if (next < 0) return;
    e.preventDefault();
    const item = items[next];
    if (!item) return;
    onChange(item.id);
    refs.current[next]?.focus();
  };

  return (
    <div role="tablist" aria-label={label} className={cn('flex items-end gap-1 border-b border-line', className)}>
      {items.map((item, i) => {
        const selected = item.id === value;
        return (
          <button
            key={item.id}
            ref={(el) => {
              refs.current[i] = el;
            }}
            role="tab"
            type="button"
            id={`${base}-tab-${item.id}`}
            aria-selected={selected}
            aria-controls={selected ? `${base}-panel-${item.id}` : undefined}
            tabIndex={selected ? 0 : -1}
            onClick={() => onChange(item.id)}
            onKeyDown={(e) => onKey(e, i)}
            className={cn(
              'relative -mb-px inline-flex h-9 items-center gap-2 border-b-2 px-3 text-sm font-semibold transition-colors duration-[var(--dur-fast)]',
              selected ? 'border-text text-text' : 'border-transparent text-muted hover:text-text',
            )}
          >
            {item.label}
            {item.count !== undefined ? (
              <span className={cn('rounded-xs px-1.5 font-mono text-xs', item.countTone === 'hold' && item.count ? 'border border-hold-line bg-hold-bg text-hold' : 'bg-surface-3 text-text')}>
                <span className="sr-only"> (</span>
                {item.count}
                <span className="sr-only">)</span>
              </span>
            ) : null}
          </button>
        );
      })}
    </div>
  );
}

export function tabPanelProps(baseId: string, id: string) {
  return { role: 'tabpanel' as const, id: `${baseId}-panel-${id}`, 'aria-labelledby': `${baseId}-tab-${id}`, tabIndex: 0 };
}
