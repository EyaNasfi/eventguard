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
      className={cn('mt-2.5 inline-flex h-7 items-center gap-1.5 rounded-sm border px-2.5 text-xs font-semibold text-text hover:brightness-125 active:scale-[0.97]', tone.line, tone.bg)}
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
      <li className={cn('flex flex-col items-end', live && 'eg-msg-in')}>
        <p className="m-0 mb-1 text-xs text-muted">
          <span className="font-semibold text-text">You</span> · {role} · {fmtTime(message.at)}
        </p>
        <p className="m-0 max-w-[34ch] rounded-sm border border-line bg-surface-1 px-3.5 py-2.5 text-[0.9rem] leading-relaxed sm:max-w-[40ch]">{message.text}</p>
      </li>
    );
  }

  if (message.author === 'oracle') {
    return (
      <li data-alarm className={cn('flex gap-2.5 rounded-sm border border-stop-line bg-stop-bg px-3 py-2 text-sm', live && 'eg-msg-in')}>
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
      <li className={cn('flex gap-2.5 rounded-sm border px-3 py-2 text-sm', blocked ? 'border-stop-line bg-stop-bg' : 'border-hold-line bg-hold-bg', live && 'eg-msg-in')}>
        <Icon aria-hidden className={cn('mt-0.5 size-4 shrink-0', blocked ? 'text-stop' : 'text-hold')} />
        <p className="m-0">
          <span className={cn('font-semibold', blocked ? 'text-stop' : 'text-hold')}>Gateway · </span>
          {message.text}
        </p>
      </li>
    );
  }

  return (
    <li className={cn('flex flex-col items-start', live && 'eg-msg-in')}>
      <p className="m-0 mb-1 text-xs text-muted">
        <span className="font-semibold text-text">Agent</span> · {fmtTime(message.at)}
      </p>
      <p className="m-0 max-w-[60ch] text-[0.9rem] leading-relaxed">{message.text}</p>
      {message.plan?.length ? (
        <ol className="m-0 mt-2 flex list-none flex-col gap-1 border-l border-line-strong p-0 pl-3">
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
    </li>
  );
}
