import { Link2, Link2Off, Search, ShieldCheck, ShieldX, ScrollText } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router';
import { api, CONFIG_IDS, ROLES, type AuditEntry, type ChainCheck } from '../api';
import { PageHeader, SampleDataNote } from '../components/shell/AppShell';
import { Button } from '../components/ui/Button';
import { Hash, JsonBlock } from '../components/ui/Code';
import { Dialog } from '../components/ui/Dialog';
import { EmptyState, ErrorState, Skeleton } from '../components/ui/Feedback';
import { SelectField, TextField } from '../components/ui/Field';
import { DataField } from '../components/ui/Panel';
import { DetailPane, LIST_DETAIL_GRID } from '../components/ui/DetailPane';
import { AUDIT_DECISION, NUMERAL_TONE, auditNumeralState } from '../components/ui/status';
import { StatusChip } from '../components/ui/StatusChip';
import { cn } from '../lib/cn';
import { fmtArgs, fmtDayTime, fmtTime } from '../lib/format';
import { useAsync } from '../lib/useAsync';
import { useApp } from '../state/AppState';

type VerifyState = { kind: 'idle' } | { kind: 'running'; tamper: boolean } | { kind: 'done'; tamper: boolean; result: ChainCheck };

const DECISIONS = Object.keys(AUDIT_DECISION) as AuditEntry['decision'][];

