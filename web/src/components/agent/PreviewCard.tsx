import { Clock, Lock, PenLine } from 'lucide-react';
import { useState } from 'react';
import type { Approval, Role } from '../../api/types';
import { cn } from '../../lib/cn';
import { fmtCountdown, fmtTime } from '../../lib/format';
import { useNow } from '../../lib/useNow';
import { Button } from '../ui/Button';
import { DiffView } from '../ui/DiffView';
import { APPROVAL } from '../ui/status';
import { StatusChip } from '../ui/StatusChip';

const FRAME: Record<Approval['status'], string> = {
  pending: 'border-hold-line bg-surface-1',
  approved: 'border-ok-line bg-surface-1',
  rejected: 'border-line bg-bg',
  expired: 'border-dashed border-warn-line bg-bg',
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
 * The write preview: exactly what will be created, linked or archived, what is left
 * alone, when the approval expires, and the single-use Approve / Reject.
 * Pending, approved, rejected and expired each read differently by frame, word and icon.
 */
export function PreviewCard({ approval, role, onDecide, live = false, headingLevel = 3, id }: PreviewCardProps) {
  const [busy, setBusy] = useState<'approve' | 'reject' | null>(null);
  const now = useNow(1000, approval.status === 'pending');
  const remaining = new Date(approval.expiresAt).getTime() - now;
  const status = approval.status === 'pending' && remaining <= 0 ? 'expired' : approval.status;
  const spec = APPROVAL[status];
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
      className={cn('eg-preview @container scroll-mt-4 rounded-sm border transition-[border-color,background-color] duration-[var(--dur-base)] ease-out', FRAME[status], live && 'eg-preview-in', status === 'rejected' && 'opacity-80')}
    >
      <header className="px-4 pt-3 pb-2.5">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <StatusChip spec={spec} key={status} className="eg-swap" />
          {status === 'pending' ? (
            <p className={cn('m-0 ml-auto flex items-center gap-1.5 text-xs', soon ? 'text-warn' : 'text-muted')}>
              <Clock aria-hidden className="size-3.5" />
              <span>{soon ? 'Less than a minute left' : `Valid until ${fmtTime(approval.expiresAt).slice(0, 5)}`}</span>
              <span className={cn('font-mono text-sm font-medium', soon ? 'text-warn' : 'text-hold')} role="timer" aria-live="off">
                {fmtCountdown(remaining)}
              </span>
            </p>
          ) : null}
        </div>
        <H id={`${approval.id}-title`} className="mt-2 text-md font-semibold">
          {approval.preview.title}
        </H>
      </header>

      <DiffView preview={approval.preview} compact />

      <footer className="flex flex-wrap items-center gap-x-3 gap-y-2 px-4 pt-3 pb-3">
        {status === 'pending' && approval.preview.note ? <p className="m-0 w-full max-w-[68ch] text-sm text-muted">{approval.preview.note}</p> : null}
        {status === 'pending' ? (
          <>
            <Button variant="primary" loading={busy === 'approve'} disabled={!canDecide || busy !== null} onClick={() => void decide(true)} icon={<PenLine aria-hidden className="size-3.5" />}>
              Approve and sign
            </Button>
            <Button disabled={!canDecide || busy !== null} loading={busy === 'reject'} onClick={() => void decide(false)}>
              Reject
            </Button>
            {!canDecide ? (
              <p className="m-0 flex items-center gap-1.5 text-xs text-muted">
                <Lock aria-hidden className="size-3.5" />
                Readers cannot approve writes. Switch to editor or admin.
              </p>
            ) : null}
          </>
        ) : null}
        {status === 'approved' ? (
          <p className="eg-swap m-0 text-sm">
            <span className="font-semibold text-ok">Signed by {approval.decidedBy}</span>
            {approval.decidedAt ? <span className="text-muted"> at {fmtTime(approval.decidedAt)}</span> : null}
            <span className="text-muted">. This approval is used up and cannot be applied again.</span>
          </p>
        ) : null}
        {status === 'rejected' ? (
          <p className="eg-swap m-0 text-sm text-muted">
            <span className="font-semibold text-text">Rejected by {approval.decidedBy ?? 'a person'}.</span> Nothing was written.
          </p>
        ) : null}
        {status === 'expired' ? (
          <p className="eg-swap m-0 text-sm text-muted">
            <span className="font-semibold text-warn">Expired without a decision.</span> Nothing was written. Ask the assistant again to get a fresh preview.
          </p>
        ) : null}
        <p
          className="m-0 ml-auto flex items-center gap-1.5 text-xs text-muted"
          title={`The signature works once and only for this exact preview. Preview hash ${approval.previewHash}${approval.signature ? `, signature ${approval.signature}` : ''}`}
        >
          <span className="font-mono">{approval.id}</span>
          <span aria-hidden>·</span>
          <span>single use, for this exact preview</span>
        </p>
      </footer>
    </section>
  );
}
