import { useCallback, useEffect, useMemo, useRef, useState, type DependencyList } from 'react';

export type AsyncState<T> =
  | { status: 'loading'; data: T | undefined; error: undefined }
  | { status: 'ready'; data: T; error: undefined }
  | { status: 'error'; data: T | undefined; error: unknown };

type Settled<T> = { key: object; ok: true; data: T } | { key: object; ok: false; error: unknown; data: T | undefined };

/**
 * Runs `load` on mount and whenever deps change; aborts stale requests and keeps the
 * last data while reloading. Loading is derived (the settled result belongs to an
 * older request key), so no state is set synchronously inside the effect.
 */
export function useAsync<T>(load: (signal: AbortSignal) => Promise<T>, deps: DependencyList): AsyncState<T> & { reload: () => void } {
  const [tick, setTick] = useState(0);
  // Deps are primitives (ids, filters); serialising them gives a stable request identity.
  const depsKey = JSON.stringify(deps);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const key = useMemo(() => ({}), [depsKey, tick]);
  const [settled, setSettled] = useState<Settled<T> | null>(null);
  const loadRef = useRef(load);

  useEffect(() => {
    loadRef.current = load;
  });

  useEffect(() => {
    const ctrl = new AbortController();
    loadRef
      .current(ctrl.signal)
      .then((data) => {
        if (!ctrl.signal.aborted) setSettled({ key, ok: true, data });
      })
      .catch((error: unknown) => {
        if (ctrl.signal.aborted || (error instanceof DOMException && error.name === 'AbortError')) return;
        setSettled((prev) => ({ key, ok: false, error, data: prev?.data }));
      });
    return () => ctrl.abort();
  }, [key]);

  const reload = useCallback(() => setTick((t) => t + 1), []);

  if (!settled || settled.key !== key) return { status: 'loading', data: settled?.data, error: undefined, reload };
  if (settled.ok) return { status: 'ready', data: settled.data, error: undefined, reload };
  return { status: 'error', data: settled.data, error: settled.error, reload };
}
