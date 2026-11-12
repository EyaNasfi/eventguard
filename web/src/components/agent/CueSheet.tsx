import { ChevronRight, CircleCheck, FileSearch, ShieldAlert, ShieldOff } from 'lucide-react';
import { useState } from 'react';
import { Link } from 'react-router';
import { presetLayers } from '../../api/gateway-model';
import type { Approval, Role, ToolCall } from '../../api/types';
import { cn } from '../../lib/cn';
import { fmtArgs, fmtTime } from '../../lib/format';
import { buttonClass } from '../ui/Button';
import { JsonBlock } from '../ui/Code';
import { APPROVAL, DECISION, NUMERAL_TONE, type StatusSpec } from '../ui/status';
import { StatusChip } from '../ui/StatusChip';
import { CheckTrail } from './CheckTrail';
import { PreviewCard } from './PreviewCard';
import { UntrustedText } from './UntrustedText';

type CueState = 'allowed' | 'held' | 'blocked' | 'executed' | 'leaked' | 'rejected' | 'expired';

function cueState(call: ToolCall, approval: Approval | undefined): CueState {
  if (call.oracle) return 'leaked';
  // A person saying no is a decision, not a security block.
  if (approval?.status === 'rejected' || call.verdict.rule === 'preview_approval.rejected') return 'rejected';
  if (approval?.status === 'expired') return 'expired';
  if (call.verdict.decision === 'blocked') return 'blocked';
  if (call.verdict.decision === 'needs_approval') return 'held';
  if (approval?.status === 'approved' && call.result?.status === 'ok') return 'executed';
  return 'allowed';
}

const NUMBER_TONE: Record<CueState, string> = { ...NUMERAL_TONE, held: NUMERAL_TONE.needs_approval };

const FRAME: Record<CueState, string> = {
  allowed: 'border-line',
  executed: 'border-line',
  held: 'border-hold-line shadow-lg shadow-black/25',
  blocked: 'border-stop-line',
  leaked: 'border-stop-line',
  rejected: 'border-line',
  expired: 'border-dashed border-warn-line',
};

const EXECUTED: StatusSpec = { tone: 'ok', label: 'Approved and executed', icon: CircleCheck };

interface CueSheetProps {
  calls: ToolCall[];
  approvals: Record<string, Approval>;
  role: Role;
  live: ReadonlySet<string>;
  onDecide: (approvalId: string, approve: boolean) => Promise<void>;
}

/** The agent's run: one numbered card per tool call; writes are held until a person approves. */
export function CueSheet({ calls, approvals, role, live, onDecide }: CueSheetProps) {
  const seenApprovals = new Set<string>();
  return (
    <ol className="m-0 flex list-none flex-col gap-3 p-0">
      {calls.map((call, i) => {
        const approval = call.approvalId ? approvals[call.approvalId] : undefined;
        const showCard = Boolean(approval && !seenApprovals.has(approval.id));
        const coveredBy = approval && !showCard ? approval.id : undefined;
        if (approval) seenApprovals.add(approval.id);
        return (
          <CallCard
            key={call.id}
            n={i + 1}
            call={call}
            approval={approval}
            showCard={showCard}
            {...(coveredBy ? { coveredBy } : {})}
            role={role}
            live={live.has(call.id)}
            onDecide={onDecide}
          />
        );
      })}
    </ol>
  );
}

