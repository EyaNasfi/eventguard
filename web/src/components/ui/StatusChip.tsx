import type { ReactNode } from 'react';
import { cn } from '../../lib/cn';
import { TONE_CLASS, type StatusSpec, type Tone } from './status';

interface StatusChipProps {
  spec: StatusSpec;
  /** Overrides the spec's word. */
  label?: ReactNode;
  /** "stamp": uppercase boxed word for checkpoint trails; "chip": sentence case. */
  variant?: 'chip' | 'stamp' | 'plain';
  size?: 'sm' | 'md';
  className?: string;
  title?: string;
}

export function StatusChip({ spec, label, variant = 'chip', size = 'md', className, title }: StatusChipProps) {
  const t = TONE_CLASS[spec.tone];
  const Icon = spec.icon;
  if (variant === 'plain') {
    return (
      <span className={cn('inline-flex items-center gap-1.5 font-semibold', t.text, size === 'sm' ? 'text-xs' : 'text-sm', className)} title={title}>
        <Icon aria-hidden className={size === 'sm' ? 'size-3.5' : 'size-4'} strokeWidth={2.2} />
        {label ?? spec.label}
      </span>
    );
  }
  return (
    <span
      title={title}
      className={cn(
        'inline-flex max-w-full items-center gap-1 border font-medium whitespace-nowrap',
        t.text,
        t.line,
        t.bg,
        variant === 'stamp' ? cn('rounded-md px-1.5 font-mono uppercase tracking-[0.06em]', size === 'sm' ? 'text-2xs' : 'text-xs') : cn('rounded-full font-mono', size === 'sm' ? 'h-5 px-2 text-[0.6875rem]' : 'h-6 px-2.5 text-xs'),
        variant === 'stamp' && (size === 'sm' ? 'h-5' : 'h-6'),
        className,
      )}
    >
      <Icon aria-hidden className={variant === 'stamp' || size === 'sm' ? 'size-3' : 'size-3.5'} strokeWidth={2.4} />
      <span className="truncate">{label ?? spec.label}</span>
    </span>
  );
}

const DOT: Record<Tone, string> = { ok: 'bg-ok', hold: 'bg-hold', stop: 'bg-stop', warn: 'bg-warn', info: 'bg-info', neutral: 'bg-muted' };

/** Decorative dot; always next to a word. */
export function ToneDot({ tone }: { tone: Tone }) {
  return <span aria-hidden className={cn('inline-block size-2 shrink-0 rounded-full', DOT[tone])} />;
}
