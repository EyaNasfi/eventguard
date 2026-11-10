import { ArrowDown, ArrowUp, ArrowUpDown } from 'lucide-react';
import type { HTMLAttributes, ReactNode, TdHTMLAttributes, ThHTMLAttributes } from 'react';
import { cn } from '../../lib/cn';

export function Table({ caption, className, children, captionHidden = true, ...rest }: HTMLAttributes<HTMLTableElement> & { caption: string; captionHidden?: boolean }) {
  return (
    <table className={cn('w-full border-collapse text-left text-sm', className)} {...rest}>
      <caption className={cn(captionHidden ? 'sr-only' : 'px-4 py-2 text-left text-xs text-muted caption-bottom')}>{caption}</caption>
      {children}
    </table>
  );
}

export function THead({ children, sticky = true }: { children: ReactNode; sticky?: boolean }) {
  return <thead className={cn('bg-surface-1', sticky && 'sticky top-0 z-[1]')}>{children}</thead>;
}

export type SortDir = 'asc' | 'desc';

interface ThProps extends ThHTMLAttributes<HTMLTableCellElement> {
  sort?: { active: boolean; dir: SortDir; onSort: () => void };
  numeric?: boolean;
}

export function Th({ children, sort, numeric, className, ...rest }: ThProps) {
  const ariaSort = sort?.active ? (sort.dir === 'asc' ? 'ascending' : 'descending') : sort ? 'none' : undefined;
  const Icon = sort?.active ? (sort.dir === 'asc' ? ArrowUp : ArrowDown) : ArrowUpDown;
  return (
    <th
      scope="col"
      aria-sort={ariaSort}
      className={cn('field-label h-9 border-b border-line px-3 align-middle font-semibold whitespace-nowrap', numeric && 'text-right', className)}
      {...rest}
    >
      {sort ? (
        <button
          type="button"
          onClick={sort.onSort}
          className={cn('-mx-1 inline-flex items-center gap-1 rounded-xs px-1 uppercase hover:text-text', sort.active && 'text-text', numeric && 'flex-row-reverse')}
        >
          {children}
          <Icon aria-hidden className={cn('size-3', !sort.active && 'opacity-50')} />
        </button>
      ) : (
        children
      )}
    </th>
  );
}

export function Td({ children, numeric, className, ...rest }: TdHTMLAttributes<HTMLTableCellElement> & { numeric?: boolean }) {
  return (
    <td className={cn('h-10 border-b border-line px-3 align-middle', numeric && 'text-right tabular-nums', className)} {...rest}>
      {children}
    </td>
  );
}

export function Tr({ children, className, selected, ...rest }: HTMLAttributes<HTMLTableRowElement> & { selected?: boolean }) {
  return (
    <tr
      data-selected={selected || undefined}
      className={cn('transition-colors duration-[var(--dur-fast)] hover:bg-surface-2/60', selected && 'bg-surface-2', className)}
      {...rest}
    >
      {children}
    </tr>
  );
}
