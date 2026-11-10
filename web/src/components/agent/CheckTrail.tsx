import { Check, Hourglass, Minus } from 'lucide-react';
import type { Checkpoint } from '../../api/types';
import { LAYER_BY_ID } from '../../api/gateway-model';
import { cn } from '../../lib/cn';
import { CHECK } from '../ui/status';
import { StatusChip } from '../ui/StatusChip';

const SHORT: Record<Checkpoint['layer'], string> = {
  rights: 'Role rights',
  least_privilege: 'Tool allowlist',
  quotas: 'Quota',
  output_filter: 'Output filter',
  preview_approval: 'Approval',
  spotlighting: 'Spotlighting',
  injection_detector: 'Detector',
  pinned_tool_descriptions: 'Pinned tools',
  security_prompt: 'Security prompt',
  audit_log: 'Audit log',
};

/**
 * The gateway checkpoints a call passed through, in order. Cleared checkpoints stay
 * quiet (name + check); the decisive one (held or refused) is a boxed stamp. On live
 * arrival they appear one after another: the call moving through the gateway.
 */
export function CheckTrail({ checkpoints, live, coveredBy }: { checkpoints: Checkpoint[]; live: boolean; coveredBy?: string }) {
  return (
    <ol aria-label="Gateway checkpoints" className="m-0 flex list-none flex-wrap items-center gap-x-1.5 gap-y-1.5 p-0 text-xs">
      {checkpoints.map((c, i) => {
        const label = SHORT[c.layer];
        const title = [c.layer === 'rights' ? 'EventSim role check' : LAYER_BY_ID[c.layer]?.label, c.note].filter(Boolean).join(': ');
        const covered = coveredBy && c.layer === 'preview_approval' && c.outcome === 'held';
        const decisive = !covered && (c.outcome === 'held' || c.outcome === 'failed' || c.outcome === 'rejected');
        return (
          <li key={c.layer} className={cn('flex items-center gap-1.5', live && 'eg-stamp-in')} style={live ? { animationDelay: `${i * 60}ms` } : undefined} title={title}>
            {i > 0 ? <span aria-hidden className="h-px w-2.5 bg-line-strong" /> : null}
            {covered ? (
              <span className="inline-flex items-center gap-1 text-muted">
                <Hourglass aria-hidden className="size-3 text-hold" strokeWidth={2.4} />
                {label}: in <span className="font-mono text-text">{coveredBy}</span> above
              </span>
            ) : decisive ? (
              <>
                <span className="font-semibold text-text">{label}</span>
                <StatusChip spec={CHECK[c.outcome]} variant="stamp" />
                {c.note ? <span className="text-muted">{c.note}</span> : null}
              </>
            ) : c.outcome === 'passed' ? (
              <span className="inline-flex items-center gap-1 text-muted">
                <Check aria-hidden className="size-3 text-ok" strokeWidth={3} />
                {label}
                <span className="sr-only">: cleared{c.note ? `, ${c.note}` : ''}</span>
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-muted">
                <Minus aria-hidden className="size-3" />
                {label}
                <span className="rounded-xs border border-line-strong px-1 text-[0.6875rem] leading-4 uppercase tracking-wide">{c.outcome === 'off' ? 'off' : 'not reached'}</span>
                <span className="sr-only">{c.outcome === 'off' ? ' in this configuration' : ''}</span>
              </span>
            )}
          </li>
        );
      })}
    </ol>
  );
}
