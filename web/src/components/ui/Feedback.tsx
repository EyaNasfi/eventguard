import { TriangleAlert, type LucideIcon } from 'lucide-react';
import type { ReactNode } from 'react';
import { cn } from '../../lib/cn';
import { Button } from './Button';

/** Empty states teach the next action rather than saying "nothing here". */
export function EmptyState({ icon: Icon, title, children, action, className }: { icon: LucideIcon; title: string; children?: ReactNode; action?: ReactNode; className?: string }) {
  return (
    <div className={cn('flex flex-col items-start gap-3 px-6 py-10', className)}>
      <Icon aria-hidden className="size-5 text-muted" strokeWidth={1.8} />
      <div className="max-w-[46ch]">
        <p className="text-md font-semibold">{title}</p>
        {children ? <div className="mt-1 text-sm text-muted">{children}</div> : null}
      </div>
      {action}
    </div>
  );
}

export function ErrorState({ title = 'This could not load', error, onRetry, className }: { title?: string; error: unknown; onRetry?: () => void; className?: string }) {
  const message = error instanceof Error ? error.message : String(error);
  return (
    <div role="alert" className={cn('flex flex-col items-start gap-3 px-6 py-8', className)}>
      <p className="flex items-center gap-2 text-sm font-semibold text-warn">
        <TriangleAlert aria-hidden className="size-4" />
        {title}
      </p>
      <p className="mono max-w-[70ch] text-xs break-words text-muted">{message}</p>
      {onRetry ? (
        <Button size="sm" onClick={onRetry}>
          Try again
        </Button>
      ) : null}
    </div>
  );
}

/** Loading placeholder shaped like the content; static under reduced motion. */
export function Skeleton({ className, lines }: { className?: string; lines?: number }) {
  if (lines) {
    return (
      <div aria-hidden className={cn('flex flex-col gap-2', className)}>
        {Array.from({ length: lines }, (_, i) => (
          <div key={i} className="eg-skeleton h-3 rounded-xs" style={{ width: `${92 - ((i * 23) % 40)}%` }} />
        ))}
      </div>
    );
  }
  return <div aria-hidden className={cn('eg-skeleton rounded-xs', className)} />;
}

export function LoadingRegion({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div role="status" aria-live="polite" aria-busy="true">
      <span className="sr-only">{label}</span>
      {children}
    </div>
  );
}
