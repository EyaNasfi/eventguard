import { ClipboardCheck, Inbox } from 'lucide-react';
import { useEffect, useId, useMemo, useState } from 'react';
import { Link } from 'react-router';
import { api, type Approval } from '../api';
import { PreviewCard } from '../components/agent/PreviewCard';
import { PageHeader, SampleDataNote } from '../components/shell/AppShell';
import { EmptyState, ErrorState, Skeleton } from '../components/ui/Feedback';
import { DataField } from '../components/ui/Panel';
import { DetailPane, LIST_DETAIL_GRID } from '../components/ui/DetailPane';
import { APPROVAL, RUN } from '../components/ui/status';
import { StatusChip } from '../components/ui/StatusChip';
import { Table, Td, Th, THead, Tr } from '../components/ui/Table';
import { Tabs, tabPanelProps } from '../components/ui/Tabs';
import { useToast } from '../components/ui/Toast';
import { cn } from '../lib/cn';
import { fmtCountdown, fmtDayTime } from '../lib/format';
import { useAsync } from '../lib/useAsync';
import { useNow } from '../lib/useNow';
import { useApp } from '../state/AppState';

type View = 'pending' | 'decided' | 'all';

export default function ApprovalsPage() {
  const { ctx, role } = useApp();
  const toast = useToast();
  const [view, setView] = useState<View>('pending');
  const [selected, setSelected] = useState<string | null>(null);
  const tabsId = useId();
  const list = useAsync((signal) => api.approvals.list({ ...ctx, signal }), [ctx.role]);
  const now = useNow(1000);

  useEffect(() => api.approvals.subscribe(list.reload), [list.reload]);

  const rows = useMemo(() => {
    const all = (list.data ?? []).map((a) => (a.status === 'pending' && new Date(a.expiresAt).getTime() <= now ? { ...a, status: 'expired' as const } : a));
    const pending = all.filter((a) => a.status === 'pending').sort((a, b) => a.expiresAt.localeCompare(b.expiresAt));
    const decided = all.filter((a) => a.status !== 'pending');
    return { pending, decided, all: [...pending, ...decided] };
  }, [list.data, now]);

  const shown = rows[view];
  const current = shown.find((a) => a.id === selected) ?? shown[0];

  const decide = async (a: Approval, approve: boolean) => {
    try {
      const next = approve ? await api.approvals.approve(ctx, a.id) : await api.approvals.reject(ctx, a.id);
      toast.show(approve ? APPROVAL.approved : APPROVAL.rejected, `${next.id} ${approve ? 'signed and used' : 'rejected'}`, approve ? next.summary : 'Nothing was written.');
    } catch (err) {
      toast.show(RUN.error, `${a.id} could not be decided`, err instanceof Error ? err.message : String(err));
    }
    list.reload();
    // Keep keyboard users in the queue: focus the next item that still needs a decision.
    window.setTimeout(() => {
      document.querySelector<HTMLButtonElement>('tbody button[data-approval]')?.focus();
    }, 250);
  };

  return (
    <div className="pb-10">
      <PageHeader title="Approvals" actions={<SampleDataNote what="The queue" />}>
        Every write the assistant proposes waits here with its exact preview. A signature is bound to that preview and works once; after ten minutes it expires and nothing is written.
      </PageHeader>

      <div className="px-6">
        <Tabs
          idBase={tabsId}
          label="Approval views"
          value={view}
          onChange={(v) => {
            setView(v);
            setSelected(null);
          }}
          items={[
            { id: 'pending', label: 'Needs approval', count: rows.pending.length, countTone: 'hold' },
            { id: 'decided', label: 'Decided', count: rows.decided.length },
            { id: 'all', label: 'All' },
          ]}
        />
      </div>

      <div {...tabPanelProps(tabsId, view)} className={`${LIST_DETAIL_GRID} px-6 pt-5`}>
        <div className="min-w-0 overflow-x-auto rounded-sm border border-line">
          {list.status === 'error' && !list.data ? (
            <ErrorState error={list.error} onRetry={list.reload} />
          ) : !list.data ? (
            <div className="p-4">
              <Skeleton lines={6} />
            </div>
          ) : shown.length === 0 ? (
            <EmptyState icon={view === 'pending' ? ClipboardCheck : Inbox} title={view === 'pending' ? 'Nothing is waiting for approval' : 'No decided approvals yet'}>
              {view === 'pending' ? (
                <>
                  When the assistant proposes a write, it stops here until someone signs the preview.{' '}
                  <Link to="/assistant" className="text-text underline">
                    Ask the assistant
                  </Link>{' '}
                  to duplicate an edition to see one.
                </>
              ) : (
                'Approved, rejected and expired approvals stay here with their signature or reason.'
              )}
            </EmptyState>
          ) : (
            <Table caption="Approvals">
              <THead>
                <tr>
                  <Th className="w-full">Change</Th>
                  <Th className="w-px">Requested by</Th>
                  <Th className="w-px">Configuration</Th>
                  <Th className="w-px">{view === 'pending' ? 'Expires in' : 'Status'}</Th>
                </tr>
              </THead>
              <tbody>
                {shown.map((a) => {
                  const remaining = new Date(a.expiresAt).getTime() - now;
                  const isCurrent = current?.id === a.id;
                  return (
                    <Tr key={a.id} selected={isCurrent} className="relative cursor-pointer">
                      <Td className="py-2.5">
                        <button
                          type="button"
                          aria-current={isCurrent || undefined}
                          data-approval={a.id}
                          onClick={() => setSelected(a.id)}
                          className="block w-full min-w-0 rounded-xs text-left before:absolute before:inset-0 before:content-['']"
                        >
                          <span className="line-clamp-2 block text-sm font-semibold">{a.summary}</span>
                          <span className="block font-mono text-xs whitespace-nowrap text-muted">
                            {a.id} · {fmtDayTime(a.requestedAt)}
                          </span>
                        </button>
                      </Td>
                      <Td className="text-sm whitespace-nowrap">{a.requestedBy}</Td>
                      <Td className="font-mono text-xs">{a.config}</Td>
                      <Td className="whitespace-nowrap">
                        {a.status === 'pending' ? (
                          <span className={cn('font-mono text-sm font-medium', remaining < 60_000 ? 'text-warn' : 'text-hold')}>
                            {fmtCountdown(remaining)}
                            {remaining < 60_000 ? <span className="ml-1.5 font-sans text-xs">less than a minute</span> : null}
                          </span>
                        ) : (
                          <StatusChip spec={APPROVAL[a.status]} variant="plain" size="sm" />
                        )}
                      </Td>
                    </Tr>
                  );
                })}
              </tbody>
            </Table>
          )}
        </div>

        {current ? (
          <DetailPane bare title={current.summary} label={`Selected approval ${current.id}`}>
            <PreviewCard key={current.id} approval={current} role={role} onDecide={(ok) => decide(current, ok)} />
            <dl className="m-0 grid grid-cols-2 gap-x-4 gap-y-3 rounded-sm border border-line px-4 py-3 sm:grid-cols-3">
              <DataField label="Requested by">{current.requestedBy}</DataField>
              <DataField label="Requested at">{fmtDayTime(current.requestedAt)}</DataField>
              <DataField label="Configuration" mono>
                {current.config}
              </DataField>
              <DataField label="Conversation" mono>
                {current.conversationId}
              </DataField>
              <DataField label="Audit trail" className="col-span-2">
                {current.toolCallIds.map((id, i) => (
                  <span key={id}>
                    {i > 0 ? ', ' : ''}
                    <Link to={`/audit?q=${encodeURIComponent(id)}`} className="mono text-text underline decoration-line-strong hover:decoration-text">
                      {id}
                    </Link>
                  </span>
                ))}
              </DataField>
            </dl>
          </DetailPane>
        ) : null}
      </div>
    </div>
  );
}
