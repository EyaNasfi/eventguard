/**
 * Live EventSim client: only the routes that exist in eventsim/api.py today.
 * Requests go through the Vite dev proxy at /eventsim, which attaches the bearer
 * token for the role named in X-Demo-Role (see vite.config.ts).
 */
import {
  ApiError,
  type ArchivableEntity,
  type AttendeesApi,
  type CallContext,
  type Edition,
  type EventFilter,
  type EventRecord,
  type EventsApi,
  type Me,
  type OutboxMessage,
  type Partner,
  type PartnersApi,
  type RecordBase,
  type Session,
  type SessionsApi,
  type Speaker,
  type SpeakersApi,
  type StatusRecord,
  type Attendee,
} from './types';

const BASE = '/eventsim';
const UNREACHABLE = 'EventSim is not reachable. Check that it runs on 127.0.0.1:8000 (or at VITE_EVENTSIM_URL) and reload. See web/README.md, live mode.';

type Query = Record<string, string | number | boolean | undefined>;

function qs(query?: Query): string {
  if (!query) return '';
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(query)) if (v !== undefined) params.set(k, String(v));
  const s = params.toString();
  return s ? `?${s}` : '';
}

async function request<T>(ctx: CallContext, method: 'GET' | 'POST', path: string, query?: Query): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE}${path}${qs(query)}`, {
      method,
      headers: { Accept: 'application/json', 'X-Demo-Role': ctx.role },
      signal: ctx.signal ?? null,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') throw err;
    throw new ApiError(0, UNREACHABLE);
  }
  // The dev proxy answers 502/503/504 itself when nothing listens on VITE_EVENTSIM_URL.
  if ([502, 503, 504].includes(response.status) && !response.headers.get('content-type')?.includes('application/json')) {
    throw new ApiError(0, UNREACHABLE);
  }
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === 'string') detail = body.detail;
    } catch {
      /* body was not JSON */
    }
    throw new ApiError(response.status, detail);
  }
  return (await response.json()) as T;
}

type SessionWithSpeakers = Session & { speaker_ids: number[] };

export const liveEvents: EventsApi = {
  me: (ctx) => request<Me>(ctx, 'GET', '/me'),
  listEditions: (ctx, opts) => request<Edition[]>(ctx, 'GET', '/editions', { archived: opts?.archived }),
  listEvents: (ctx, filter?: EventFilter) => request<EventRecord[]>(ctx, 'GET', '/events', { ...filter }),
  getEvent: (ctx, id) => request<EventRecord>(ctx, 'GET', `/events/${id}`),
  archive: (ctx, entity: ArchivableEntity, id) =>
    request<StatusRecord | RecordBase>(ctx, 'POST', `/${entity}/${id}/archive`),
  unarchive: (ctx, entity: ArchivableEntity, id) =>
    request<StatusRecord | RecordBase>(ctx, 'POST', `/${entity}/${id}/unarchive`),
  outbox: (ctx) => request<OutboxMessage[]>(ctx, 'GET', '/outbox'),
};

export const liveSessions: SessionsApi = {
  list: (ctx, opts) => request<Session[]>(ctx, 'GET', '/sessions', { ...opts }),
};

export const liveSpeakers: SpeakersApi = {
  list: (ctx, opts) => request<Speaker[]>(ctx, 'GET', '/speakers', { ...opts }),
  async forSession(ctx, sessionId) {
    const session = await request<SessionWithSpeakers>(ctx, 'GET', `/sessions/${sessionId}`);
    if (session.speaker_ids.length === 0) return [];
    const all = await request<Speaker[]>(ctx, 'GET', '/speakers');
    const wanted = new Set(session.speaker_ids);
    return all.filter((s) => wanted.has(s.id));
  },
};

export const livePartners: PartnersApi = {
  list: (ctx, opts) => request<Partner[]>(ctx, 'GET', '/partners', { ...opts }),
};

export const liveAttendees: AttendeesApi = {
  list: (ctx, opts) => request<Attendee[]>(ctx, 'GET', '/attendees', { event_id: opts.event_id }),
};
