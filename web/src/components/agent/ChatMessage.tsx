import { Ban, BookOpenCheck, Hourglass, PenLine, ShieldAlert } from 'lucide-react';
import type { ApprovalStatus, Message } from '../../api/types';
import { cn } from '../../lib/cn';
import { fmtTime } from '../../lib/format';
import { APPROVAL, TONE_CLASS } from '../ui/status';

/** Jumps to the preview; its word and tone follow the approval's state. */
function ReviewButton({ id, status, onReview }: { id: string; status: string; onReview: (id: string) => void }) {
  const s = (status in APPROVAL ? status : 'pending') as ApprovalStatus;
  const spec = APPROVAL[s];
  const tone = TONE_CLASS[spec.tone];
  const Icon = spec.icon;
  return (
    <button
      type="button"
      onClick={() => onReview(id)}
      className={cn('inline-flex h-7 items-center gap-1.5 rounded-lg border px-2.5 text-xs font-semibold text-text hover:brightness-125 active:scale-[0.97]', tone.line, tone.bg)}
    >
      <Icon aria-hidden className={cn('size-3.5', tone.text)} />
      {s === 'pending' ? 'Review the preview' : `${spec.label}: view preview`}
      <span className="font-mono text-xs text-muted">{id}</span>
    </button>
  );
}

interface ChatMessageProps {
  message: Message;
  role: string;
  /** Status of the approval this message points to, if any. */
  approvalStatus?: string;
  onReview?: (approvalId: string) => void;
  live?: boolean;
}

export function ChatMessage({ message, role, approvalStatus, onReview, live }: ChatMessageProps) {
  if (message.author === 'user') {
    return (
      <li className={cn('ml-auto flex max-w-[90%] flex-col items-end gap-1.5', live && 'eg-msg-in')}>
        <p className="m-0 font-mono text-[0.6875rem] text-muted">
          You · {role} · {fmtTime(message.at).slice(0, 5)}
        </p>
        <p className="m-0 rounded-xl rounded-tr-sm border border-line bg-surface-2 p-3.5 text-[0.84rem] leading-relaxed text-strong shadow-sm">{message.text}</p>
      </li>
    );
  }

  if (message.author === 'oracle') {
    return (
      <li data-alarm className={cn('flex gap-2.5 rounded-xl border border-stop-line bg-stop-bg px-3 py-2 text-sm', live && 'eg-msg-in')}>
        <ShieldAlert aria-hidden className="mt-0.5 size-4 shrink-0 text-stop" />
        <div>
          <p className="m-0">
            <span className="font-semibold text-stop">Attack succeeded · </span>
            {message.text}
          </p>
          <p className="m-0 mt-0.5 text-xs text-muted">Evaluation oracle, shown in demo and bench runs only. The agent’s own reply below does not mention it.</p>
        </div>
      </li>
    );
  }

  if (message.author === 'gateway') {
    const blocked = /^Blocked|refused|quarantined/i.test(message.text);
    const Icon = blocked ? Ban : Hourglass;
    return (
      <li className={cn('flex gap-2.5 rounded-xl border px-3 py-2.5 text-sm', blocked ? 'border-stop-line bg-stop-bg' : 'border-hold-line bg-hold-bg', live && 'eg-msg-in')}>
        <Icon aria-hidden className={cn('mt-0.5 size-4 shrink-0', blocked ? 'text-stop' : 'text-hold')} />
        <p className="m-0">
          <span className={cn('font-semibold', blocked ? 'text-stop' : 'text-hold')}>Gateway · </span>
          {message.text}
        </p>
      </li>
    );
  }

  return (
    <li className={cn('mr-auto flex max-w-[96%] flex-col items-start gap-1.5', live && 'eg-msg-in')}>
      <div className="flex flex-wrap items-center gap-2">
        <span aria-hidden className="flex size-5 items-center justify-center rounded border border-brand-line bg-brand-bg font-mono text-[0.625rem] font-bold text-brand">
          EG
        </span>
        <span className="font-mono text-[0.6875rem] text-muted">
          EventGuard agent · {fmtTime(message.at).slice(0, 5)}
        </span>
        {message.approvalId && approvalStatus === 'pending' ? (
          <span className="inline-flex items-center gap-1 rounded-full border border-hold-line bg-hold-bg px-2 py-0.5 text-[0.6875rem] font-medium text-hold">
            <Hourglass aria-hidden className="size-3" />
            Awaiting human approval
          </span>
        ) : null}
      </div>
      <div className="space-y-2.5 rounded-xl rounded-tl-sm border border-line bg-surface-1 p-4 text-[0.84rem] leading-relaxed shadow-sm">
      <p className="m-0 max-w-[60ch] text-strong">{message.text}</p>
      {message.plan?.length ? (
        <ol className="m-0 flex list-none flex-col gap-1 rounded-lg border border-line bg-bg p-2.5">
          {message.plan.map((s, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-muted">
              {s.kind === 'write' ? <PenLine aria-hidden className="mt-0.5 size-3.5 shrink-0 text-text" /> : <BookOpenCheck aria-hidden className="mt-0.5 size-3.5 shrink-0" />}
              <span>
                <span className="sr-only">{s.kind === 'write' ? 'Write: ' : 'Read: '}</span>
                <span className={s.kind === 'write' ? 'text-text' : undefined}>{s.text}</span>
              </span>
            </li>
          ))}
        </ol>
      ) : null}
      {message.approvalId && onReview ? <ReviewButton id={message.approvalId} status={approvalStatus ?? 'pending'} onReview={onReview} /> : null}
      </div>
    </li>
  );
}
