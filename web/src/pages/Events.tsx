import { Archive, ArchiveRestore, CalendarX2, Hourglass, Lock, MessagesSquare, Users } from 'lucide-react';
import { useEffect, useId, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router';
import { api, ApiError, type Approval, type EventRecord, type EventType } from '../api';
import { PageHeader, SampleDataNote } from '../components/shell/AppShell';
import { Button, buttonClass } from '../components/ui/Button';
import { DetailPane, LIST_DETAIL_GRID } from '../components/ui/DetailPane';
import { Dialog } from '../components/ui/Dialog';
import { EmptyState, ErrorState, Skeleton } from '../components/ui/Feedback';
import { SelectField } from '../components/ui/Field';
import { DataField } from '../components/ui/Panel';
import { RECORD, RECORD_ACTION, RUN } from '../components/ui/status';
import { StatusChip } from '../components/ui/StatusChip';
import { Table, Td, Th, THead, Tr, type SortDir } from '../components/ui/Table';
import { Tabs, tabPanelProps } from '../components/ui/Tabs';
import { useToast } from '../components/ui/Toast';
import { cn } from '../lib/cn';
import { fmtDate } from '../lib/format';
import { useAsync } from '../lib/useAsync';
import { useApp } from '../state/AppState';

const TYPE_LABEL: Record<EventType, string> = { conference: 'Conference', club: 'Club', evening: 'Evening' };
type StatusFilter = 'all' | 'live' | 'archived';

/** Plain-language message for a refused EventSim write. */
function explain(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 409) return 'Nothing to do: the event is already in that state (someone may have changed it a moment ago).';
    if (err.status === 403) return `Your role cannot do this. EventSim said: ${err.detail}.`;
    if (err.status === 0) return err.detail;
    return `EventSim refused (${err.status}): ${err.detail}.`;
  }
  return err instanceof Error ? err.message : String(err);
}

/** EventSim event times are local wall-clock: show the date part as written, never shifted by time zone. */
const fmtWhen = (iso: string) => fmtDate(iso.slice(0, 10));
const fmtClock = (iso: string) => iso.slice(11, 16);

