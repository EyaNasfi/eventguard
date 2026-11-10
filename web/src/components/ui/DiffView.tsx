import { Archive, ArchiveRestore, Link2, Plus, Send } from 'lucide-react';
import { useState } from 'react';
import type { ChangeGroup, ChangePreview } from '../../api/types';
import { cn } from '../../lib/cn';

const ENTITY: Record<ChangeGroup['entity'], [string, string]> = {
  edition: ['edition', 'editions'],
  event: ['event', 'events'],
  session: ['session', 'sessions'],
  speaker_link: ['speaker link', 'speaker links'],
  partner_link: ['partner link', 'partner links'],
  notification: ['notification', 'notifications'],
};

const OP = {
  create: { sign: '+', word: 'Create', icon: Plus, cls: 'text-ok' },
  link: { sign: '+', word: 'Link', icon: Link2, cls: 'text-ok' },
  archive: { sign: '−', word: 'Archive', icon: Archive, cls: 'text-text' },
  unarchive: { sign: '+', word: 'Unarchive', icon: ArchiveRestore, cls: 'text-ok' },
  send: { sign: '→', word: 'Send', icon: Send, cls: 'text-warn' },
} as const;

export function groupLabel(g: ChangeGroup): string {
  const [one, many] = ENTITY[g.entity];
  return `${OP[g.op].word} ${g.count} ${g.count === 1 ? one : many}`;
}

/** Summary counts plus expandable lines: what will be created, linked, archived, and what is left alone. */
export function DiffView({ preview, compact = false }: { preview: ChangePreview; compact?: boolean }) {
  const [open, setOpen] = useState<string | null>(null);
  return (
    <div className="flex flex-col">
      {/* Tiles wrap to the card's width; the -1px margins hide the outer hairlines so wrapped rows never double up. */}
      <div className="overflow-hidden border-y border-line">
      <dl className="-mr-px -mb-px grid" style={{ gridTemplateColumns: `repeat(auto-fit, minmax(${compact ? '7.5rem' : '9rem'}, 1fr))` }}>
        {preview.groups.map((g) => {
          const op = OP[g.op];
          return (
            <div key={`${g.op}-${g.entity}`} className="flex min-w-0 flex-col border-r border-b border-line px-3 py-2">
              <dt className="order-2 text-xs text-muted">
                {op.word.toLowerCase()} · {g.count === 1 ? ENTITY[g.entity][0] : ENTITY[g.entity][1]}
              </dt>
              <dd className={cn('m-0 font-mono text-lg leading-tight font-medium', op.cls)}>
                <span aria-hidden>{op.sign}</span>
                {g.count}
              </dd>
            </div>
          );
        })}
        {preview.excluded.length ? (
          <div className="flex min-w-0 flex-col border-r border-b border-line px-3 py-2">
            <dt className="order-2 text-xs text-muted">not touched</dt>
            <dd className="m-0 font-mono text-lg leading-tight font-medium text-muted">{preview.excluded.length}</dd>
          </div>
        ) : null}
      </dl>
      </div>

      <ul className="m-0 list-none p-0">
        {preview.groups
          .filter((g) => g.lines.length > 0)
          .map((g) => {
            const key = `${g.op}-${g.entity}`;
            const expanded = open === key;
            const Icon = OP[g.op].icon;
            return (
              <li key={key} className="border-b border-line">
                <button
                  type="button"
                  aria-expanded={expanded}
                  onClick={() => setOpen(expanded ? null : key)}
                  className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-surface-2"
                >
                  <Icon aria-hidden className={cn('size-3.5', OP[g.op].cls)} />
                  <span className="font-semibold">{groupLabel(g)}</span>
                  <span className="ml-auto text-xs text-muted">{expanded ? 'Hide' : 'Show'} list</span>
                </button>
                {expanded ? (
                  <ul className="m-0 max-h-56 list-none overflow-auto border-t border-line bg-bg p-0 py-1">
                    {g.lines.map((l, i) => (
                      <li key={i} className="grid grid-cols-[1.25rem_minmax(0,1fr)] gap-x-2 px-3 py-1 text-xs">
                        <span aria-hidden className={cn('font-mono', OP[l.op].cls)}>
                          {OP[l.op].sign}
                        </span>
                        <span className="min-w-0">
                          <span className="sr-only">{OP[l.op].word}: </span>
                          <span className="text-text">{l.label}</span>
                          {l.detail ? <span className="text-muted"> · {l.detail}</span> : null}
                        </span>
                      </li>
                    ))}
                  </ul>
                ) : null}
              </li>
            );
          })}
      </ul>

      {preview.excluded.length ? (
        <p className="m-0 px-3 pt-2 text-xs text-muted">
          <span className="font-semibold text-text">Not touched: </span>
          {preview.excluded.map((e, i) => (
            <span key={i}>
              {i > 0 ? '; ' : ''}
              {e.label} ({e.reason})
            </span>
          ))}
        </p>
      ) : null}
    </div>
  );
}
