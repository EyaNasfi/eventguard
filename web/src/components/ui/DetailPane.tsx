import { useId, type ReactNode } from 'react';
import { cn } from '../../lib/cn';

/** Grid used by every list + detail page, so detail panes have one width everywhere. */
export const LIST_DETAIL_GRID = 'grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(24rem,32rem)]';

interface DetailPaneProps {
  title: ReactNode;
  /** Small line under the title (ids, kind). */
  meta?: ReactNode;
  /** Status at the right of the header (a boxed StatusChip). */
  status?: ReactNode;
  /** Shown above the body, e.g. an urgent finding that must not be scrolled away. */
  lead?: ReactNode;
  footer?: ReactNode;
  children?: ReactNode;
  /** Frame tone, e.g. 'border-stop-line' when the item is the problem. */
  frameClassName?: string;
  /** No frame and no header: a sticky column for content that brings its own (e.g. PreviewCard). */
  bare?: boolean;
  label?: string;
}

/**
 * The detail pane beside a list: sticky on wide screens, capped to the viewport with
 * its own scroll so nothing important ends below the fold.
 */
export function DetailPane({ title, meta, status, lead, footer, children, frameClassName, bare, label }: DetailPaneProps) {
  const id = useId();
  const sticky = 'xl:sticky xl:top-4 xl:max-h-[calc(100dvh-6rem)] xl:self-start xl:overflow-auto';
  if (bare) {
    return (
      <aside aria-labelledby={id} className={cn('flex min-w-0 flex-col gap-3', sticky)}>
        <h2 id={id} className="sr-only">
          {label ?? title}
        </h2>
        {children}
      </aside>
    );
  }
  return (
    <aside aria-labelledby={id} className={cn('flex min-w-0 flex-col rounded-sm border bg-surface-1', frameClassName ?? 'border-line', sticky)}>
      <header className="flex flex-wrap items-start gap-3 border-b border-line px-4 py-3">
        <div className="min-w-0 flex-1">
          <h2 id={id} className="m-0 text-md font-semibold">
            {title}
          </h2>
          {meta ? <p className="m-0 text-xs text-muted">{meta}</p> : null}
        </div>
        {status}
      </header>
      {lead}
      {children}
      {footer ? <footer className="mt-auto flex flex-wrap items-center gap-3 border-t border-line px-4 py-3">{footer}</footer> : null}
    </aside>
  );
}
