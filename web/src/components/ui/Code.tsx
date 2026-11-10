import { Check, Copy } from 'lucide-react';
import { useState, type ReactNode } from 'react';
import { cn } from '../../lib/cn';

/** Pretty JSON, monochrome: keys muted, values in text colour. No decorative syntax colour. */
export function JsonBlock({ value, label, className, maxHeight = 'max-h-72' }: { value: unknown; label: string; className?: string; maxHeight?: string }) {
  const text = JSON.stringify(value, null, 2) ?? 'undefined';
  return (
    <figure className={cn('m-0 overflow-hidden rounded-sm border border-line bg-bg', className)}>
      <figcaption className="flex h-8 items-center justify-between border-b border-line pr-1 pl-3">
        <span className="field-label">{label}</span>
        <CopyButton text={text} label={`Copy ${label}`} />
      </figcaption>
      <pre className={cn('m-0 overflow-auto px-3 py-2.5 text-xs leading-relaxed', maxHeight)}>
        <code>{highlight(text)}</code>
      </pre>
    </figure>
  );
}

function highlight(text: string): ReactNode[] {
  return text.split('\n').map((line, i) => {
    const m = /^(\s*)("(?:[^"\\]|\\.)*")(:\s?)(.*)$/.exec(line);
    return (
      <span key={i} className="block">
        {m ? (
          <>
            {m[1]}
            <span className="text-muted">{m[2]}</span>
            {m[3]}
            {m[4]}
          </>
        ) : (
          line
        )}
      </span>
    );
  });
}

export function CopyButton({ text, label }: { text: string; label: string }) {
  const [done, setDone] = useState(false);
  return (
    <button
      type="button"
      aria-label={label}
      onClick={() => {
        void navigator.clipboard?.writeText(text).then(() => {
          setDone(true);
          window.setTimeout(() => setDone(false), 1400);
        });
      }}
      className="inline-flex h-6 items-center gap-1 rounded-xs px-1.5 text-xs font-semibold text-muted hover:bg-surface-2 hover:text-text"
    >
      {done ? <Check aria-hidden className="size-3 text-ok" /> : <Copy aria-hidden className="size-3" />}
      {done ? 'Copied' : 'Copy'}
    </button>
  );
}

/** A hash shown short with the full value available to copy and to screen readers. */
export function Hash({ value, chars = 8, className }: { value: string; chars?: number; className?: string }) {
  const short = value.length > chars * 2 ? `${value.slice(0, chars)}…${value.slice(-4)}` : value;
  return (
    <span className={cn('mono whitespace-nowrap', className)} title={value}>
      <span aria-hidden>{short}</span>
      <span className="sr-only">{value}</span>
    </span>
  );
}
