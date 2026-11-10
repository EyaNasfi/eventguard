/**
 * Gateway vocabulary shared by mocks and pages: the nine layers of
 * config/configurations.yaml, the C0–C4 presets, and tool metadata.
 *
 * C0 mirrors configurations.yaml today. C1–C4 are stubs there ("Planned: …");
 * the layer sets below follow those planned descriptions.
 */
import type { ConfigId, LayerId, Layers, Role, ToolKind } from './types';

export interface LayerMeta {
  id: LayerId;
  label: string;
  /** One line: what this layer stops. */
  blocks: string;
  /** Configuration that first turns it on. */
  since: ConfigId;
}

export const LAYERS: readonly LayerMeta[] = [
  {
    id: 'security_prompt',
    label: 'Security system prompt',
    blocks: 'Tells the model that record text is data and that out-of-scope requests are refused.',
    since: 'C1',
  },
  {
    id: 'least_privilege',
    label: 'Least-privilege tools',
    blocks: 'Removes the broad tools (update_record, raw_api_call) so the agent can only do what the task needs.',
    since: 'C2',
  },
  {
    id: 'quotas',
    label: 'Write quotas',
    blocks: 'Caps writes at 120 and archives at 12 per task, which stops mass-archive "clean-ups".',
    since: 'C2',
  },
  {
    id: 'preview_approval',
    label: 'Preview and approval',
    blocks: 'Holds every write until a person signs its exact preview. Each signature works once.',
    since: 'C2',
  },
  {
    id: 'output_filter',
    label: 'Output filter',
    blocks: 'Refuses arguments and replies that carry canaries, secrets or an outside recipient.',
    since: 'C3',
  },
  {
    id: 'spotlighting',
    label: 'Spotlighting',
    blocks: 'Wraps text from records in data markers so instructions hidden inside are not followed.',
    since: 'C3',
  },
  {
    id: 'audit_log',
    label: 'Hash-chained audit log',
    blocks: 'Records every call and decision in a chain where any later edit is detectable.',
    since: 'C3',
  },
  {
    id: 'injection_detector',
    label: 'Injection detector',
    blocks: 'Scores tool results for instruction-like text and quarantines flagged fields before the model reads them.',
    since: 'C4',
  },
  {
    id: 'pinned_tool_descriptions',
    label: 'Pinned tool descriptions',
    blocks: 'Rejects any tool whose description changed since review (tool "rug-pull").',
    since: 'C4',
  },
];

export const LAYER_BY_ID = Object.fromEntries(LAYERS.map((l) => [l.id, l])) as Record<LayerId, LayerMeta>;

const ORDER: Record<ConfigId, number> = { C0: 0, C1: 1, C2: 2, C3: 3, C4: 4 };

export function presetLayers(config: ConfigId): Layers {
  return Object.fromEntries(LAYERS.map((l) => [l.id, ORDER[l.since] <= ORDER[config]])) as Layers;
}

export const CONFIG_SUMMARY: Record<ConfigId, string> = {
  C0: 'No protection. The gateway passes every call through and broad tools are available.',
  C1: 'C0 plus a security system prompt.',
  C2: 'C1 plus least-privilege tools, write quotas and human approval of every write.',
  C3: 'C2 plus the output filter, spotlighting and the hash-chained audit log.',
  C4: 'C3 plus the injection detector and pinned tool descriptions.',
};

/** Name of a config whose preset equals these layers, or null when customised. */
export function matchPreset(layers: Layers): ConfigId | null {
  for (const id of ['C0', 'C1', 'C2', 'C3', 'C4'] as const) {
    const p = presetLayers(id);
    if (LAYERS.every((l) => p[l.id] === layers[l.id])) return id;
  }
  return null;
}

export function protectionCount(layers: Layers): number {
  return LAYERS.filter((l) => layers[l.id]).length;
}

export interface ToolMeta {
  name: string;
  kind: ToolKind;
  minRole: Role;
  c0Only?: boolean;
}

export const TOOLS: readonly ToolMeta[] = [
  { name: 'list_editions', kind: 'read', minRole: 'reader' },
  { name: 'get_edition', kind: 'read', minRole: 'reader' },
  { name: 'list_events', kind: 'read', minRole: 'reader' },
  { name: 'get_event', kind: 'read', minRole: 'reader' },
  { name: 'list_sessions', kind: 'read', minRole: 'reader' },
  { name: 'get_session', kind: 'read', minRole: 'reader' },
  { name: 'list_speakers', kind: 'read', minRole: 'reader' },
  { name: 'get_speaker', kind: 'read', minRole: 'reader' },
  { name: 'list_partners', kind: 'read', minRole: 'reader' },
  { name: 'get_partner', kind: 'read', minRole: 'reader' },
  { name: 'list_attendees', kind: 'read', minRole: 'admin' },
  { name: 'get_attendee', kind: 'read', minRole: 'admin' },
  { name: 'search_records', kind: 'read', minRole: 'reader' },
  { name: 'search_procedures', kind: 'read', minRole: 'reader' },
  { name: 'create_edition', kind: 'write', minRole: 'admin' },
  { name: 'create_event', kind: 'write', minRole: 'editor' },
  { name: 'create_session', kind: 'write', minRole: 'editor' },
  { name: 'create_speaker', kind: 'write', minRole: 'editor' },
  { name: 'create_partner', kind: 'write', minRole: 'editor' },
  { name: 'create_attendee', kind: 'write', minRole: 'admin' },
  { name: 'link_speaker_to_session', kind: 'write', minRole: 'editor' },
  { name: 'link_partner_to_event', kind: 'write', minRole: 'editor' },
  { name: 'archive_record', kind: 'write', minRole: 'editor' },
  { name: 'unarchive_record', kind: 'write', minRole: 'editor' },
  { name: 'send_notification', kind: 'notify', minRole: 'editor' },
  { name: 'update_record', kind: 'broad', minRole: 'editor', c0Only: true },
  { name: 'raw_api_call', kind: 'broad', minRole: 'reader', c0Only: true },
];

export const TOOL_BY_NAME = Object.fromEntries(TOOLS.map((t) => [t.name, t])) as Record<string, ToolMeta>;

export function toolsFor(layers: Layers): string[] {
  return TOOLS.filter((t) => !(t.c0Only && layers.least_privilege)).map((t) => t.name);
}

export const QUOTA = { writes: 120, archives: 12 } as const;

/** Domains the output filter treats as internal recipients. */
export const INTERNAL_DOMAINS = ['rendez-vous.example.org'] as const;
