import { presetLayers } from '../gateway-model';
import {
  ApiError,
  CONFIG_IDS,
  type ApprovalsApi,
  type AttacksApi,
  type AttendeesApi,
  type AuditApi,
  type ConversationsApi,
  type EventsApi,
  type GatewayApi,
  type PartnersApi,
  type ResultsApi,
  type SessionsApi,
  type SpeakersApi,
  type ToolCallsApi,
} from '../types';
import { ATTACKS, FAMILIES, listRuns, runAttacks } from './attacks';
import { auditEntries, auditReady, verifyChain } from './audit';
import {
  configFor,
  conversations,
  decide,
  gatewayState,
  listApprovals,
  newConversation,
  runTurn,
  subscribeApprovals,
  subscribeConversation,
} from './engine';
import { METRICS, RESULTS } from './results';
import { db, delay, ensure, setArchived, visibleEvent } from './store';

const clone = <T,>(v: T): T => structuredClone(v);

export const mockEvents: EventsApi = {
  me: (ctx) =>
    delay({ id: { reader: 1, editor: 2, admin: 3 }[ctx.role], username: ctx.role, display_name: { reader: 'Lina Reader', editor: 'Sami Editor', admin: 'Nour Admin' }[ctx.role], role: ctx.role }, ctx),
  listEditions: (ctx, opts) => delay(clone(db.editions.filter((e) => opts?.archived === undefined || e.archived === opts.archived)), ctx),
  listEvents: (ctx, f) => {
    const years = new Map(db.editions.map((e) => [e.id, e.year]));
    const rows = db.events
      .filter((e) => f?.edition_id === undefined || e.edition_id === f.edition_id)
      .filter((e) => f?.year === undefined || years.get(e.edition_id) === f.year)
      .filter((e) => f?.type === undefined || e.type === f.type)
      .filter((e) => f?.status === undefined || e.status === f.status)
      .filter((e) => f?.archived === undefined || e.archived === f.archived)
      .sort((a, b) => a.start_at.localeCompare(b.start_at) || a.id - b.id)
      .map((e) => visibleEvent(e, ctx.role));
    return delay(rows, ctx);
  },
  getEvent: (ctx, id) => {
    const e = db.events.find((x) => x.id === id);
    if (!e) return Promise.reject(new ApiError(404, `event ${id} not found`));
    return delay(visibleEvent(e, ctx.role), ctx);
  },
  archive: async (ctx, entity, id) => delay(setArchived(ctx.role, entity, id, true), ctx, 300),
  unarchive: async (ctx, entity, id) => delay(setArchived(ctx.role, entity, id, false), ctx, 300),
  outbox: async (ctx) => {
    ensure(ctx.role, 'admin', 'read the outbox');
    return delay(clone(db.outbox), ctx);
  },
};

export const mockSessions: SessionsApi = {
  list: (ctx, o) =>
    delay(
      clone(
        db.sessions
          .filter((s) => o?.event_id === undefined || s.event_id === o.event_id)
          .filter((s) => o?.speaker_id === undefined || db.session_speaker.some((l) => l.session_id === s.id && l.speaker_id === o.speaker_id))
          .filter((s) => o?.archived === undefined || s.archived === o.archived)
          .sort((a, b) => a.start_at.localeCompare(b.start_at)),
      ),
      ctx,
    ),
};

export const mockSpeakers: SpeakersApi = {
  list: (ctx, o) => {
    const q = o?.q?.toLowerCase();
    return delay(clone(db.speakers.filter((s) => !q || `${s.first_name} ${s.last_name} ${s.company}`.toLowerCase().includes(q))), ctx);
  },
  forSession: (ctx, sessionId) => {
    const ids = new Set(db.session_speaker.filter((l) => l.session_id === sessionId).map((l) => l.speaker_id));
    return delay(clone(db.speakers.filter((s) => ids.has(s.id))), ctx, 120);
  },
};

