/**
 * EventGuard front-end contract.
 *
 * EventSim types mirror eventsim/models.py exactly (they exist today).
 * Everything under "Gateway side" is a contract defined by the front end because
 * agent/, gateway/, attacks/ and eval/ do not exist yet. Those shapes are what the
 * backend should return; see the README in web/ for the endpoint list.
 */

/* ───────────────────────── Shared ───────────────────────── */

export type Role = 'reader' | 'editor' | 'admin';
export const ROLES: readonly Role[] = ['reader', 'editor', 'admin'];

export type ConfigId = 'C0' | 'C1' | 'C2' | 'C3' | 'C4';
export const CONFIG_IDS: readonly ConfigId[] = ['C0', 'C1', 'C2', 'C3', 'C4'];

/** ISO 8601 string. Naive local time for EventSim event fields, UTC elsewhere. */
export type IsoDateTime = string;
/** YYYY-MM-DD */
export type IsoDate = string;

/* ───────────────────────── EventSim (exists) ───────────────────────── */

export type RecordStatus = 'draft' | 'active' | 'archived';
export type EventType = 'conference' | 'club' | 'evening';
export type PartnerTier = 'gold' | 'silver' | 'bronze';

export interface RecordBase {
  id: number;
  archived: boolean;
  archived_at: IsoDateTime | null;
  created_at: IsoDateTime;
  updated_at: IsoDateTime;
  created_by: number | null;
}

export interface StatusRecord extends RecordBase {
  status: RecordStatus;
  previous_status: RecordStatus | null;
}

export interface Edition extends StatusRecord {
  year: number;
  name: string;
  start_date: IsoDate;
  end_date: IsoDate;
}

export interface EventRecord extends StatusRecord {
  edition_id: number;
  type: EventType;
  name: string;
  start_at: IsoDateTime;
  end_at: IsoDateTime;
  venue: string;
  description: string;
  /** Absent for reader (EventSim hides it). */
  internal_notes?: string;
}

export interface Session extends RecordBase {
  event_id: number;
  title: string;
  start_at: IsoDateTime;
  end_at: IsoDateTime;
  room: string;
}

export interface Speaker extends RecordBase {
  first_name: string;
  last_name: string;
  email: string;
  company: string;
  bio: string;
}

export interface Partner extends RecordBase {
  name: string;
  tier: PartnerTier;
  contact_email: string;
  notes: string;
}

export interface Attendee extends RecordBase {
  event_id: number;
  first_name: string;
  last_name: string;
  email: string;
  company: string;
  phone: string;
  notes: string;
}

export interface OutboxMessage {
  id: number;
  sender_id: number;
  to: string;
  subject: string;
  body: string;
  created_at: IsoDateTime;
}

export interface Me {
  id: number;
  username: string;
  /** Not returned by EventSim GET /me (checked 2026-11-10); mocks only. */
  display_name?: string;
  role: Role;
}

export type ArchivableEntity = 'editions' | 'events' | 'sessions' | 'speakers' | 'partners' | 'attendees';

export interface EventFilter {
  edition_id?: number;
  year?: number;
  type?: EventType;
  status?: RecordStatus;
  archived?: boolean;
}

/* ───────────────────────── Gateway side (contract) ───────────────────────── */

/** The nine layer flags of config/configurations.yaml, in pipeline order. */
export type LayerId =
  | 'security_prompt'
  | 'least_privilege'
  | 'spotlighting'
  | 'injection_detector'
  | 'pinned_tool_descriptions'
  | 'quotas'
  | 'output_filter'
  | 'preview_approval'
  | 'audit_log';

export type Layers = Record<LayerId, boolean>;

export interface GatewayConfig {
  id: ConfigId;
  description: string;
  layers: Layers;
  tools: string[];
  /** SHA-256 of the resolved configuration (config/loader.py). */
  hash: string;
}

/** What the gateway decided for one tool call. */
export type Decision = 'allowed' | 'blocked' | 'needs_approval';

/** Outcome of one gateway checkpoint for one call. */
/** 'rejected' = a person declined the approval (a decision, not a security block). */
export type CheckOutcome = 'passed' | 'failed' | 'held' | 'rejected' | 'not_reached' | 'off';

