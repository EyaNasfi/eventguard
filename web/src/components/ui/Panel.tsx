import type { HTMLAttributes, ReactNode } from 'react';
import { cn } from '../../lib/cn';

interface PanelProps extends Omit<HTMLAttributes<HTMLElement>, 'title'> {
  title?: ReactNode;
  /** Small context next to the title, e.g. a count. */
  meta?: ReactNode;
  actions?: ReactNode;
  /** Heading level for the title (document outline). */
  level?: 2 | 3;
  bodyClassName?: string;
  as?: 'section' | 'div' | 'article' | 'aside';
}

/** Hairline-bounded region. Never nested inside another Panel. */
export function Panel({ title, meta, actions, level = 2, className, bodyClassName, children, as: Tag = 'section', ...rest }: PanelProps) {
  const H = level === 2 ? 'h2' : 'h3';
  return (
    <Tag className={cn('flex min-w-0 flex-col rounded-sm border border-line bg-surface-1', className)} {...rest}>
      {title || actions ? (
        <header className="flex min-h-11 items-center gap-3 border-b border-line px-4 py-2">
          {title ? (
            <H className="flex min-w-0 items-baseline gap-2 text-sm font-semibold">
              <span className="truncate">{title}</span>
              {meta ? <span className="text-xs font-normal text-muted">{meta}</span> : null}
            </H>
          ) : null}
          {actions ? <div className="ml-auto flex shrink-0 items-center gap-2">{actions}</div> : null}
        </header>
      ) : null}
      <div className={cn('min-h-0 flex-1', bodyClassName)}>{children}</div>
    </Tag>
  );
}

/** Label-over-value field, as on a carbon-copy form. */
export function DataField({ label, children, className, mono }: { label: string; children: ReactNode; className?: string; mono?: boolean }) {
  return (
    <div className={cn('min-w-0', className)}>
      <dt className="field-label">{label}</dt>
      <dd className={cn('mt-0.5 m-0 truncate text-sm', mono && 'mono')}>{children}</dd>
    </div>
  );
}
