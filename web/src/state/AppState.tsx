import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { api, type CallContext, type ConfigId, type GatewayConfig, type Layers, type Role } from '../api';
import { presetLayers } from '../api/gateway-model';

interface AppState {
  role: Role;
  setRole: (r: Role) => void;
  config: GatewayConfig | null;
  /** Activates a preset, or custom layers on top of a preset id. */
  activate: (id: ConfigId, layers?: Layers) => Promise<void>;
  pendingApprovals: number;
  ctx: CallContext;
  /** Second breadcrumb segment for the current page (e.g. the conversation title). */
  crumb: string | null;
  setCrumb: (c: string | null) => void;
}

const Ctx = createContext<AppState | null>(null);

function readRole(): Role {
  try {
    const v = window.localStorage.getItem('eg.role');
    if (v === 'reader' || v === 'editor' || v === 'admin') return v;
  } catch {
    /* storage blocked */
  }
  return 'editor';
}

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [role, setRoleState] = useState<Role>(readRole);
  const [config, setConfig] = useState<GatewayConfig | null>(null);
  const [pendingApprovals, setPending] = useState(0);
  const [crumb, setCrumb] = useState<string | null>(null);

  const ctx = useMemo<CallContext>(() => ({ role, config: config?.id ?? 'C3' }), [role, config?.id]);

  const setRole = useCallback((r: Role) => {
    setRoleState(r);
    try {
      window.localStorage.setItem('eg.role', r);
    } catch {
      /* storage blocked */
    }
  }, []);

  useEffect(() => {
    void api.gateway.active({ role, config: 'C3' }).then(setConfig);
    // Active config is global, not per role.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    let alive = true;
    const refresh = () =>
      void api.approvals.list({ role, config: 'C3' }, { status: 'pending' }).then((xs) => {
        if (alive) setPending(xs.length);
      });
    refresh();
    const off = api.approvals.subscribe(refresh);
    // Expiry happens with time, not events.
    const t = window.setInterval(refresh, 15_000);
    return () => {
      alive = false;
      off();
      window.clearInterval(t);
    };
  }, [role]);

  const activate = useCallback(
    async (id: ConfigId, layers?: Layers) => {
      const next = await api.gateway.activate({ role, config: id }, id, layers ?? presetLayers(id));
      setConfig(next);
    },
    [role],
  );

  const value = useMemo(() => ({ role, setRole, config, activate, pendingApprovals, ctx, crumb, setCrumb }), [role, setRole, config, activate, pendingApprovals, ctx, crumb]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useApp(): AppState {
  const v = useContext(Ctx);
  if (!v) throw new Error('useApp outside AppStateProvider');
  return v;
}