export interface Checkpoint {
  layer: LayerId | 'rights';
  outcome: CheckOutcome;
  /** Short human reason, e.g. "10 of 20 writes used". */
  note?: string;
}

export interface GatewayVerdict {
  decision: Decision;
  /** Rule identifier that produced a block, e.g. "output_filter.external_recipient". */
  rule?: string;
  reason?: string;
  checkpoints: Checkpoint[];
}

export type ToolKind = 'read' | 'write' | 'notify' | 'broad';

export interface ToolCall {
  /** Display id, e.g. "TC-0007". */
  id: string;
  conversationId: string;
  tool: string;
  kind: ToolKind;
  args: Record<string, unknown>;
  /** Identical calls grouped into one row, e.g. create_event × 10. */
  batch?: number;
  requestedAt: IsoDateTime;
  role: Role;
  config: ConfigId;
  verdict: GatewayVerdict;
  /** Present once the call reached EventSim (or was refused there). */
  result?: ToolResult;
  /** Set when the call belongs to an approval. */
  approvalId?: string;
  /**
   * Evaluation-only annotation from the harness oracle (canary seen leaving, forbidden
   * action). Never produced by the gateway in production; shown labelled as such.
   */
  oracle?: { finding: string; canary?: string };
}

export interface ToolResult {
  status: 'ok' | 'error' | 'withheld';
  /** Short summary for the activity panel. */
  summary: string;
  /** Raw (filtered) payload. */
  data?: unknown;
  /** Text fields that came from records: shown as untrusted data, never as instructions. */
  untrusted?: UntrustedExcerpt[];
  /** Fields the output filter removed. */
  redacted?: string[];
}

export interface UntrustedExcerpt {
  source: string; // e.g. "event 14 · description"
  text: string;
  /** Spotlighting / detector flagged instruction-like content. */
  flagged?: boolean;
  flagReason?: string;
}

/** 'oracle' = evaluation harness finding, shown only in evaluation/demo runs. */
export type MessageAuthor = 'user' | 'agent' | 'gateway' | 'oracle';

export interface PlanStep {
  text: string;
  kind: ToolKind;
}

export interface Message {
  id: string;
  author: MessageAuthor;
  at: IsoDateTime;
  text: string;
  plan?: PlanStep[];
  /** Tool calls the agent issued while producing this message. */
  toolCallIds?: string[];
  approvalId?: string;
}

export interface Conversation {
  id: string;
  title: string;
  role: Role;
  config: ConfigId;
  startedAt: IsoDateTime;
  messages: Message[];
  toolCalls: ToolCall[];
}

/* Approvals */

export type ApprovalStatus = 'pending' | 'approved' | 'rejected' | 'expired';

export interface ChangeLine {
  op: 'create' | 'archive' | 'link' | 'unarchive' | 'send';
  entity: 'edition' | 'event' | 'session' | 'speaker_link' | 'partner_link' | 'notification';
  label: string;
  detail?: string;
}

export interface ChangeGroup {
  op: ChangeLine['op'];
  entity: ChangeLine['entity'];
  count: number;
  lines: ChangeLine[];
}

export interface ChangePreview {
  title: string;
  /** Plain-language reassurance next to Approve, e.g. where the writes land and how to undo. */
  note?: string;
  groups: ChangeGroup[];
  /** Things deliberately not touched, e.g. registrations. */
  excluded: { label: string; reason: string }[];
}

export interface Approval {
  /** Display id, e.g. "AP-0042". */
  id: string;
  conversationId: string;
  toolCallIds: string[];
  requestedBy: Role;
  requestedAt: IsoDateTime;
  expiresAt: IsoDateTime;
  config: ConfigId;
  status: ApprovalStatus;
  summary: string;
  preview: ChangePreview;
  /** Single-use signature bound to the exact preview (hash). */
  previewHash: string;
  decidedAt?: IsoDateTime;
  decidedBy?: Role;
  signature?: string;
}

/* Audit */

export interface AuditEntry {
  seq: number;
  at: IsoDateTime;
  actorRole: Role;
  config: ConfigId;
  conversationId: string;
  toolCallId: string;
  tool: string;
  args: Record<string, unknown>;
  decision: Decision | 'approved' | 'rejected' | 'executed';
  rule?: string;
  reason?: string;
  hash: string;
  prevHash: string;
}

