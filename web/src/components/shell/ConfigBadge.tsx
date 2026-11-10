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

const FILL = { stop: 'bg-stop text-on-accent', warn: 'bg-warn text-on-accent', ok: 'bg-ok text-on-accent' } as const;
const RING = { stop: 'border-stop text-stop', warn: 'border-warn text-warn', ok: 'border-ok text-ok' } as const;

/** The active configuration, impossible to miss: filled id block + plain words. Links to Gateway. */
export function ConfigBadge({ config, size = 'md', asLink = true }: { config: GatewayConfig | null; size?: 'md' | 'lg'; asLink?: boolean }) {
  if (!config) return <span className="eg-skeleton inline-block h-9 w-48 rounded-sm" aria-hidden />;
  const preset = matchPreset(config.layers);
  const { tone, words } = configTone(config);
  const label = preset ? config.id : `${config.id} custom`;
  const body = (
    <>
      <span className={cn('flex h-full items-center px-2.5 font-mono font-semibold', FILL[tone], size === 'lg' ? 'text-md' : 'text-sm')}>{label}</span>
      <span className={cn('px-2.5 font-semibold whitespace-nowrap', size === 'lg' ? 'text-sm' : 'text-xs')}>{words}</span>
    </>
  );
  const cls = cn('eg-config inline-flex items-center overflow-hidden rounded-sm border', RING[tone], size === 'lg' ? 'h-10' : 'h-9');
  const a11y = `Active configuration ${label}: ${words}`;
  return asLink ? (
    <Link to="/gateway" className={cn(cls, 'hover:bg-surface-2')} aria-label={`${a11y}. Open gateway settings`} key={`${label}-${tone}`}>
      {body}
    </Link>
  ) : (
    <span className={cls} role="img" aria-label={a11y} key={`${label}-${tone}`}>
      {body}
    </span>
  );
}
