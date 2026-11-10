import { FileText, ShieldAlert } from 'lucide-react';
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
  const quarantined = excerpt.flagReason?.startsWith('Injection detector');
  return (
    <figure className="m-0 rounded-sm border border-dashed border-line-strong bg-bg">
      <figcaption className="flex flex-wrap items-center gap-x-2 gap-y-0.5 border-b border-dashed border-line-strong px-3 py-1.5">
        <FileText aria-hidden className="size-3.5 text-muted" />
        <span className="field-label text-text">Untrusted data</span>
        <span className="mono min-w-0 truncate text-xs text-muted">{excerpt.source}</span>
      </figcaption>
      <blockquote
        className={cn('m-0 max-w-[62ch] px-3 py-2 text-sm leading-relaxed break-words whitespace-pre-wrap text-muted', clamp && long && !expanded && 'line-clamp-3')}
        aria-label={`Untrusted text from ${excerpt.source}`}
      >
        {excerpt.text}
      </blockquote>
      {(clamp && long) || excerpt.flagReason ? (
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 px-3 pb-2">
          {excerpt.flagReason ? (
            <p className={cn('m-0 flex items-center gap-1.5 text-xs font-semibold', quarantined ? 'text-ok' : 'text-warn')}>
              <ShieldAlert aria-hidden className="size-3.5" />
              {excerpt.flagReason}
            </p>
          ) : null}
          {clamp && long ? (
            <button type="button" aria-expanded={expanded} onClick={() => setExpanded((e) => !e)} className="ml-auto text-xs font-semibold text-muted underline-offset-2 hover:text-text hover:underline">
              {expanded ? 'Show less' : 'Show full text'}
            </button>
          ) : null}
        </div>
      ) : null}
    </figure>
  );
}
