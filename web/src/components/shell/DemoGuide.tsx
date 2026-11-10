import { ListChecks, Play, X } from 'lucide-react';
import { useEffect, useId, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router';
import { USE_MOCKS } from '../../api';
import { DEMO_STEPS, prepareStep, type DemoStep } from '../../api/demo';
import { cn } from '../../lib/cn';
import { useApp } from '../../state/AppState';
import { Switch } from '../ui/Field';

function readProjector(): boolean {
  try {
    return window.localStorage.getItem('eg.projector') === '1';
  } catch {
    return false;
  }
}

/**
 * The 5-minute jury script, one click per step. Opened from the top bar or by
 * /assistant?guide=1 (the demo page's launch button).
 */
export function DemoGuide() {
  const [params, setParams] = useSearchParams();
  const wantOpen = params.get('guide') === '1';
  const [open, setOpen] = useState(wantOpen);
  const [current, setCurrent] = useState<DemoStep['id'] | null>(null);
  const { activate } = useApp();
  const navigate = useNavigate();
  const panelId = useId();
  const buttonRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const [projector, setProjectorState] = useState(readProjector);
  const setProjector = (on: boolean) => {
    setProjectorState(on);
    try {
      window.localStorage.setItem('eg.projector', on ? '1' : '0');
    } catch {
      /* storage blocked */
    }
  };
  // Root font size drives every rem in the app.
  useEffect(() => {
    document.documentElement.style.fontSize = projector ? '112.5%' : '';
  }, [projector]);

  // Opened by ?guide=1 (the demo page's launch button): adjust during render, then drop the param.
  if (wantOpen && !open) setOpen(true);
  useEffect(() => {
    if (!wantOpen) return;
    const next = new URLSearchParams(params);
    next.delete('guide');
    setParams(next, { replace: true });
  }, [wantOpen, params, setParams]);

  useEffect(() => {
    if (!open) return;
    panelRef.current?.querySelector<HTMLButtonElement>('button[data-step]')?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setOpen(false);
        buttonRef.current?.focus();
      }
    };
    const onPointer = (e: PointerEvent) => {
      const t = e.target as Node;
      if (!panelRef.current?.contains(t) && !buttonRef.current?.contains(t)) setOpen(false);
    };
    window.addEventListener('keydown', onKey);
    window.addEventListener('pointerdown', onPointer);
    return () => {
      window.removeEventListener('keydown', onKey);
      window.removeEventListener('pointerdown', onPointer);
    };
  }, [open]);

  if (!USE_MOCKS) return null;

  const run = async (step: DemoStep) => {
    prepareStep(step);
    await activate(step.config);
    setCurrent(step.id);
    setOpen(false);
    navigate(`/assistant?new=1&prompt=${encodeURIComponent(step.prompt)}`);
  };

  return (
    <div className="relative">
      <button
        ref={buttonRef}
        type="button"
        aria-expanded={open}
        aria-controls={open ? panelId : undefined}
        onClick={() => setOpen((o) => !o)}
        className={cn('inline-flex h-9 items-center gap-2 rounded-sm border px-3 text-sm font-semibold', open ? 'border-info-line bg-info-bg text-text' : 'border-line-strong text-muted hover:text-text')}
      >
        <ListChecks aria-hidden className="size-3.5" />
        <span className="hidden lg:inline">Demo guide</span>
      </button>
      {open ? (
        <div ref={panelRef} id={panelId} role="region" aria-label="Demo guide" className="eg-pop absolute top-10 right-0 z-40 w-[26rem] max-w-[calc(100vw-2rem)] rounded-sm border border-line-strong bg-surface-1">
          <div className="flex items-center gap-2 border-b border-line px-4 py-2.5">
            <p className="m-0 text-sm font-semibold">Jury demo · 3 steps</p>
            <button type="button" aria-label="Close demo guide" onClick={() => setOpen(false)} className="-mr-1.5 ml-auto rounded-xs p-1.5 text-muted hover:text-text">
              <X aria-hidden className="size-3.5" />
            </button>
          </div>
          <ol className="m-0 list-none p-0">
            {DEMO_STEPS.map((step, i) => (
              <li key={step.id} className="grid grid-cols-[2.75rem_minmax(0,1fr)] border-b border-line last:border-b-0">
                <span aria-hidden className={cn('pt-3 text-center font-mono text-xl font-light', current === step.id ? 'text-text' : 'text-muted')}>
                  {i + 1}
                </span>
                <div className="py-3 pr-4">
                  <p className="m-0 flex items-center gap-2 text-sm font-semibold">
                    {step.title}
                    <span className="rounded-xs border border-line-strong px-1 font-mono text-xs text-muted">{step.config}</span>
                  </p>
                  <p className="m-0 mt-0.5 text-xs text-muted">{step.expect}</p>
                  <button
                    type="button"
                    data-step={step.id}
                    onClick={() => void run(step)}
                    className="mt-2 inline-flex h-7 items-center gap-1.5 rounded-sm border border-line-strong bg-surface-2 px-2.5 text-xs font-semibold hover:bg-surface-3 active:scale-[0.97]"
                  >
                    <Play aria-hidden className="size-3" />
                    {current === step.id ? 'Run again' : 'Set up and open'}
                  </button>
                </div>
              </li>
            ))}
          </ol>
          <div className="flex flex-col gap-2 border-t border-line px-4 py-3">
            <Switch checked={projector} onChange={setProjector} label="Projector size" description="Enlarges all text and controls by 12.5% so the room can read them." />
            <p className="m-0 text-xs text-muted">Each step resets the fictional data, plants or removes the injected note, and switches the configuration.</p>
          </div>
        </div>
      ) : null}
    </div>
  );
}