export default function EventsPage() {
  const { ctx, role } = useApp();
  const toast = useToast();
  const tabsId = useId();
  const [params, setParams] = useSearchParams();
  const year = params.get('year') ? Number(params.get('year')) : null;
  const type = (params.get('kind') ?? '') as EventType | '';
  const status = (params.get('status') ?? 'all') as StatusFilter;
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [sort, setSort] = useState<{ key: 'date' | 'name'; dir: SortDir }>({ key: 'date', dir: 'asc' });
  const [confirm, setConfirm] = useState<{ event: EventRecord; archive: boolean } | null>(null);
  const [busy, setBusy] = useState(false);

  const setParam = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
  };

  const editions = useAsync((signal) => api.events.listEditions({ ...ctx, signal }), [ctx.role]);
  const editionList = editions.data ?? [];
  const edition = editionList.find((e) => e.year === year) ?? editionList.find((e) => e.year === 2026) ?? editionList[0];

  const events = useAsync((signal) => (edition ? api.events.listEvents({ ...ctx, signal }, { edition_id: edition.id }) : Promise.resolve([])), [edition?.id, ctx.role]);
  const sessions = useAsync((signal) => api.sessions.list({ ...ctx, signal }), [ctx.role, events.data?.length ?? 0]);

  const all = useMemo(() => events.data ?? [], [events.data]);
  const rows = useMemo(() => {
    const list = all.filter((e) => !type || e.type === type).filter((e) => status === 'all' || (status === 'archived' ? e.archived : !e.archived));
    return [...list].sort((a, b) => {
      const d = sort.key === 'date' ? a.start_at.localeCompare(b.start_at) : a.name.localeCompare(b.name);
      return sort.dir === 'asc' ? d : -d;
    });
  }, [all, type, status, sort]);

  const sessionCount = (id: number) => (sessions.data ?? []).filter((s) => s.event_id === id).length;
  const selected = rows.find((e) => e.id === selectedId) ?? rows[0];
  const archivedCount = all.filter((e) => e.archived).length;
  const filtered = Boolean(type || status !== 'all');

  const doArchive = async () => {
    if (!confirm) return;
    setBusy(true);
    try {
      if (confirm.archive) await api.events.archive(ctx, 'events', confirm.event.id);
      else await api.events.unarchive(ctx, 'events', confirm.event.id);
      toast.show(
        confirm.archive ? RECORD_ACTION.archived : RECORD_ACTION.restored,
        confirm.event.name,
        confirm.archive ? 'Hidden from active lists. Unarchive restores its previous status.' : 'Back to its previous status.',
      );
      events.reload();
    } catch (err) {
      toast.show(RUN.error, `${confirm.event.name} was not changed`, explain(err));
      events.reload();
    } finally {
      setBusy(false);
      setConfirm(null);
    }
  };

  const toggleSort = (key: 'date' | 'name') => setSort((s) => ({ key, dir: s.key === key && s.dir === 'asc' ? 'desc' : 'asc' }));

  return (
    <div className="pb-10">
      <PageHeader title="Events" actions={api.source.events === 'mock' ? <SampleDataNote what="EventSim seed 42 (copy)" /> : null}>
        The EventSim records the assistant works on. Nothing is ever deleted: archiving hides a record and unarchiving restores it.
      </PageHeader>

      {editions.status === 'error' && !editions.data ? (
        <ErrorState title="EventSim could not be reached" error={explain(editions.error)} onRetry={editions.reload} className="mx-6 rounded-sm border border-line" />
      ) : (
        <>
          <div className="px-6">
            {editions.data && edition ? (
              <Tabs
                idBase={tabsId}
                label="Editions"
                value={String(edition.year)}
                onChange={(y) => {
                  setParam('year', y);
                  setSelectedId(null);
                }}
                items={editionList.map((e) => ({
                  id: String(e.year),
                  label: (
                    <span className="flex items-center gap-2">
                      {e.year}
                      <StatusChip spec={RECORD[e.status]} variant="plain" size="sm" className="font-medium" />
                    </span>
                  ),
                }))}
              />
            ) : (
              <Skeleton className="h-9 w-80" />
            )}
          </div>

          <div {...(edition ? tabPanelProps(tabsId, String(edition.year)) : {})} className="px-6 pt-4">
            {edition ? (
              <p className="m-0 mb-4 text-sm text-muted">
                <span className="font-semibold text-text">{edition.name}</span> · {fmtDate(edition.start_date)} to {fmtDate(edition.end_date)} · {all.length} events
                {archivedCount ? `, ${archivedCount} archived` : ''}
                {edition.status === 'draft' ? ' · Draft editions are where editors may create events.' : ''}
              </p>
            ) : null}

            <form role="search" className="mb-4 flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
              <SelectField label="Kind" value={type} onChange={(e) => setParam('kind', e.target.value)} wrapperClassName="w-44">
                <option value="">All kinds</option>
                <option value="conference">Conferences</option>
                <option value="club">Clubs</option>
                <option value="evening">Evenings</option>
              </SelectField>
              <SelectField label="Status" value={status} onChange={(e) => setParam('status', e.target.value === 'all' ? '' : e.target.value)} wrapperClassName="w-44">
                <option value="all">All statuses</option>
                <option value="live">Not archived</option>
                <option value="archived">Archived only</option>
              </SelectField>
              {filtered ? (
                <Button
                  variant="ghost"
                  onClick={() => {
                    const next = new URLSearchParams(params);
                    next.delete('kind');
                    next.delete('status');
                    setParams(next, { replace: true });
                  }}
                >
                  Clear filters
                </Button>
              ) : null}
              <p className="m-0 ml-auto pb-2 text-sm text-muted" aria-live="polite">
                {events.data ? `${rows.length} of ${all.length} events` : ''}
              </p>
            </form>

            <div className={LIST_DETAIL_GRID}>
              <div className="min-w-0 overflow-x-auto rounded-sm border border-line">
                {events.status === 'error' && !events.data ? (
                  <ErrorState title="Events could not load" error={explain(events.error)} onRetry={events.reload} />
                ) : !events.data ? (
                  <div className="p-4">
                    <Skeleton lines={8} />
                  </div>
                ) : rows.length === 0 ? (
                  all.length === 0 ? (
                    <EmptyState
                      icon={CalendarX2}
                      title={`No events in ${edition?.year ?? 'this edition'} yet`}
                      action={
                        edition ? (
                          <Link
                            to={`/assistant?new=1&prompt=${encodeURIComponent(`Duplicate the ${edition.year - 1} edition into ${edition.year}, skip archived events.`)}`}
                            className={buttonClass('secondary', 'sm')}
                          >
                            <MessagesSquare aria-hidden className="size-3.5" />
                            Ask the assistant to duplicate {edition.year - 1}
                          </Link>
                        ) : undefined
                      }
                    >
                      Copies of the previous edition arrive here as drafts once their preview is approved.
                    </EmptyState>
                  ) : (
                    <EmptyState icon={CalendarX2} title="No event matches these filters">
                      Change the kind or status filter, or clear the filters.
                    </EmptyState>
                  )
                ) : (
                  <Table caption={`Events of ${edition?.name ?? ''}`}>
                    <THead>
                      <tr>
                        <Th className="w-full" sort={{ active: sort.key === 'name', dir: sort.dir, onSort: () => toggleSort('name') }}>
                          Event
                        </Th>
                        <Th sort={{ active: sort.key === 'date', dir: sort.dir, onSort: () => toggleSort('date') }}>Date</Th>
                        <Th numeric>Sessions</Th>
                        <Th>Status</Th>
                      </tr>
                    </THead>
                    <tbody>
                      {rows.map((e) => {
                        const isSel = selected?.id === e.id;
                        return (
                          <Tr key={e.id} selected={isSel} className="relative">
                            <Td className="py-2">
                              <button type="button" aria-current={isSel || undefined} onClick={() => setSelectedId(e.id)} className="block text-left before:absolute before:inset-0 before:content-['']">
                                <span className={cn('block text-sm font-semibold', e.archived ? 'text-muted' : 'text-text')}>{e.name}</span>
                                <span className="block text-xs text-muted">
                                  {TYPE_LABEL[e.type]} · {e.venue}
                                </span>
                              </button>
                            </Td>
                            <Td className="text-sm whitespace-nowrap tabular-nums">{fmtWhen(e.start_at)}</Td>
                            <Td numeric>{sessions.data ? sessionCount(e.id) : '…'}</Td>
                            <Td className="whitespace-nowrap">
                              <StatusChip spec={RECORD[e.status]} variant="plain" size="sm" />
                            </Td>
                          </Tr>
                        );
                      })}
                    </tbody>
                  </Table>
                )}
              </div>

              {selected ? <EventDetail key={selected.id} event={selected} onArchive={(archive) => setConfirm({ event: selected, archive })} role={role} /> : null}
            </div>
          </div>
        </>
      )}

      <Dialog
        open={confirm !== null}
        onClose={() => setConfirm(null)}
        size="sm"
        title={confirm ? `${confirm.archive ? 'Archive' : 'Unarchive'} ${confirm.event.name}?` : 'Archive event?'}
        description={
          confirm?.archive
            ? 'The event leaves active lists and the assistant skips it when duplicating. Its sessions are not archived (archive does not cascade). You can unarchive it at any time. This is a direct EventSim edit: it does not go through the gateway and is not in the audit log.'
            : 'The event returns to the status it had before it was archived. This is a direct EventSim edit: it does not go through the gateway and is not in the audit log.'
        }
        footer={
          <>
            <Button variant="ghost" onClick={() => setConfirm(null)}>
              Cancel
            </Button>
            <Button variant="primary" loading={busy} onClick={() => void doArchive()} icon={confirm?.archive ? <Archive aria-hidden className="size-4" /> : <ArchiveRestore aria-hidden className="size-4" />}>
              {confirm?.archive ? 'Archive event' : 'Unarchive event'}
            </Button>
          </>
        }
      />
    </div>
  );
}

