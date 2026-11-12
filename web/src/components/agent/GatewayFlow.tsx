import { ArrowRight, Ban, Check, Hourglass, Minus } from 'lucide-react';
import type { Checkpoint, ToolCall } from '../../api/types';
import { cn } from '../../lib/cn';

const LABEL: Record<Checkpoint['layer'], string> = {
  rights: 'Rights',
  least_privilege: 'Tools',
  quotas: 'Quota',
  output_filter: 'Filter',
  preview_approval: 'Approval',
  spotlighting: 'Spotlight',
  injection_detector: 'Detector',
  pinned_tool_descriptions: 'Pinned',
  security_prompt: 'Prompt',
  audit_log: 'Audit',
};

type NodeState = 'passed' | 'held' | 'failed' | 'off' | 'idle';

interface FlowNode {
  key: string;
  label: string;
  state: NodeState;
  sub: string;
}

/** The call the strip follows: waiting for a person first, then a block, then the latest. */
export function focusCall(calls: ToolCall[]): ToolCall | undefined {
  return (
    calls.find((c) => c.verdict.decision === 'needs_approval') ??
    [...calls].reverse().find((c) => c.verdict.decision === 'blocked' && c.verdict.rule !== 'preview_approval.rejected') ??
    [...calls].reverse().find((c) => c.oracle) ??
    calls.at(-1)
  );
}

function nodesFor(call: ToolCall): FlowNode[] {
  const nodes: FlowNode[] = [{ key: 'agent', label: 'Agent', state: 'passed', sub: 'Requested' }];
  for (const c of call.verdict.checkpoints) {
    const state: NodeState = c.outcome === 'passed' ? 'passed' : c.outcome === 'held' ? 'held' : c.outcome === 'failed' || c.outcome === 'rejected' ? 'failed' : c.outcome === 'off' ? 'off' : 'idle';
    const sub = c.outcome === 'passed' ? 'Cleared' : c.outcome === 'held' ? 'Pending' : c.outcome === 'failed' ? 'Blocked' : c.outcome === 'rejected' ? 'Rejected' : c.outcome === 'off' ? 'Off' : 'Not reached';
    nodes.push({ key: c.layer, label: LABEL[c.layer], state, sub });
  }
  const reached = call.verdict.decision === 'allowed' && call.result?.status === 'ok';
  nodes.push({ key: 'eventsim', label: 'EventSim', state: reached ? 'passed' : 'idle', sub: reached ? 'Executed' : call.verdict.decision === 'blocked' ? 'Not reached' : 'Target' });
  return nodes;
}

const NODE: Record<NodeState, string> = {
  passed: 'border-ok-line bg-surface-2 text-ok',
  held: 'border-2 border-hold bg-hold-bg text-hold font-semibold',
  failed: 'border-2 border-stop bg-stop-bg text-stop font-semibold',
  off: 'border-dashed border-line-strong bg-transparent text-muted',
  idle: 'border-line bg-surface-2 text-muted',
};

const ICON: Record<NodeState, typeof Check> = { passed: Check, held: Hourglass, failed: Ban, off: Minus, idle: Minus };

/**
 * Gateway execution flow: the path of one call through the gateway checkpoints to
 * EventSim, with where it stopped. Every node carries a word, never colour alone.
 */
export function GatewayFlow({ call }: { call: ToolCall }) {
  const nodes = nodesFor(call);
  const stop = nodes.find((n) => n.state === 'held' || n.state === 'failed');
  const headline = stop
    ? stop.state === 'held'
      ? { text: `Halted at: ${stop.label} (waiting for a person)`, cls: 'text-hold' }
      : { text: `Stopped at: ${stop.label}`, cls: 'text-stop' }
    : nodes.at(-1)?.state === 'passed'
      ? { text: 'Reached EventSim', cls: 'text-ok' }
      : { text: 'In progress', cls: 'text-muted' };

  return (
    <section aria-labelledby="flow-title" className="rounded-xl border border-line bg-surface-1 p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2 border-b border-line pb-3">
        <h3 id="flow-title" className="m-0 font-mono text-xs font-medium tracking-wider text-muted uppercase">
          Gateway execution flow
          <span className="ml-2 tracking-normal normal-case">
            · <span className="text-text">{call.tool}</span>
            {call.batch ? ` ×${call.batch}` : ''}
          </span>
        </h3>
        <p className={cn('m-0 font-mono text-xs font-medium', headline.cls)} aria-live="polite">
          {headline.text}
        </p>
      </div>
      <ol className="m-0 flex list-none items-start gap-1 overflow-x-auto p-0 py-1">
        {nodes.map((n, i) => {
          const Icon = ICON[n.state];
          return (
            <li key={n.key} className="flex min-w-0 flex-1 items-start gap-1">
              {i > 0 ? <ArrowRight aria-hidden className={cn('mt-2 size-3 shrink-0', n.state === 'held' ? 'text-hold' : n.state === 'failed' ? 'text-stop' : 'text-line-strong')} /> : null}
              <div className={cn('flex min-w-[3.5rem] flex-1 flex-col items-center', (n.state === 'held' || n.state === 'failed') && 'min-w-[5.75rem] flex-[1.4]')}>
                <div className={cn('flex w-full items-center justify-center gap-1 rounded-lg border px-1.5 py-1.5 font-mono text-[0.6875rem] whitespace-nowrap', NODE[n.state])}>
                  {/* Icon only where the call stopped; the word under each node carries its state. */}
                  {n.state === 'held' || n.state === 'failed' ? <Icon aria-hidden className={cn('size-3 shrink-0', n.state === 'held' && 'eg-pulse')} strokeWidth={2.6} /> : null}
                  <span>{n.label}</span>
                </div>
                <span className={cn('mt-1 text-[0.6875rem]', n.state === 'held' ? 'font-semibold text-hold' : n.state === 'failed' ? 'font-semibold text-stop' : 'text-muted')}>{n.sub}</span>
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