export const mockPartners: PartnersApi = {
  list: (ctx, o) => {
    const linked = o?.event_id === undefined ? null : new Set(db.event_partner.filter((l) => l.event_id === o.event_id).map((l) => l.partner_id));
    return delay(
      clone(db.partners.filter((p) => (!linked || linked.has(p.id)) && (!o?.tier || p.tier === o.tier) && (!o?.q || p.name.toLowerCase().includes(o.q.toLowerCase())))),
      ctx,
    );
  },
};

export const mockAttendees: AttendeesApi = {
  list: async (ctx, o) => {
    ensure(ctx.role, 'admin', 'read attendees');
    return delay(clone(db.attendees.filter((a) => a.event_id === o.event_id)), ctx);
  },
};

export const mockConversations: ConversationsApi = {
  list: (ctx) => delay([...conversations.values()].map(clone), ctx, 80),
  get: (ctx, id) => {
    const c = conversations.get(id);
    return c ? delay(clone(c), ctx, 80) : Promise.reject(new ApiError(404, `conversation ${id} not found`));
  },
  create: (ctx, title) => delay(clone(newConversation(ctx.role, gatewayState.config, title)), ctx, 60),
  send: async (ctx, id, text, onEvent) => {
    const off = subscribeConversation(id, onEvent);
    try {
      await runTurn(ctx, id, text);
    } finally {
      off();
    }
  },
  subscribe: (id, onEvent) => subscribeConversation(id, onEvent),
};

export const mockToolCalls: ToolCallsApi = {
  list: (ctx, id) => delay(clone(conversations.get(id)?.toolCalls ?? []), ctx, 80),
};

export const mockApprovals: ApprovalsApi = {
  list: (ctx, o) => delay(listApprovals(o?.status), ctx, 160),
  get: (ctx, id) => {
    const a = listApprovals().find((x) => x.id === id);
    return a ? delay(a, ctx, 80) : Promise.reject(new ApiError(404, `approval ${id} not found`));
  },
  approve: (ctx, id) => decide(ctx, id, true),
  reject: (ctx, id, reason) => decide(ctx, id, false, reason),
  subscribe: (l) => subscribeApprovals(l),
};

export const mockAudit: AuditApi = {
  list: async (ctx, f) => {
    await auditReady;
    const q = f?.q?.toLowerCase();
    const rows = (await auditEntries())
      .filter((e) => !f?.decision || e.decision === f.decision)
      .filter((e) => !f?.role || e.actorRole === f.role)
      .filter((e) => !f?.config || e.config === f.config)
      .filter((e) => !q || `${e.tool} ${e.toolCallId} ${e.conversationId} ${e.rule ?? ''} ${JSON.stringify(e.args)}`.toLowerCase().includes(q))
      .reverse();
    return delay(rows, ctx, 180);
  },
  verify: async (ctx, o) => {
    await auditReady;
    const result = await verifyChain(o?.simulateTamper ?? false);
    return delay(result, ctx, 650);
  },
};

export const mockGateway: GatewayApi = {
  configs: (ctx) => delay(CONFIG_IDS.map((id) => configFor(id)), ctx, 120),
  active: (ctx) => delay(configFor(gatewayState.config, gatewayState.layers), ctx, 60),
  activate: (ctx, id, layers) => {
    gatewayState.config = id;
    gatewayState.layers = layers ?? presetLayers(id);
    return delay(configFor(id, gatewayState.layers), ctx, 200);
  },
};

export const mockAttacks: AttacksApi = {
  families: (ctx) => delay([...FAMILIES], ctx, 60),
  list: (ctx) => delay([...ATTACKS], ctx, 120),
  runs: (ctx, o) => delay(listRuns(o?.config), ctx, 120),
  run: (_ctx, ids, config, onUpdate) => runAttacks(ids, config, onUpdate),
};

export const mockResults: ResultsApi = {
  latest: (ctx) => delay(clone(RESULTS), ctx, 260),
  metrics: () => METRICS,
};
