/**
 * One vocabulary for every state in the product. A state is always rendered as
 * icon + word (never colour alone); tone only reinforces it.
 */
import {
  Archive,
  ArchiveRestore,
  Ban,
  CircleCheck,
  CircleDot,
  CircleDashed,
  CircleSlash,
  Clock,
  Hourglass,
  Info,
  Loader,
  PenLine,
  ShieldAlert,
  ShieldCheck,
  TriangleAlert,
  type LucideIcon,
} from 'lucide-react';
import type { ApprovalStatus, AttackOutcome, AuditEntry, CheckOutcome, Decision, RecordStatus, RunStatus } from '../../api/types';

export type Tone = 'ok' | 'hold' | 'stop' | 'warn' | 'info' | 'neutral';

export interface StatusSpec {
  tone: Tone;
  label: string;
  icon: LucideIcon;
}

export const DECISION: Record<Decision, StatusSpec> = {
  allowed: { tone: 'ok', label: 'Allowed', icon: CircleCheck },
  blocked: { tone: 'stop', label: 'Blocked', icon: Ban },
  needs_approval: { tone: 'hold', label: 'Needs approval', icon: Hourglass },
};

export const AUDIT_DECISION: Record<AuditEntry['decision'], StatusSpec> = {
  ...DECISION,
  approved: { tone: 'ok', label: 'Approved', icon: PenLine },
  rejected: { tone: 'neutral', label: 'Rejected', icon: CircleSlash },
  executed: { tone: 'ok', label: 'Executed', icon: ShieldCheck },
};

// One name per state across pages: "Blocked" and "Needs approval", as in DECISION.
export const CHECK: Record<CheckOutcome, StatusSpec> = {
  passed: { tone: 'ok', label: 'Cleared', icon: CircleCheck },
  failed: { tone: 'stop', label: 'Blocked', icon: Ban },
  held: { tone: 'hold', label: 'Needs approval', icon: Hourglass },
  rejected: { tone: 'neutral', label: 'Rejected', icon: CircleSlash },
  not_reached: { tone: 'neutral', label: 'Not reached', icon: CircleDashed },
  off: { tone: 'neutral', label: 'Off', icon: CircleSlash },
};

export const APPROVAL: Record<ApprovalStatus, StatusSpec> = {
  pending: { tone: 'hold', label: 'Waiting for approval', icon: Hourglass },
  approved: { tone: 'ok', label: 'Approved', icon: PenLine },
  rejected: { tone: 'neutral', label: 'Rejected', icon: CircleSlash },
  expired: { tone: 'warn', label: 'Expired', icon: Clock },
};

export const OUTCOME: Record<AttackOutcome, StatusSpec> = {
  blocked: { tone: 'ok', label: 'Blocked', icon: ShieldCheck },
  succeeded: { tone: 'stop', label: 'Succeeded', icon: ShieldAlert },
};

export const RUN: Record<RunStatus, StatusSpec> = {
  queued: { tone: 'neutral', label: 'Queued', icon: Clock },
  running: { tone: 'info', label: 'Running', icon: Loader },
  done: { tone: 'neutral', label: 'Done', icon: CircleCheck },
  error: { tone: 'warn', label: 'Error', icon: TriangleAlert },
};

export const INFO: StatusSpec = { tone: 'info', label: 'Info', icon: Info };

/**
 * Record status (editions, events). Green stays reserved for Allowed / Executed, so
 * Active is neutral; Draft is info (where new work is prepared).
 */
export const RECORD: Record<RecordStatus, StatusSpec> = {
  active: { tone: 'neutral', label: 'Active', icon: CircleDot },
  draft: { tone: 'info', label: 'Draft', icon: PenLine },
  archived: { tone: 'neutral', label: 'Archived', icon: Archive },
};

/** Toast specs for record actions. Errors use RUN.error. */
export const RECORD_ACTION = {
  archived: { tone: 'neutral', label: 'Archived', icon: Archive } satisfies StatusSpec,
  restored: { tone: 'ok', label: 'Restored', icon: ArchiveRestore } satisfies StatusSpec,
};

/**
 * Tone of the step / sequence numeral in the margin, shared by the cue sheet and the
 * audit chain: blocked → stop, needs approval → hold, executed/approved → ok,
 * everything else muted. Chain integrity is shown by the link glyph, never the numeral.
 */
export type NumeralState = 'allowed' | 'needs_approval' | 'blocked' | 'executed' | 'rejected' | 'expired' | 'leaked';

export const NUMERAL_TONE: Record<NumeralState, string> = {
  allowed: 'text-muted',
  needs_approval: 'text-hold',
  blocked: 'text-stop',
  leaked: 'text-stop',
  executed: 'text-ok',
  rejected: 'text-muted',
  expired: 'text-warn',
};

export function auditNumeralState(decision: AuditEntry['decision']): NumeralState {
  if (decision === 'approved' || decision === 'executed') return 'executed';
  return decision;
}

export const TONE_CLASS: Record<Tone, { text: string; bg: string; line: string }> = {
  ok: { text: 'text-ok', bg: 'bg-ok-bg', line: 'border-ok-line' },
  hold: { text: 'text-hold', bg: 'bg-hold-bg', line: 'border-hold-line' },
  stop: { text: 'text-stop', bg: 'bg-stop-bg', line: 'border-stop-line' },
  warn: { text: 'text-warn', bg: 'bg-warn-bg', line: 'border-warn-line' },
  info: { text: 'text-info', bg: 'bg-info-bg', line: 'border-info-line' },
  neutral: { text: 'text-muted', bg: 'bg-surface-2', line: 'border-line' },
};