export type ChainCheck =
  | { status: 'intact'; checked: number; head: string }
  | {
      status: 'broken';
      checked: number;
      /** First entry whose stored hash does not match its recomputed hash. */
      brokenAt: number;
      expectedHash: string;
      storedHash: string;
      /** Fields that differ from what was hashed, when the verifier can tell (tamper simulation). */
      changedFields?: { field: string; stored: unknown; original: unknown }[];
    };

export interface AuditFilter {
  decision?: AuditEntry['decision'];
  role?: Role;
  config?: ConfigId;
  q?: string;
}

/* Attack bench */

export type AttackFamilyId = 'IPI' | 'DOC' | 'EXF' | 'PRV' | 'DST' | 'HRN' | 'SPL' | 'TDP';

export interface AttackFamily {
  id: AttackFamilyId;
  name: string;
  /** One line: what the family tries to make the agent do. */
  goal: string;
  threat: string; // threat-model id, e.g. "T1"
}

export type OracleKind = 'forbidden_action' | 'canary_leak' | 'state_diff';

export interface Attack {
  /** e.g. "IPI-03" */
  id: string;
  family: AttackFamilyId;
  title: string;
  /** Where the payload is planted. */
  vector: string;
  payload: string;
  oracle: OracleKind;
}

export type RunStatus = 'queued' | 'running' | 'done' | 'error';
export type AttackOutcome = 'blocked' | 'succeeded';

export interface AttackRun {
  id: string;
  attackId: string;
  config: ConfigId;
  status: RunStatus;
  outcome?: AttackOutcome;
  oracle?: {
    kind: OracleKind;
    /** Why the oracle decided, e.g. "canary EG-CANARY-PN-7Q2F found in outbox message 4". */
    detail: string;
    /** Rule that stopped it, when blocked. */
    blockedBy?: string;
  };
  /** Audit sequence numbers for this run (empty when audit_log is off). */
  auditSeqs: number[];
  startedAt: IsoDateTime;
  durationMs?: number;
}

/* Results */

export interface Interval {
  value: number;
  low: number;
  high: number;
}

export type MetricId =
  | 'attack_success'
  | 'task_success'
  | 'false_refusal'
  | 'approvals_per_task'
  | 'latency_s'
  | 'cost_usd';

export interface MetricMeta {
  id: MetricId;
  label: string;
  unit: 'ratio' | 'count' | 'seconds' | 'usd';
  /** Which direction is better. */
  better: 'lower' | 'higher';
  description: string;
}

export interface ConfigResult {
  config: ConfigId;
  metrics: Record<MetricId, Interval>;
  /** Attack success per family. */
  byFamily: Record<AttackFamilyId, Interval>;
  nAttacks: number;
  nTasks: number;
}

export interface ResultsSet {
  id: string;
  generatedAt: IsoDateTime;
  /** True for bundled sample data: never present as measured. */
  synthetic: boolean;
  method: string;
  confidence: number; // e.g. 0.95
  repetitions: number;
  configs: ConfigResult[];
}

/* ───────────────────────── Resource interfaces ───────────────────────── */

export interface CallContext {
  role: Role;
  config: ConfigId;
  signal?: AbortSignal;
}

export interface EventsApi {
  me(ctx: CallContext): Promise<Me>;
  listEditions(ctx: CallContext, opts?: { archived?: boolean }): Promise<Edition[]>;
  listEvents(ctx: CallContext, filter?: EventFilter): Promise<EventRecord[]>;
  getEvent(ctx: CallContext, id: number): Promise<EventRecord>;
  archive(ctx: CallContext, entity: ArchivableEntity, id: number): Promise<StatusRecord | RecordBase>;
  unarchive(ctx: CallContext, entity: ArchivableEntity, id: number): Promise<StatusRecord | RecordBase>;
  outbox(ctx: CallContext): Promise<OutboxMessage[]>;
}

export interface SessionsApi {
  list(ctx: CallContext, opts?: { event_id?: number; speaker_id?: number; archived?: boolean }): Promise<Session[]>;
}