function EventDetail({ event: e, onArchive, role }: { event: EventRecord; onArchive: (archive: boolean) => void; role: string }) {
  const { ctx } = useApp();
  const canArchive = role !== 'reader';
  const sessions = useAsync((signal) => api.sessions.list({ ...ctx, signal }, { event_id: e.id }), [e.id, e.updated_at]);
  const partners = useAsync((signal) => api.partners.list({ ...ctx, signal }, { event_id: e.id }), [e.id]);
  const isAdmin = ctx.role === 'admin';
  const attendees = useAsync((signal) => (isAdmin ? api.attendees.list({ ...ctx, signal }, { event_id: e.id }) : Promise.resolve(null)), [e.id, isAdmin]);
  const pending = useAsync((signal) => api.approvals.list({ ...ctx, signal }, { status: 'pending' }), [e.id, e.updated_at]);
  const [speakers, setSpeakers] = useState<Record<number, string>>({});
  const year = e.start_at.slice(0, 4);

  // Pending approvals that touch this event (matched on the preview's lines).
  const related: Approval[] = (pending.data ?? []).filter((a) =>
    a.preview.groups.some((g) => g.entity === 'event' && g.lines.some((l) => l.label === e.name && `${a.preview.title} ${l.detail ?? ''}`.includes(year))),
  );

  useEffect(() => {
    let alive = true;
    void Promise.all((sessions.data ?? []).map(async (s) => [s.id, (await api.speakers.forSession(ctx, s.id)).map((p) => `${p.first_name} ${p.last_name}`).join(', ')] as const)).then((pairs) => {
      if (alive) setSpeakers(Object.fromEntries(pairs));
    });
    return () => {
      alive = false;
    };
  }, [sessions.data, ctx]);

  return (
    <DetailPane
      title={e.name}
      meta={
        <>
          {TYPE_LABEL[e.type]} · <span className="font-mono">#{e.id}</span>
        </>
      }
      status={<StatusChip spec={RECORD[e.status]} />}
      footer={
        <>
          {related.length ? (
            <div className="flex w-full flex-col gap-1 rounded-sm border border-hold-line bg-hold-bg px-3 py-2 text-sm">
              {related.map((a) => (
                <p key={a.id} className="m-0 flex flex-wrap items-center gap-2">
                  <Hourglass aria-hidden className="size-3.5 text-hold" />
                  <span>
                    <span className="font-semibold">Needs approval:</span> {a.summary}
                  </span>
                  <Link to="/approvals" className="font-mono text-xs text-text underline decoration-line-strong hover:decoration-text">
                    Review {a.id}
                  </Link>
                </p>
              ))}
            </div>
          ) : null}
          {e.archived ? (
            <Button onClick={() => onArchive(false)} disabled={!canArchive} icon={<ArchiveRestore aria-hidden className="size-4" />}>
              Unarchive
            </Button>
          ) : (
            <Button onClick={() => onArchive(true)} disabled={!canArchive} icon={<Archive aria-hidden className="size-4" />}>
              Archive event
            </Button>
          )}
          <p className="m-0 flex items-center gap-1.5 text-xs text-muted">
            {canArchive ? (
              'Reversible. Direct EventSim edit: not through the gateway, not in the audit log.'
            ) : (
              <>
                <Lock aria-hidden className="size-3.5" />
                Readers cannot archive. Switch to editor or admin.
              </>
            )}
          </p>
        </>
      }
    >
      <dl className="m-0 grid grid-cols-2 gap-x-4 gap-y-3 px-4 py-3">
        <DataField label="Starts">
          {fmtWhen(e.start_at)} · {fmtClock(e.start_at)}
        </DataField>
        <DataField label="Ends">
          {fmtWhen(e.end_at)} · {fmtClock(e.end_at)}
        </DataField>
        <DataField label="Venue" className="col-span-2">
          {e.venue}
        </DataField>
        <div className="col-span-2">
          <dt className="field-label">Description</dt>
          <dd className="m-0 mt-0.5 max-w-[65ch] text-sm break-words">{e.description || <span className="text-muted">No description</span>}</dd>
        </div>
        <div className="col-span-2">
          <dt className="field-label">Internal notes</dt>
          <dd className="m-0 mt-0.5 text-sm">
            {e.internal_notes === undefined ? (
              <span className="inline-flex items-center gap-1.5 text-muted">
                <Lock aria-hidden className="size-3.5" />
                Hidden for {role}. Editors and admins can read them.
              </span>
            ) : e.internal_notes ? (
              e.internal_notes
            ) : (
              <span className="text-muted">None</span>
            )}
          </dd>
        </div>
      </dl>

      <section aria-labelledby={`ev-sessions-${e.id}`} className="border-t border-line px-4 py-3">
        <h3 id={`ev-sessions-${e.id}`} className="field-label m-0">
          Sessions {sessions.data ? `(${sessions.data.length})` : ''}
        </h3>
        {sessions.status === 'error' ? (
          <ErrorState error={explain(sessions.error)} className="px-0 py-2" />
        ) : !sessions.data ? (
          <Skeleton lines={3} className="mt-2" />
        ) : sessions.data.length === 0 ? (
          <p className="m-0 mt-1 text-sm text-muted">No sessions.</p>
        ) : (
          <ul className="m-0 mt-2 flex list-none flex-col gap-2 p-0">
            {sessions.data.map((s) => (
              <li key={s.id} className="text-sm">
                <span className={cn('font-semibold', s.archived && 'text-muted')}>{s.title}</span>
                {s.archived ? <StatusChip spec={RECORD.archived} variant="plain" size="sm" className="ml-2" /> : null}
                <span className="block text-xs text-muted tabular-nums">
                  {fmtClock(s.start_at)}
                  {s.room ? ` · ${s.room}` : ''}
                  {speakers[s.id] ? ` · ${speakers[s.id]}` : ''}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-labelledby={`ev-partners-${e.id}`} className="border-t border-line px-4 py-3">
        <h3 id={`ev-partners-${e.id}`} className="field-label m-0">
          Partners {partners.data ? `(${partners.data.length})` : ''}
        </h3>
        {partners.status === 'error' ? (
          <ErrorState error={explain(partners.error)} className="px-0 py-2" />
        ) : !partners.data ? (
          <Skeleton lines={2} className="mt-2" />
        ) : partners.data.length === 0 ? (
          <p className="m-0 mt-1 text-sm text-muted">No partners linked.</p>
        ) : (
          <ul className="m-0 mt-2 flex list-none flex-wrap gap-2 p-0">
            {partners.data.map((p) => (
              <li key={p.id} className="rounded-xs border border-line px-2 py-1 text-sm">
                {p.name} <span className="text-xs text-muted">· {p.tier}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-labelledby={`ev-attendees-${e.id}`} className="border-t border-line px-4 py-3">
        <h3 id={`ev-attendees-${e.id}`} className="field-label m-0">
          Registrations
        </h3>
        {!isAdmin ? (
          <p className="m-0 mt-1 flex items-center gap-1.5 text-sm text-muted">
            <Lock aria-hidden className="size-3.5" />
            Attendee data is visible to admins only. You are acting as {role}.
          </p>
        ) : attendees.status === 'error' ? (
          <ErrorState error={explain(attendees.error)} className="px-0 py-2" />
        ) : !attendees.data ? (
          <Skeleton lines={3} className="mt-2" />
        ) : attendees.data.length === 0 ? (
          <p className="m-0 mt-1 text-sm text-muted">No registrations.</p>
        ) : (
          <>
            <p className="m-0 mt-1 flex items-center gap-1.5 text-sm">
              <Users aria-hidden className="size-3.5 text-muted" />
              {attendees.data.length} registrations · fictional people, example.org addresses
            </p>
            <ul className="m-0 mt-2 flex max-h-40 list-none flex-col gap-1 overflow-auto p-0 text-xs">
              {attendees.data.map((a) => (
                <li key={a.id} className="flex justify-between gap-3">
                  <span>
                    {a.first_name} {a.last_name} <span className="text-muted">· {a.company}</span>
                  </span>
                  <span className="mono text-muted">{a.email}</span>
                </li>
              ))}
            </ul>
          </>
        )}
      </section>
    </DetailPane>
  );
}