function CallCard({
  n,
  call,
  approval,
  showCard,
  coveredBy,
  role,
  live,
  onDecide,
}: {
  n: number;
  call: ToolCall;
  approval: Approval | undefined;
  showCard: boolean;
  coveredBy?: string;
  role: Role;
  live: boolean;
  onDecide: CueSheetProps['onDecide'];
}) {
  const [open, setOpen] = useState(false);
  const state = cueState(call, approval);
  const spec = state === 'executed' ? EXECUTED : state === 'rejected' ? APPROVAL.rejected : state === 'expired' ? APPROVAL.expired : DECISION[call.verdict.decision];
  const alarm = state === 'blocked' || state === 'leaked';
  const audited = presetLayers(call.config).audit_log;
  const argsText = fmtArgs(call.args);
  // Reads stay compact; the checkpoint trail is evidence where something was decided.
  const showTrail = state !== 'allowed' && state !== 'executed';

  return (
    <li
      className={cn('rounded-xl border bg-surface-1 p-4 transition-[border-color] duration-[var(--dur-base)] ease-out', FRAME[state], live && 'eg-cue-in')}
      aria-label={`Step ${n}: ${call.tool}, ${spec.label}`}
      data-alarm={alarm || undefined}
    >
      <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1.5">
        <span aria-hidden className={cn('font-mono text-xs tabular-nums', NUMBER_TONE[state])}>
          {String(n).padStart(2, '0')}
        </span>
        <h3 className={cn('m-0 rounded-md border bg-surface-2 px-2 py-0.5 font-mono text-[0.8125rem] font-semibold text-strong', state === 'held' ? 'border-hold-line' : 'border-line')}>
          {call.tool}
          {call.batch ? <span className="ml-1 font-normal text-muted">×{call.batch}</span> : null}
        </h3>
        {argsText ? (
          <span className="mono min-w-0 flex-1 truncate text-xs text-muted" title={argsText}>
            ({argsText})
          </span>
        ) : (
          <span className="mono flex-1 text-xs text-muted">()</span>
        )}
        <span className="ml-auto flex shrink-0 items-center gap-2.5" key={state}>
          <span className="font-mono text-xs text-muted tabular-nums">{fmtTime(call.requestedAt)}</span>
          {call.verdict.rule && state === 'blocked' ? (
            <span className="hidden rounded-md border border-stop-line bg-stop-bg px-2 py-0.5 font-mono text-xs text-stop 2xl:inline">{call.verdict.rule}</span>
          ) : null}
          <StatusChip spec={spec} size="sm" className={live ? 'eg-verdict-in' : 'eg-swap'} />
        </span>
      </div>

      {state === 'blocked' ? (
        <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-2">
          <p className="m-0 flex items-start gap-1.5 text-sm text-stop">
            <ShieldOff aria-hidden className="mt-0.5 size-4 shrink-0" />
            <span>
              <span className="font-semibold">Blocked at the gateway:</span> <span className="text-text">{call.verdict.reason}</span>. Nothing was executed.
              {call.verdict.rule ? <span className="mono ml-1 text-xs text-muted 2xl:hidden">({call.verdict.rule})</span> : null}
            </span>
          </p>
          {audited ? <AuditButton id={call.id} /> : null}
        </div>
      ) : state === 'rejected' ? (
        <p className="m-0 mt-2.5 text-sm text-muted">
          <span className="font-semibold text-text">Rejected{approval?.decidedBy ? ` by ${approval.decidedBy}` : ''}.</span> Nothing was executed.
        </p>
      ) : state === 'expired' ? (
        <p className="m-0 mt-2.5 text-sm text-muted">
          <span className="font-semibold text-warn">Approval expired.</span> Nothing was executed.
        </p>
      ) : call.result ? (
        <p className="m-0 mt-2 text-sm text-muted">{call.result.summary}</p>
      ) : null}

      {showTrail || open ? (
        <div className="mt-3">
          <CheckTrail checkpoints={call.verdict.checkpoints} live={live} {...(coveredBy ? { coveredBy } : {})} />
        </div>
      ) : null}

      {call.oracle ? (
        <div role="alert" className={cn('mt-3 rounded-lg border border-stop-line bg-stop-bg px-3 py-2.5', live && 'eg-verdict-in')}>
          <p className="m-0 flex items-center gap-1.5 text-sm font-semibold text-stop">
            <ShieldAlert aria-hidden className="size-4" />
            Attack succeeded: data left the organisation
          </p>
          <p className="m-0 mt-0.5 text-sm text-strong">{call.oracle.finding}</p>
          <p className="m-0 mt-1 text-xs text-muted">Evaluation oracle finding. In production nothing flags this under {call.config}: the gateway let it through, and {call.config} keeps no audit entry.</p>
        </div>
      ) : null}

      {call.result?.redacted?.length ? (
        <p className="m-0 mt-2 text-xs text-muted">
          <span className="font-semibold text-text">Output filter withheld:</span> <span className="mono">{call.result.redacted.join(', ')}</span>
        </p>
      ) : null}

      {call.result?.untrusted?.length ? (
        <div className="mt-3 flex flex-col gap-2">
          {call.result.untrusted.map((u) => (
            <UntrustedText key={u.source} excerpt={u} />
          ))}
        </div>
      ) : null}

      {showCard && approval ? (
        <div className="mt-4">
          <PreviewCard id={`preview-${approval.id}`} headingLevel={4} approval={approval} role={role} live={live} onDecide={(ok) => onDecide(approval.id, ok)} />
        </div>
      ) : null}

      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-line pt-2.5">
        <button type="button" aria-expanded={open} onClick={() => setOpen((o) => !o)} className="-ml-1 inline-flex h-6 items-center gap-1 rounded-md px-1 text-xs font-medium text-muted hover:text-text">
          <ChevronRight aria-hidden className={cn('size-3.5 transition-transform duration-[var(--dur-fast)] ease-out motion-reduce:transition-none', open && 'rotate-90')} />
          {open ? 'Hide' : 'Show'} details
        </button>
        <span className="font-mono text-xs text-muted">{call.id}</span>
        {audited ? (
          <Link to={`/audit?q=${encodeURIComponent(call.id)}`} className="inline-flex items-center gap-1 text-xs font-medium text-muted hover:text-text">
            <FileSearch aria-hidden className="size-3.5" />
            Audit entry
          </Link>
        ) : (
          <span className="text-xs text-muted">Not in the audit log ({call.config} has it off)</span>
        )}
      </div>
      {open ? (
        <div className="mt-2 grid gap-2 lg:grid-cols-2">
          <JsonBlock label="Arguments" value={call.args} maxHeight="max-h-48" />
          <JsonBlock label="Result" value={call.result ?? { status: 'pending' }} maxHeight="max-h-48" />
        </div>
      ) : null}
    </li>
  );
}

function AuditButton({ id }: { id: string }) {
  return (
    <Link to={`/audit?q=${encodeURIComponent(id)}`} className={buttonClass('secondary', 'sm')}>
      <FileSearch aria-hidden className="size-3.5" />
      Open audit entry
    </Link>
  );
}
