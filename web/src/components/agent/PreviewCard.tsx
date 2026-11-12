import { CircleSlash, Clock, Lock, LockKeyhole, PenLine } from 'lucide-react';
import { useState } from 'react';
import type { Approval, Role } from '../../api/types';
import { cn } from '../../lib/cn';
import { fmtCountdown, fmtTime } from '../../lib/format';
import { useNow } from '../../lib/useNow';
import { Button } from '../ui/Button';
import { DiffView } from '../ui/DiffView';
import { APPROVAL, TONE_CLASS } from '../ui/status';

const FRAME: Record<Approval['status'], string> = {
  pending: 'border-hold-line bg-surface-2',
  approved: 'border-ok-line bg-surface-2',
  rejected: 'border-line bg-surface-1',
  expired: 'border-dashed border-warn-line bg-surface-1',
};

const HEADLINE: Record<Approval['status'], string> = {
  pending: 'Waiting for your approval',
  approved: 'Approved and signed',
  rejected: 'Rejected',
  expired: 'Expired without a decision',
};

interface PreviewCardProps {
  approval: Approval;
  role: Role;
  onDecide: (approve: boolean) => Promise<void>;
  /** Animate entry (live arrival only). */
  live?: boolean;
  headingLevel?: 2 | 3 | 4;
  id?: string;
}

/**
 * The write preview, raised above its call: what will be created, linked or archived,
 * what is left alone, when it expires, and the single-use Approve / Reject.
 * Pending, approved, rejected and expired read differently by frame, word and icon.
 */
export function PreviewCard({ approval, role, onDecide, live = false, headingLevel = 3, id }: PreviewCardProps) {
  const [busy, setBusy] = useState<'approve' | 'reject' | null>(null);
  const now = useNow(1000, approval.status === 'pending');
  const remaining = new Date(approval.expiresAt).getTime() - now;
  const status = approval.status === 'pending' && remaining <= 0 ? 'expired' : approval.status;
  const spec = APPROVAL[status];
  const tone = TONE_CLASS[spec.tone];
  const Icon = status === 'pending' ? LockKeyhole : spec.icon;
  const H = headingLevel === 2 ? 'h2' : headingLevel === 3 ? 'h3' : 'h4';
  const soon = remaining < 60_000;
  const canDecide = role !== 'reader';

  const decide = async (approve: boolean) => {
    setBusy(approve ? 'approve' : 'reject');
    try {
      await onDecide(approve);
    } finally {
      setBusy(null);
    }
  };

  return (
    <section
      id={id}
      tabIndex={-1}
      aria-labelledby={`${approval.id}-title`}
      className={cn('eg-preview @container scroll-mt-4 rounded-xl border p-5 transition-[border-color,background-color] duration-[var(--dur-base)] ease-out', FRAME[status], live && 'eg-preview-in', status === 'rejected' && 'opacity-85')}
    >
      <header className="flex flex-wrap items-center gap-x-3 gap-y-2 border-b border-line pb-3">
        <span aria-hidden className={cn('flex size-7 items-center justify-center rounded-md', tone.bg, tone.text)}>
          <Icon className="size-4" />
        </span>
        <p className={cn('eg-swap m-0 text-[0.9375rem] font-semibold', status === 'pending' ? 'text-strong' : tone.text)} key={status}>
          {HEADLINE[status]}
        </p>
        {status === 'pending' ? (
          <p
            className={cn(
              'm-0 ml-auto flex items-center gap-1.5 rounded-md border px-2 py-1 font-mono text-xs',
              soon ? 'border-warn-line bg-warn-bg text-warn' : 'border-hold-line bg-hold-bg text-hold',
            )}
          >
            <Clock aria-hidden className="size-3.5" />
            <span>{soon ? 'under a minute' : 'expires in'}</span>
            <span className="font-bold tabular-nums" role="timer" aria-live="off" aria-label={`${fmtCountdown(remaining)} left, valid until ${fmtTime(approval.expiresAt).slice(0, 5)}`}>
              {fmtCountdown(remaining)}
            </span>
          </p>
        ) : null}
      </header>

      <H id={`${approval.id}-title`} className="mt-3 mb-3 text-sm font-semibold text-text">
        {approval.preview.title}
      </H>

      <DiffView preview={approval.preview} compact />

      {status === 'pending' && approval.preview.note ? <p className="m-0 mt-3 max-w-[68ch] text-sm text-muted">{approval.preview.note}</p> : null}

      {status === 'pending' ? (
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <Button
            variant="primary"
            className="min-w-48 flex-1"
            loading={busy === 'approve'}
            disabled={!canDecide || busy !== null}
            onClick={() => void decide(true)}
            icon={<PenLine aria-hidden className="size-4" />}
          >
            Approve and sign
          </Button>
          <Button
            className="hover:border-stop-line hover:bg-stop-bg hover:text-stop"
            disabled={!canDecide || busy !== null}
            loading={busy === 'reject'}
            onClick={() => void decide(false)}
            icon={<CircleSlash aria-hidden className="size-4" />}
          >
            Reject
          </Button>
          {!canDecide ? (
            <p className="m-0 flex w-full items-center gap-1.5 text-xs text-muted">
              <Lock aria-hidden className="size-3.5" />
              Readers cannot approve writes. Switch to editor or admin.
            </p>
          ) : null}
        </div>
      ) : null}

      {status === 'approved' ? (
        <p className="eg-swap m-0 mt-4 text-sm">
          <span className="font-semibold text-ok">Signed by {approval.decidedBy}</span>
          {approval.decidedAt ? <span className="text-muted"> at {fmtTime(approval.decidedAt)}</span> : null}
          <span className="text-muted">. This approval is used up and cannot be applied again.</span>
        </p>
      ) : null}
      {status === 'rejected' ? (
        <p className="eg-swap m-0 mt-4 text-sm text-muted">
          <span className="font-semibold text-text">Rejected by {approval.decidedBy ?? 'a person'}.</span> Nothing was written.
        </p>
      ) : null}
      {status === 'expired' ? (
        <p className="eg-swap m-0 mt-4 text-sm text-muted">
          <span className="font-semibold text-warn">Nothing was written.</span> Ask the assistant again to get a fresh preview.
        </p>
      ) : null}

      <footer
        className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-line pt-3 font-mono text-xs text-muted"
        title={`The signature works once and only for this exact preview. Preview hash ${approval.previewHash}${approval.signature ? `, signature ${approval.signature}` : ''}`}
      >
        <span className="flex items-center gap-1.5">
          <Lock aria-hidden className="size-3.5 text-ok" />
          Single-use signature bound to this exact preview
        </span>
        <span>
          {approval.id} · hash {approval.previewHash.slice(0, 4)}…{approval.previewHash.slice(-4)}
        </span>
      </footer>
    </section>
  );
}
