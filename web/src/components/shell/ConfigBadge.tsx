import { ShieldAlert, ShieldCheck, ShieldOff } from 'lucide-react';
import { Link } from 'react-router';
import type { GatewayConfig } from '../../api/types';
import { matchPreset, protectionCount, LAYERS } from '../../api/gateway-model';
import { cn } from '../../lib/cn';

export function configTone(c: Pick<GatewayConfig, 'layers'>): { tone: 'stop' | 'warn' | 'ok'; words: string } {
  const n = protectionCount(c.layers);
  if (n === 0) return { tone: 'stop', words: 'No protection' };
  if (!c.layers.preview_approval && !c.layers.output_filter) return { tone: 'warn', words: `Weak · ${n} of ${LAYERS.length} layers` };
  return { tone: 'ok', words: `Protected · ${n} of ${LAYERS.length} layers` };
}

const PILL = {
  stop: 'border-stop-line bg-stop-bg text-stop',
  warn: 'border-warn-line bg-warn-bg text-warn',
  ok: 'border-ok-line bg-ok-bg text-ok',
} as const;
const CHIP = { stop: 'bg-stop/20', warn: 'bg-warn/20', ok: 'bg-ok/20' } as const;
const ICON = { stop: ShieldOff, warn: ShieldAlert, ok: ShieldCheck } as const;

/** The active configuration, impossible to miss: id chip + shield + plain words. Links to Gateway. */
export function ConfigBadge({ config, size = 'md', asLink = true }: { config: GatewayConfig | null; size?: 'md' | 'lg'; asLink?: boolean }) {
  if (!config) return <span className="eg-skeleton inline-block h-9 w-52 rounded-lg" aria-hidden />;
  const preset = matchPreset(config.layers);
  const { tone, words } = configTone(config);
  const label = preset ? config.id : `${config.id} custom`;
  const Icon = ICON[tone];
  const body = (
    <>
      <span className={cn('rounded px-1.5 py-0.5 font-mono font-bold', CHIP[tone], size === 'lg' ? 'text-sm' : 'text-xs')}>{label}</span>
      <Icon aria-hidden className="size-3.5 shrink-0" strokeWidth={2.2} />
      <span className={cn('font-medium whitespace-nowrap', size === 'lg' ? 'text-sm' : 'text-xs')}>{words}</span>
    </>
  );
  const cls = cn('eg-config inline-flex items-center gap-2 rounded-lg border px-2.5', PILL[tone], size === 'lg' ? 'h-10' : 'h-9');
  const a11y = `Active configuration ${label}: ${words}`;
  return asLink ? (
    <Link to="/gateway" className={cn(cls, 'hover:brightness-125')} aria-label={`${a11y}. Open gateway settings`} key={`${label}-${tone}`}>
      {body}
    </Link>
  ) : (
    <span className={cls} role="img" aria-label={a11y} key={`${label}-${tone}`}>
      {body}
    </span>
  );
}