export default function AuditPage() {
  const { ctx } = useApp();
  const [params, setParams] = useSearchParams();
  const q = params.get('q') ?? '';
  const decision = (params.get('decision') ?? '') as AuditEntry['decision'] | '';
  const role = params.get('role') ?? '';
  const config = params.get('config') ?? '';
  const [selected, setSelected] = useState<number | null>(null);
  const [verify, setVerify] = useState<VerifyState>({ kind: 'idle' });
  const [confirmTamper, setConfirmTamper] = useState(false);

  const list = useAsync(
    (signal) =>
      api.audit.list(
        { ...ctx, signal },
        {
          ...(q ? { q } : {}),
          ...(decision ? { decision } : {}),
          ...(role ? { role: role as AuditEntry['actorRole'] } : {}),
          ...(config ? { config: config as AuditEntry['config'] } : {}),
        },
      ),
    [q, decision, role, config],
  );
  const all = useAsync((signal) => api.audit.list({ ...ctx, signal }), []);

  const setParam = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
  };

  const entries = useMemo(() => list.data ?? [], [list.data]);
  const brokenAt = verify.kind === 'done' && verify.result.status === 'broken' ? verify.result.brokenAt : null;
  // A search for one tool call selects its newest entry.
  const current = entries.find((e) => e.seq === selected) ?? (q ? entries[0] : undefined) ?? (brokenAt ? entries.find((e) => e.seq === brokenAt) : undefined);

  useEffect(() => {
    if (brokenAt === null) return;
    document.getElementById(`audit-${brokenAt}`)?.scrollIntoView({ block: 'center', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
  }, [brokenAt]);

  const runVerify = async (tamper: boolean) => {
    setConfirmTamper(false);
    setVerify({ kind: 'running', tamper });
    const result = await api.audit.verify(ctx, { simulateTamper: tamper });
    setVerify({ kind: 'done', tamper, result });
    if (result.status === 'broken') setSelected(result.brokenAt);
  };

  const prevOf = (e: AuditEntry) => all.data?.find((x) => x.seq === e.seq - 1);
  const filtered = Boolean(q || decision || role || config);

  return (
    <div className="pb-10">
      <PageHeader
        title="Audit log"
        actions={
          <>
            <SampleDataNote what="The log" />
            <Button variant="secondary" onClick={() => setConfirmTamper(true)} disabled={verify.kind === 'running'} icon={<Link2Off aria-hidden className="size-4" />}>
              Simulate tampering
            </Button>
            <Button variant="primary" onClick={() => void runVerify(false)} loading={verify.kind === 'running' && !verify.tamper} icon={<ShieldCheck aria-hidden className="size-4" />}>
              Verify chain
            </Button>
          </>
        }
      >
        Every gateway decision is written here, and each entry carries the hash of the one before it. Editing any past entry changes its hash and breaks every link after it. Entries are recorded only in configurations with the audit log on (C3 and C4).
      </PageHeader>

      <div className="px-6">
        <ChainBanner state={verify} />
      </div>

      <form role="search" className="flex flex-wrap items-end gap-3 px-6 pt-5 pb-4" onSubmit={(e) => e.preventDefault()}>
        <TextField
          label="Search"
          placeholder="Tool, call id, rule, recipient…"
          value={q}
          onChange={(e) => setParam('q', e.target.value)}
          wrapperClassName="w-72"
          type="search"
        />
        <SelectField label="Decision" value={decision} onChange={(e) => setParam('decision', e.target.value)} wrapperClassName="w-44">
          <option value="">All decisions</option>
          {DECISIONS.map((d) => (
            <option key={d} value={d}>
              {AUDIT_DECISION[d].label}
            </option>
          ))}
        </SelectField>
        <SelectField label="Role" value={role} onChange={(e) => setParam('role', e.target.value)} wrapperClassName="w-36">
          <option value="">All roles</option>
          {ROLES.map((r) => (
            <option key={r}>{r}</option>
          ))}
        </SelectField>
        <SelectField label="Configuration" value={config} onChange={(e) => setParam('config', e.target.value)} wrapperClassName="w-36">
          <option value="">All</option>
          {CONFIG_IDS.map((c) => (
            <option key={c}>{c}</option>
          ))}
        </SelectField>
        {filtered ? (
          <Button variant="ghost" onClick={() => setParams({}, { replace: true })}>
            Clear filters
          </Button>
        ) : null}
        <p className="m-0 ml-auto pb-2 text-sm text-muted" aria-live="polite">
          {list.data ? `${entries.length} of ${all.data?.length ?? '…'} entries · newest first` : 'Loading…'}
        </p>
      </form>

      <div className={`${LIST_DETAIL_GRID} px-6`}>
        <section aria-label="Entries" className="min-w-0 rounded-sm border border-line">
          {list.status === 'error' && !list.data ? (
            <ErrorState error={list.error} onRetry={list.reload} />
          ) : !list.data ? (
            <div className="p-4">
              <Skeleton lines={8} />
            </div>
          ) : entries.length === 0 ? (
            <EmptyState
              icon={filtered ? Search : ScrollText}
              title={filtered ? 'No entry matches these filters' : 'The log is empty'}
              action={
                filtered ? (
                  <Button size="sm" onClick={() => setParams({}, { replace: true })}>
                    Clear filters
                  </Button>
                ) : undefined
              }
            >
              {filtered ? 'Try a call id such as TC-0008, or clear the filters.' : 'Run the assistant on C3 or C4 to record gateway decisions.'}
            </EmptyState>
          ) : (
            <ol className="eg-script relative m-0 list-none p-0">
              {entries.map((e) => (
                <AuditRow
                  key={e.seq}
                  entry={e}
                  selected={current?.seq === e.seq}
                  onSelect={() => setSelected(e.seq)}
                  broken={brokenAt === e.seq}
                  afterBreak={brokenAt !== null && e.seq > brokenAt}
                  verified={verify.kind === 'done' && (verify.result.status === 'intact' || (brokenAt !== null && e.seq < brokenAt))}
                />
              ))}
            </ol>
          )}
        </section>

        {current ? (
          <DetailPane
            title={
              <>
                Entry <span className="font-mono">#{current.seq}</span>
              </>
            }
            meta={<span className="font-mono">{current.toolCallId}</span>}
            status={<StatusChip spec={AUDIT_DECISION[current.decision]} />}
            frameClassName={brokenAt === current.seq ? 'border-stop-line' : undefined}
            lead={verify.kind === 'done' && verify.result.status === 'broken' && verify.result.brokenAt === current.seq ? <BreakDetail result={verify.result} /> : undefined}
          >
              <dl className="m-0 grid grid-cols-2 gap-x-4 gap-y-3 px-4 py-3">
                <DataField label="Time">{fmtDayTime(current.at)}</DataField>
                <DataField label="Actor role">{current.actorRole}</DataField>
                <DataField label="Tool" mono>
                  {current.tool}
                </DataField>
                <DataField label="Configuration" mono>
                  {current.config}
                </DataField>
                <DataField label="Tool call" mono>
                  {current.toolCallId}
                </DataField>
                <DataField label="Conversation" mono>
                  {current.conversationId}
                </DataField>
                {current.rule ? (
                  <DataField label="Rule" mono className="col-span-2">
                    {current.rule}
                  </DataField>
                ) : null}
                {current.reason ? (
                  <div className="col-span-2">
                    <dt className="field-label">Reason</dt>
                    <dd className="m-0 mt-0.5 text-sm">{current.reason}</dd>
                  </div>
                ) : null}
              </dl>
              <div className="px-4 pb-4">
                <JsonBlock label="Arguments" value={current.args} maxHeight="max-h-40" />
              </div>
              <div className="border-t border-line px-4 py-3">
                <p className="field-label m-0">Chain link</p>
                <dl className="m-0 mt-2 flex flex-col gap-2 text-xs">
                  <div className="grid grid-cols-[7rem_minmax(0,1fr)] gap-2">
                    <dt className="text-muted">Previous hash</dt>
                    <dd className="mono m-0 break-all">{current.prevHash}</dd>
                  </div>
                  <div className="grid grid-cols-[7rem_minmax(0,1fr)] gap-2">
                    <dt className="text-muted">This hash</dt>
                    <dd className="mono m-0 break-all">{current.hash}</dd>
                  </div>
                </dl>
                {prevOf(current) ? (
                  <button type="button" onClick={() => setSelected(current.seq - 1)} className="mt-2 text-xs font-semibold text-muted underline-offset-2 hover:text-text hover:underline">
                    Go to entry #{current.seq - 1}
                  </button>
                ) : (
                  <p className="m-0 mt-2 text-xs text-muted">First entry: linked to the genesis hash (all zeros).</p>
                )}
              </div>
          </DetailPane>
        ) : (
          <aside className="hidden rounded-sm border border-dashed border-line xl:block">
            <EmptyState icon={Link2} title="Select an entry">
              Its arguments, the rule that applied and both hashes of its chain link appear here.
            </EmptyState>
          </aside>
        )}
      </div>

      <Dialog
        open={confirmTamper}
        onClose={() => setConfirmTamper(false)}
        title="Simulate tampering?"
        description="We take a copy of the log, edit one past entry the way someone covering their tracks would (the blocked exfiltration is rewritten as an allowed, internal email), then verify that copy. The real log is not changed."
        size="sm"
        footer={
          <>
            <Button variant="ghost" onClick={() => setConfirmTamper(false)}>
              Cancel
            </Button>
            <Button variant="danger" onClick={() => void runVerify(true)} icon={<Link2Off aria-hidden className="size-4" />}>
              Verify the edited copy
            </Button>
          </>
        }
      />
    </div>
  );
}

function ChainBanner({ state }: { state: VerifyState }) {
  if (state.kind === 'idle') {
    return (
      <p className="m-0 flex items-center gap-2 rounded-sm border border-line bg-surface-1 px-4 py-2.5 text-sm text-muted">
        <Link2 aria-hidden className="size-4" />
        Not verified in this session. Verify chain recomputes every hash from the first entry.
      </p>
    );
  }
  if (state.kind === 'running') {
    return (
      <p role="status" className="m-0 flex items-center gap-2 rounded-sm border border-info-line bg-info-bg px-4 py-2.5 text-sm">
        <Link2 aria-hidden className="size-4 text-info" />
        Recomputing hashes{state.tamper ? ' on the edited copy' : ''}…
      </p>
    );
  }
  const r = state.result;
  if (r.status === 'intact') {
    return (
      <div role="status" className="eg-swap flex flex-wrap items-center gap-x-3 gap-y-1 rounded-sm border border-ok-line bg-ok-bg px-4 py-2.5 text-sm">
        <ShieldCheck aria-hidden className="size-4 text-ok" />
        <span className="font-semibold text-ok">Chain intact.</span>
        <span>All {r.checked} entries match their recorded hash and link to the one before.</span>
        <span className="text-muted">
          Head <Hash value={r.head} chars={10} />
        </span>
      </div>
    );
  }
  return (
    <div role="alert" className="eg-swap flex flex-wrap items-center gap-x-3 gap-y-1 rounded-sm border border-stop-line bg-stop-bg px-4 py-2.5 text-sm">
      <ShieldX aria-hidden className="size-4 text-stop" />
      <span className="font-semibold text-stop">Chain broken at entry #{r.brokenAt}.</span>
      <span>
        Its contents no longer match the hash recorded when it was written, so entries #{r.brokenAt} onward cannot be trusted.
        {state.tamper ? ' (Edited copy: the real log is unchanged.)' : ''}
      </span>
    </div>
  );
}

function BreakDetail({ result }: { result: Extract<ChainCheck, { status: 'broken' }> }) {
  return (
    <div className="border-b border-stop-line bg-stop-bg px-4 py-3">
      <p className="m-0 flex items-center gap-1.5 text-sm font-semibold text-stop">
        <Link2Off aria-hidden className="size-4" />
        This entry was edited after it was written
      </p>
      <dl className="m-0 mt-2 flex flex-col gap-1.5 text-xs">
        <div className="grid grid-cols-[9rem_minmax(0,1fr)] gap-2">
          <dt className="text-muted">Hash recorded</dt>
          <dd className="mono m-0 break-all">{result.storedHash}</dd>
        </div>
        <div className="grid grid-cols-[9rem_minmax(0,1fr)] gap-2">
          <dt className="text-muted">Hash of it now</dt>
          <dd className="mono m-0 break-all text-stop">{result.expectedHash}</dd>
        </div>
      </dl>
      {result.changedFields?.length ? (
        <table className="mt-3 w-full border-collapse text-xs">
          <caption className="field-label pb-1 text-left">What was changed</caption>
          <thead>
            <tr className="text-left text-muted">
              <th scope="col" className="py-1 pr-2 font-semibold">
                Field
              </th>
              <th scope="col" className="py-1 pr-2 font-semibold">
                Originally
              </th>
              <th scope="col" className="py-1 font-semibold">
                Now reads
              </th>
            </tr>
          </thead>
          <tbody>
            {result.changedFields.map((c) => (
              <tr key={c.field} className="border-t border-stop-line align-top">
                <td className="mono py-1 pr-2">{c.field}</td>
                <td className="mono py-1 pr-2 break-all">{String(c.original ?? '(empty)')}</td>
                <td className="mono py-1 break-all text-stop">{String(c.stored ?? '(removed)')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
    </div>
  );
}

function AuditRow({
  entry: e,
  selected,
  onSelect,
  broken,
  afterBreak,
  verified,
}: {
  entry: AuditEntry;
  selected: boolean;
  onSelect: () => void;
  broken: boolean;
  afterBreak: boolean;
  verified: boolean;
}) {
  const spec = AUDIT_DECISION[e.decision];
  // Same tone rules as the cue sheet; chain integrity is carried by the link glyph and the row, not the numeral.
  const numberTone = NUMERAL_TONE[auditNumeralState(e.decision)];
  return (
    <li id={`audit-${e.seq}`} className={cn('relative grid grid-cols-[4.5rem_minmax(0,1fr)] sm:grid-cols-[5.5rem_minmax(0,1fr)]', selected && 'bg-surface-2', broken && 'bg-stop-bg')}>
      <div className="pt-3 pl-4 sm:pl-6">
        <span aria-hidden className={cn('block font-mono text-[1.75rem] leading-none font-light tracking-[-0.03em]', numberTone)}>
          {e.seq}
        </span>
        <span className="mt-1.5 block text-xs text-muted tabular-nums">{fmtTime(e.at).slice(0, 5)}</span>
      </div>
      <div className="min-w-0 border-b border-line py-3 pr-4 pl-4 sm:pl-5">
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <button type="button" onClick={onSelect} aria-current={selected || undefined} className="font-mono text-[0.84rem] font-semibold before:absolute before:inset-0 before:content-[''] hover:underline">
            <span className="sr-only">Entry {e.seq}: </span>
            {e.tool}
          </button>
          <span className="text-xs text-muted">
            {e.actorRole} · <span className="font-mono">{e.config}</span> · <span className="font-mono">{e.toolCallId}</span>
          </span>
          <span className="ml-auto flex items-baseline gap-2">
            <StatusChip spec={spec} variant="plain" size="sm" />
            {e.rule ? <span className="mono text-xs text-muted">{e.rule}</span> : null}
          </span>
        </div>
        <p className="mono m-0 mt-0.5 truncate text-xs text-muted" title={fmtArgs(e.args)}>
          {fmtArgs(e.args) || '(no arguments)'}
        </p>
        <p className="m-0 mt-1 flex flex-wrap items-center gap-1.5 text-xs text-muted">
          {broken ? <Link2Off aria-hidden className="size-3.5 text-stop" /> : <Link2 aria-hidden className={cn('size-3.5', verified ? 'text-ok' : undefined)} />}
          <Hash value={e.prevHash} chars={6} />
          <span aria-hidden>→</span>
          <Hash value={e.hash} chars={6} className="text-text" />
          {broken ? <span className="font-semibold text-stop">Hash mismatch: edited after it was written</span> : null}
          {afterBreak ? <span className="font-semibold text-warn">After the break: cannot be trusted</span> : null}
          {verified && !broken && !afterBreak ? <span className="text-ok">Verified</span> : null}
        </p>
      </div>
    </li>
  );
}