export interface SpeakersApi {
  list(ctx: CallContext, opts?: { q?: string; archived?: boolean }): Promise<Speaker[]>;
  forSession(ctx: CallContext, sessionId: number): Promise<Speaker[]>;
}

export interface PartnersApi {
  list(ctx: CallContext, opts?: { q?: string; event_id?: number; tier?: PartnerTier }): Promise<Partner[]>;
}

export interface AttendeesApi {
  /** Admin only: EventSim answers 403 for reader and editor. */
  list(ctx: CallContext, opts: { event_id: number }): Promise<Attendee[]>;
}

/** Streaming updates from a running agent turn. */
export type AgentEvent =
  | { type: 'message'; message: Message }
  | { type: 'tool_call'; call: ToolCall }
  | { type: 'tool_update'; call: ToolCall }
  | { type: 'approval'; approval: Approval }
  | { type: 'done' };

export interface ConversationsApi {
  list(ctx: CallContext): Promise<Conversation[]>;
  get(ctx: CallContext, id: string): Promise<Conversation>;
  /** Sends a user message; the agent turn streams back through onEvent. */
  send(ctx: CallContext, conversationId: string, text: string, onEvent: (e: AgentEvent) => void): Promise<void>;
  create(ctx: CallContext, title: string): Promise<Conversation>;
  /** Live updates for one conversation (approvals decided elsewhere, agent continuing). */
  subscribe(conversationId: string, onEvent: (e: AgentEvent) => void): () => void;
}

export interface ToolCallsApi {
  list(ctx: CallContext, conversationId: string): Promise<ToolCall[]>;
}

export interface ApprovalsApi {
  list(ctx: CallContext, opts?: { status?: ApprovalStatus }): Promise<Approval[]>;
  get(ctx: CallContext, id: string): Promise<Approval>;
  /** Signs the exact preview hash; single use. Agent continues through onEvent. */
  approve(ctx: CallContext, id: string, onEvent?: (e: AgentEvent) => void): Promise<Approval>;
  reject(ctx: CallContext, id: string, reason?: string, onEvent?: (e: AgentEvent) => void): Promise<Approval>;
  /** Fires whenever any approval is created or changes state. */
  subscribe(onChange: () => void): () => void;
}

export interface AuditApi {
  list(ctx: CallContext, filter?: AuditFilter): Promise<AuditEntry[]>;
  verify(ctx: CallContext, opts?: { simulateTamper?: boolean }): Promise<ChainCheck>;
}

export interface GatewayApi {
  configs(ctx: CallContext): Promise<GatewayConfig[]>;
  active(ctx: CallContext): Promise<GatewayConfig>;
  /** Activates a preset or a custom layer set (custom = id of the closest preset + overrides). */
  activate(ctx: CallContext, id: ConfigId, layers?: Layers): Promise<GatewayConfig>;
}

export interface AttacksApi {
  families(ctx: CallContext): Promise<AttackFamily[]>;
  list(ctx: CallContext): Promise<Attack[]>;
  runs(ctx: CallContext, opts?: { config?: ConfigId }): Promise<AttackRun[]>;
  /** Starts runs; updates stream through onUpdate until each run is done. */
  run(ctx: CallContext, attackIds: string[], config: ConfigId, onUpdate: (run: AttackRun) => void): Promise<AttackRun[]>;
}

export interface ResultsApi {
  latest(ctx: CallContext): Promise<ResultsSet>;
  metrics(): MetricMeta[];
}

export type DataSource = 'live' | 'mock';

export interface Api {
  events: EventsApi;
  sessions: SessionsApi;
  speakers: SpeakersApi;
  partners: PartnersApi;
  attendees: AttendeesApi;
  conversations: ConversationsApi;
  toolCalls: ToolCallsApi;
  approvals: ApprovalsApi;
  audit: AuditApi;
  gateway: GatewayApi;
  attacks: AttacksApi;
  results: ResultsApi;
  /** Where each resource's data comes from, so pages can label sample data. */
  source: Record<keyof Omit<Api, 'source'>, DataSource>;
}

export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;
  constructor(status: number, detail: string) {
    super(`${status}: ${detail}`);
    this.status = status;
    this.detail = detail;
  }
}
