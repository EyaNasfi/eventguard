import { ShieldAlert, TriangleAlert } from 'lucide-react';
import { useState } from 'react';
import type { UntrustedExcerpt } from '../../api/types';
import { cn } from '../../lib/cn';

/**
 * Text that came from records or tool results. Always framed and labelled as data:
 * rendered as plain text (never as links or markup), with its source and what the
 * gateway did with it.
 */
export function UntrustedText({ excerpt, clamp = true }: { excerpt: UntrustedExcerpt; clamp?: boolean }) {
  const [expanded, setExpanded] = useState(false);
  const long = excerpt.text.length > 180;
  // Flagged text is the evidence: show it whole.
  const clamped = clamp && long && !excerpt.flagged && !expanded;
  const quarantined = excerpt.flagReason?.startsWith('Injection detector');
  return (
    <figure className="m-0 space-y-1.5 rounded-lg border border-l-4 border-line border-l-hold bg-surface-2/70 p-3 text-xs">
      <figcaption className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
        <span className="flex items-center gap-1.5 font-mono text-[0.6875rem] font-semibold tracking-wide text-hold uppercase">
          <TriangleAlert aria-hidden className="size-3.5" />
          Untrusted data · {excerpt.source}
        </span>
        <span className="font-mono text-[0.6875rem] text-muted">Shown as data, never as instructions</span>
      </figcaption>
      <blockquote
        className={cn('m-0 max-w-[72ch] rounded-md border border-line bg-bg p-2 font-mono text-[0.75rem] leading-relaxed break-words whitespace-pre-wrap text-text', clamped && 'line-clamp-3')}
        aria-label={`Untrusted text from ${excerpt.source}`}
      >
        “{excerpt.text}”
      </blockquote>
      {excerpt.flagReason || (clamp && long && !excerpt.flagged) ? (
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          {excerpt.flagReason ? (
            <p className={cn('m-0 flex items-center gap-1.5 text-xs', quarantined ? 'text-ok' : 'text-muted')}>
              <ShieldAlert aria-hidden className="size-3.5" />
              {excerpt.flagReason}
            </p>
          ) : null}
          {clamp && long && !excerpt.flagged ? (
            <button type="button" aria-expanded={expanded} onClick={() => setExpanded((e) => !e)} className="ml-auto text-xs font-medium text-muted underline-offset-2 hover:text-text hover:underline">
              {expanded ? 'Show less' : 'Show full text'}
            </button>
          ) : null}
        </div>
      ) : null}
    </figure>
  );
}
