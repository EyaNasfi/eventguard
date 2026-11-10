import { ChevronRight, CircleCheck, FileSearch, ShieldAlert, ShieldOff } from 'lucide-react';
import { useState } from 'react';
import { Link } from 'react-router';
import { presetLayers } from '../../api/gateway-model';
import type { Approval, Role, ToolCall } from '../../api/types';
import { cn } from '../../lib/cn';
import { fmtArgs, fmtTime } from '../../lib/format';
import { JsonBlock } from '../ui/Code';
import { buttonClass } from '../ui/Button';
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

const EXECUTED: StatusSpec = { tone: 'ok', label: 'Approved and executed', icon: CircleCheck };

interface CueSheetProps {
  calls: ToolCall[];
  approvals: Record<string, Approval>;
  role: Role;
  live: ReadonlySet<string>;
  onDecide: (approvalId: string, approve: boolean) => Promise<void>;
}

/**
 * The agent's run as a calling script: numbered cues in the margin, one tool call per
 * cue line, writes held at the gateway until a person approves.
 */
export function CueSheet({ calls, approvals, role, live, onDecide }: CueSheetProps) {
  const seenApprovals = new Set<string>();
  return (
    <ol className="eg-script relative m-0 list-none p-0">
      {calls.map((call, i) => {
        const approval = call.approvalId ? approvals[call.approvalId] : undefined;
        const showCard = Boolean(approval && !seenApprovals.has(approval.id));
        const coveredBy = approval && !showCard ? approval.id : undefined;
        if (approval) seenApprovals.add(approval.id);
        return (
          <CueLine
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

function CueLine({
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

  return (
    <li className={cn('grid grid-cols-[4.5rem_minmax(0,1fr)] sm:grid-cols-[5.5rem_minmax(0,1fr)]', live && 'eg-cue-in')} aria-label={`Step ${n}: ${call.tool}, ${spec.label}`} data-alarm={alarm || undefined}>
      <div className="pt-3 pl-4 sm:pl-6">
        <span aria-hidden className={cn('block font-mono text-[1.75rem] leading-none font-light tracking-[-0.03em] transition-colors duration-[var(--dur-base)] ease-out', NUMBER_TONE[state], state === 'allowed' && 'opacity-70')}>
          {n}
        </span>
        <span className="mt-1.5 block text-xs text-muted tabular-nums">{fmtTime(call.requestedAt)}</span>
      </div>

      <div className="min-w-0 border-b border-line py-3 pr-4 pl-4 sm:pr-6 sm:pl-5">
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <h3 className="m-0 font-mono text-[0.84rem] font-semibold">
            {call.tool}
            {call.batch ? <span className="ml-1 font-normal text-muted">×{call.batch}</span> : null}
          </h3>
          <span className="ml-auto flex min-w-0 items-baseline gap-2" key={`${state}`}>
            <StatusChip spec={spec} variant="plain" size="sm" className={live ? 'eg-verdict-in' : 'eg-swap'} />
            {call.verdict.rule && state === 'blocked' ? <span className="mono truncate text-xs text-muted">{call.verdict.rule}</span> : null}
          </span>
        </div>

        {argsText ? (
          <p className="mono m-0 mt-0.5 truncate text-xs text-muted" title={argsText}>
            {argsText}
          </p>
        ) : null}

        {state === 'blocked' ? (
          <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-2">
            <p className="m-0 flex items-start gap-1.5 text-sm text-stop">
              <ShieldOff aria-hidden className="mt-0.5 size-4 shrink-0" />
              <span>
                <span className="font-semibold">Blocked at the gateway:</span> <span className="text-text">{call.verdict.reason}</span>. Nothing was executed.
              </span>
            </p>
            {audited ? <AuditButton id={call.id} /> : null}
          </div>
        ) : state === 'rejected' ? (
          <p className="m-0 mt-1 text-sm text-muted">
            <span className="font-semibold text-text">Rejected{approval?.decidedBy ? ` by ${approval.decidedBy}` : ''}.</span> Nothing was executed.
          </p>
        ) : state === 'expired' ? (
          <p className="m-0 mt-1 text-sm text-muted">
            <span className="font-semibold text-warn">Approval expired.</span> Nothing was executed.
          </p>
        ) : call.result ? (
          <p className="m-0 mt-1 text-sm text-muted">{call.result.summary}</p>
        ) : null}

        <div className="mt-2">
          <CheckTrail checkpoints={call.verdict.checkpoints} live={live} {...(coveredBy ? { coveredBy } : {})} />
        </div>

        {call.oracle ? (
          <div role="alert" className={cn('mt-2.5 rounded-sm border border-stop-line bg-stop-bg px-3 py-2', live && 'eg-verdict-in')}>
            <p className="m-0 flex items-center gap-1.5 text-sm font-semibold text-stop">
              <ShieldAlert aria-hidden className="size-4" />
              Attack succeeded: data left the organisation
            </p>
            <p className="m-0 mt-0.5 text-sm text-text">{call.oracle.finding}</p>
            <p className="m-0 mt-1 text-xs text-muted">Evaluation oracle finding. In production nothing flags this under {call.config}: the gateway let it through, and {call.config} keeps no audit entry.</p>
          </div>
        ) : null}

        {call.result?.redacted?.length ? (
          <p className="m-0 mt-2 text-xs text-muted">
            <span className="font-semibold text-text">Output filter withheld:</span> <span className="mono">{call.result.redacted.join(', ')}</span>
          </p>
        ) : null}

        {call.result?.untrusted?.length ? (
          <div className="mt-2.5 flex flex-col gap-2">
            {call.result.untrusted.map((u) => (
              <UntrustedText key={u.source} excerpt={u} />
            ))}
          </div>
        ) : null}

        {showCard && approval ? (
          <div className="mt-3">
            <PreviewCard id={`preview-${approval.id}`} headingLevel={4} approval={approval} role={role} live={live} onDecide={(ok) => onDecide(approval.id, ok)} />
          </div>
        ) : null}

        <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1">
          <button type="button" aria-expanded={open} onClick={() => setOpen((o) => !o)} className="-ml-1 inline-flex h-6 items-center gap-1 rounded-xs px-1 text-xs font-semibold text-muted hover:text-text">
            <ChevronRight aria-hidden className={cn('size-3.5 transition-transform duration-[var(--dur-fast)] ease-out motion-reduce:transition-none', open && 'rotate-90')} />
            {open ? 'Hide' : 'Show'} arguments and result
          </button>
          <span className="font-mono text-xs text-muted">{call.id}</span>
          {audited ? (
            <Link to={`/audit?q=${encodeURIComponent(call.id)}`} className="inline-flex items-center gap-1 text-xs font-semibold text-muted hover:text-text">
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
      </div>
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
