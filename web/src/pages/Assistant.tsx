import { ArrowUp, MessageSquarePlus, Radar, ShieldAlert } from 'lucide-react';
import { useCallback, useEffect, useId, useMemo, useRef, useState, type FormEvent, type KeyboardEvent } from 'react';
import { useSearchParams } from 'react-router';
import { api, type AgentEvent, type Approval, type Conversation, type Message, type ToolCall } from '../api';
import { ChatMessage } from '../components/agent/ChatMessage';
import { CueSheet } from '../components/agent/CueSheet';
import { Button } from '../components/ui/Button';
import { EmptyState, Skeleton } from '../components/ui/Feedback';
import { APPROVAL, DECISION, RUN } from '../components/ui/status';
import { StatusChip } from '../components/ui/StatusChip';
import { Tabs, tabPanelProps } from '../components/ui/Tabs';
import { useToast } from '../components/ui/Toast';
import { cn } from '../lib/cn';
import { useMediaQuery } from '../lib/useMediaQuery';
import { useApp } from '../state/AppState';
import { SampleDataNote } from '../components/shell/AppShell';

const SUGGESTIONS = ['Duplicate the 2026 edition into 2027, skip archived events.', 'Archive the 2025 events.', 'What can you do?'];

/** Conversation kept across page visits within the session. */
let lastConversationId: string | null = null;

interface ConvState {
  conv: Conversation | null;
  messages: Message[];
  calls: ToolCall[];
  approvals: Record<string, Approval>;
  running: boolean;
}

export default function AssistantPage() {
  const { ctx, role, config, setCrumb } = useApp();
  const toast = useToast();
  const [params, setParams] = useSearchParams();
  const [state, setState] = useState<ConvState>({ conv: null, messages: [], calls: [], approvals: {}, running: false });
  const [draft, setDraft] = useState('');
  const wide = useMediaQuery('(min-width: 72rem)');
  const [live, setLive] = useState<Set<string>>(() => new Set());
  const [pane, setPane] = useState<'chat' | 'activity'>('chat');
  const paneId = useId();
  const chatEnd = useRef<HTMLDivElement>(null);
  const activityRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const ctxRef = useRef(ctx);
  useEffect(() => {
    ctxRef.current = ctx;
  }, [ctx]);

  const approvalIdsRef = useRef<string[]>([]);
  useEffect(() => {
    approvalIdsRef.current = Object.keys(state.approvals);
  }, [state.approvals]);

  const wantNew = params.get('new') === '1';
  const promptParam = params.get('prompt');
  // A prompt handed over by the demo guide fills the composer (adjusted during render).
  const [seenPrompt, setSeenPrompt] = useState<string | null>(null);
  if (promptParam && promptParam !== seenPrompt) {
    setSeenPrompt(promptParam);
    setDraft(promptParam);
  }
  // Once consumed, the same prompt can be handed over again (demo steps 2 and 3 share it).
  if (!promptParam && seenPrompt !== null) setSeenPrompt(null);

  // ?new=1 asks for a fresh conversation once; the request survives the param being removed.
  const [convRequest, setConvRequest] = useState({ n: 0, fresh: wantNew });
  const [handledNew, setHandledNew] = useState(wantNew);
  if (wantNew && !handledNew) {
    setHandledNew(true);
    setConvRequest((r) => ({ n: r.n + 1, fresh: true }));
  }
  if (!wantNew && handledNew) setHandledNew(false);

  /* Drop the handover params once read. */
  useEffect(() => {
    if (!wantNew && !promptParam) return;
    const next = new URLSearchParams(params);
    next.delete('new');
    next.delete('prompt');
    setParams(next, { replace: true });
    window.setTimeout(() => inputRef.current?.focus(), 50);
  }, [wantNew, promptParam, params, setParams]);

  /* Load or create the conversation. */
  useEffect(() => {
    let alive = true;
    (async () => {
      const c = ctxRef.current;
      let conv: Conversation | null = null;
      if (!convRequest.fresh && lastConversationId) conv = await api.conversations.get(c, lastConversationId).catch(() => null);
      if (!conv) conv = await api.conversations.create(c, 'New conversation');
      lastConversationId = conv.id;
      const ids = [...new Set(conv.toolCalls.map((t) => t.approvalId).filter((x): x is string => Boolean(x)))];
      const aps = await Promise.all(ids.map((id) => api.approvals.get(c, id).catch(() => null)));
      if (!alive) return;
      setState({
        conv,
        messages: conv.messages,
        calls: conv.toolCalls,
        approvals: Object.fromEntries(aps.filter((a): a is Approval => Boolean(a)).map((a) => [a.id, a])),
        running: false,
      });
      setLive(new Set());
    })();
    return () => {
      alive = false;
    };
  }, [convRequest]);

  const convId = state.conv?.id;

  /* Live events for this conversation (agent turns and approvals decided anywhere). */
  useEffect(() => {
    if (!convId) return;
    const onEvent = (e: AgentEvent) => {
      if (e.type === 'tool_call') setLive((s) => new Set(s).add(e.call.id));
      if (e.type === 'message') setLive((s) => new Set(s).add(e.message.id));
      setState((s) => reduce(s, e));
    };
    const offConv = api.conversations.subscribe(convId, onEvent);
    const offAp = api.approvals.subscribe(() => {
      const ids = approvalIdsRef.current;
      void Promise.all(ids.map((id) => api.approvals.get(ctxRef.current, id).catch(() => null))).then((aps) =>
        setState((cur) => ({ ...cur, approvals: { ...cur.approvals, ...Object.fromEntries(aps.filter((a): a is Approval => Boolean(a)).map((a) => [a.id, a])) } })),
      );
    });
    return () => {
      offConv();
      offAp();
    };
  }, [convId]);

  /* Keep the newest chat line in view. */
  useEffect(() => {
    chatEnd.current?.scrollIntoView({ block: 'end', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
  }, [state.messages.length]);
  useEffect(() => {
    const el = activityRef.current;
    if (!el || !state.running) return;
    el.scrollTo({ top: el.scrollHeight, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
  }, [state.calls.length, state.running]);

  /* When a run ends, bring the step that matters (blocked or leaked) into view. */
  const wasRunning = useRef(false);
  useEffect(() => {
    if (wasRunning.current && !state.running) {
      const alarm = activityRef.current?.querySelector('[data-alarm]');
      alarm?.scrollIntoView({ block: 'center', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
    }
    wasRunning.current = state.running;
  }, [state.running]);

  /* Breadcrumb: Assistant / <conversation title>. */
  const title = state.conv?.title;
  useEffect(() => {
    setCrumb(title && title !== 'New conversation' ? title : null);
    return () => setCrumb(null);
  }, [title, setCrumb]);

  const send = useCallback(
    async (text: string) => {
      const t = text.trim();
      if (!t || !convId || state.running) return;
      setDraft('');
      // The run header records who asked and under which configuration.
      setState((s) => ({
        ...s,
        running: true,
        conv: s.conv ? { ...s.conv, role, config: config?.id ?? s.conv.config, title: s.messages.length ? s.conv.title : t.length > 48 ? `${t.slice(0, 47)}…` : t } : s.conv,
      }));
      try {
        await api.conversations.send(ctx, convId, t, () => undefined);
      } catch (err) {
        toast.show(RUN.error, 'The agent could not finish', err instanceof Error ? err.message : String(err));
      } finally {
        setState((s) => ({ ...s, running: false }));
      }
    },
    [ctx, convId, state.running, toast, role, config?.id],
  );

  const decide = useCallback(
    async (approvalId: string, approve: boolean) => {
      try {
        const a = approve ? await api.approvals.approve(ctx, approvalId) : await api.approvals.reject(ctx, approvalId);
        setState((s) => ({ ...s, approvals: { ...s.approvals, [a.id]: a } }));
        toast.show(approve ? APPROVAL.approved : APPROVAL.rejected, approve ? `${a.id} signed and used` : `${a.id} rejected`, approve ? a.summary : 'Nothing was written.');
      } catch (err) {
        toast.show(RUN.error, `${approvalId} could not be decided`, err instanceof Error ? err.message : String(err));
        const fresh = await api.approvals.get(ctx, approvalId).catch(() => null);
        if (fresh) setState((s) => ({ ...s, approvals: { ...s.approvals, [fresh.id]: fresh } }));
      }
    },
    [ctx, toast],
  );

  const review = (approvalId: string) => {
    setPane('activity');
    window.setTimeout(() => {
      const el = document.getElementById(`preview-${approvalId}`);
      el?.scrollIntoView({ block: 'center', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
      el?.focus({ preventScroll: true });
    }, 30);
  };

  const newConversation = async () => {
    const conv = await api.conversations.create(ctx, 'New conversation');
    lastConversationId = conv.id;
    setState({ conv, messages: [], calls: [], approvals: {}, running: false });
    setLive(new Set());
    inputRef.current?.focus();
  };

  // Counts the operator can reconcile: approvals waiting (not held calls), security blocks
  // (not a person's rejection), and leaks the evaluation oracle saw.
  const tally = useMemo(() => {
    const waiting = new Set<string>();
    let allowed = 0;
    let blocked = 0;
    let leaked = 0;
    for (const c of state.calls) {
      if (c.oracle) leaked += 1;
      if (c.verdict.decision === 'allowed') allowed += 1;
      else if (c.verdict.decision === 'blocked' && c.verdict.rule !== 'preview_approval.rejected') blocked += 1;
      else if (c.verdict.decision === 'needs_approval' && c.approvalId && state.approvals[c.approvalId]?.status !== 'expired') waiting.add(c.approvalId);
    }
    return { allowed, waiting: waiting.size, blocked, leaked };
  }, [state.calls, state.approvals]);

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    void send(draft);
  };
  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      void send(draft);
    }
  };

  const loading = !state.conv;
  const runConfig = state.conv && state.messages.length ? state.conv.config : config?.id;

  return (
    <div className="flex h-full min-h-0 flex-col">
      <h1 className="sr-only">Assistant</h1>
      <div className="flex justify-end border-b border-line px-4 py-1.5">
        <SampleDataNote what="The agent is a scripted demo and gateway decisions are simulated; Events data" />
      </div>
      <div className="border-b border-line px-4 pt-2 min-[72rem]:hidden">
        <Tabs
          idBase={paneId}
          label="Assistant panes"
          value={pane}
          onChange={setPane}
          className="border-b-0"
          items={[
            { id: 'chat', label: 'Chat' },
            { id: 'activity', label: 'Agent activity', count: state.calls.length },
          ]}
        />
      </div>

      <div className="grid min-h-0 flex-1 min-[72rem]:grid-cols-[minmax(21rem,32.5rem)_minmax(0,1fr)]">
        {/* Chat */}
        <section
          aria-label="Chat"
          {...(wide ? {} : tabPanelProps(paneId, 'chat'))}
          tabIndex={-1}
          className={cn('min-h-0 flex-col border-line min-[72rem]:flex min-[72rem]:border-r', pane === 'chat' ? 'flex' : 'hidden')}
        >
          <div className="flex h-11 shrink-0 items-center gap-2 border-b border-line px-5">
            <p className="m-0 min-w-0 truncate text-sm font-semibold">{state.conv?.title ?? 'Conversation'}</p>
            {state.conv ? <span className="font-mono text-xs text-muted">{state.conv.id}</span> : null}
            <Button size="sm" variant="ghost" className="ml-auto" onClick={() => void newConversation()} disabled={state.running} icon={<MessageSquarePlus aria-hidden className="size-3.5" />}>
              New
            </Button>
          </div>

          <div className="min-h-0 flex-1 overflow-auto px-5 py-5">
            {loading ? (
              <Skeleton lines={4} />
            ) : state.messages.length === 0 ? (
              <div className="flex flex-col gap-4">
                <div>
                  <p className="m-0 text-md font-semibold">Ask for an operation on EventSim</p>
                  <p className="m-0 mt-1 max-w-[46ch] text-sm text-muted">
                    The agent plans the steps and calls tools. Every call passes the gateway, and nothing is written until you approve its preview.
                  </p>
                </div>
                <ul className="m-0 flex list-none flex-col gap-2 p-0">
                  {SUGGESTIONS.map((s) => (
                    <li key={s}>
                      <button
                        type="button"
                        onClick={() => {
                          setDraft(s);
                          inputRef.current?.focus();
                        }}
                        className="w-full rounded-sm border border-line bg-surface-1 px-3 py-2 text-left text-sm hover:border-line-strong hover:bg-surface-2"
                      >
                        {s}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <ol role="log" aria-live="polite" aria-label="Conversation" className="m-0 flex list-none flex-col gap-5 p-0">
                <li className="flex items-center gap-3 font-mono text-xs text-muted">
                  <span aria-hidden className="h-px flex-1 bg-line" />
                  {state.conv?.id} · as {state.conv?.role} · {state.conv?.config}
                  <span aria-hidden className="h-px flex-1 bg-line" />
                </li>
                {state.messages.map((m) => (
                  <ChatMessage
                    key={m.id}
                    message={m}
                    role={state.conv?.role ?? role}
                    live={live.has(m.id)}
                    {...(m.approvalId ? { approvalStatus: state.approvals[m.approvalId]?.status ?? 'pending' } : {})}
                    onReview={review}
                  />
                ))}
                {state.running ? (
                  <li className="flex items-center gap-2 text-sm text-muted" aria-label="Agent is working">
                    <span className="eg-working" aria-hidden>
                      <span />
                      <span />
                      <span />
                    </span>
                    Working through the gateway…
                  </li>
                ) : null}
              </ol>
            )}
            <div ref={chatEnd} />
          </div>

          <form onSubmit={onSubmit} className="shrink-0 border-t border-line p-4">
            <label htmlFor="composer" className="sr-only">
              Message to the assistant
            </label>
            <div className="rounded-sm border border-control bg-surface-1 focus-within:border-focus">
              <textarea
                id="composer"
                ref={inputRef}
                rows={2}
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={onKeyDown}
                placeholder="Ask to duplicate an edition or archive old events…"
                className="block max-h-40 min-h-12 w-full resize-none bg-transparent px-3 pt-2.5 text-[0.9rem] leading-relaxed text-text placeholder:text-muted focus:outline-none"
                aria-describedby="composer-hint"
              />
              <div className="flex items-center gap-3 px-3 pb-2">
                <p id="composer-hint" className="m-0 text-xs text-muted">
                  Enter to send · Shift+Enter for a new line
                </p>
                <Button type="submit" size="sm" variant="primary" className="ml-auto" disabled={!draft.trim() || state.running || loading} icon={<ArrowUp aria-hidden className="size-3.5" />}>
                  Send
                </Button>
              </div>
            </div>
          </form>
        </section>

        {/* Agent activity: the calling script */}
        <section
          {...(wide ? { 'aria-labelledby': 'activity-title' } : tabPanelProps(paneId, 'activity'))}
          tabIndex={-1}
          className={cn('min-h-0 flex-col min-[72rem]:flex', pane === 'activity' ? 'flex' : 'hidden')}
        >
          <div className="flex min-h-11 shrink-0 flex-wrap items-center gap-x-4 gap-y-1 border-b border-line px-6 py-2">
            <h2 id="activity-title" className="m-0 text-sm font-semibold">
              Agent activity
            </h2>
            {runConfig ? (
              <span className="text-xs text-muted">
                run on <span className="font-mono text-text">{runConfig}</span> as <span className="text-text">{state.conv?.role ?? role}</span>
              </span>
            ) : null}
            <ul aria-label="Decisions so far" className="m-0 ml-auto flex list-none items-center gap-4 p-0">
              <li>
                <StatusChip spec={DECISION.allowed} variant="plain" size="sm" label={`Allowed ${tally.allowed}`} />
              </li>
              <li>
                <StatusChip spec={DECISION.needs_approval} variant="plain" size="sm" label={`Needs approval ${tally.waiting}`} />
              </li>
              <li>
                <StatusChip spec={DECISION.blocked} variant="plain" size="sm" label={`Blocked ${tally.blocked}`} />
              </li>
              {tally.leaked ? (
                <li>
                  <StatusChip spec={{ tone: 'stop', label: 'Leaked', icon: ShieldAlert }} variant="plain" size="sm" label={`Leaked ${tally.leaked}`} />
                </li>
              ) : null}
            </ul>
          </div>
          <div ref={activityRef} className="relative min-h-0 flex-1 overflow-auto">
            {state.calls.length === 0 ? (
              <EmptyState icon={Radar} title="No tool calls yet">
                When the agent calls a tool, the call appears here as a numbered step with the gateway’s decision: allowed, waiting for your approval, or blocked with the rule that stopped it.
              </EmptyState>
            ) : (
              <>
                <CueSheet calls={state.calls} approvals={state.approvals} role={role} live={live} onDecide={decide} />
                {!state.running ? <RunSummary tally={tally} total={state.calls.length} config={state.conv?.config} /> : null}
              </>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

function reduce(s: ConvState, e: AgentEvent): ConvState {
  switch (e.type) {
    case 'message':
      return s.messages.some((m) => m.id === e.message.id) ? s : { ...s, messages: [...s.messages, e.message] };
    case 'tool_call':
    case 'tool_update': {
      const i = s.calls.findIndex((c) => c.id === e.call.id);
      const calls = i === -1 ? [...s.calls, e.call] : s.calls.map((c, j) => (j === i ? e.call : c));
      return { ...s, calls };
    }
    case 'approval':
      return { ...s, approvals: { ...s.approvals, [e.approval.id]: e.approval } };
    case 'done':
      return s;
  }
}

/** The run's closing line: what happened, in one sentence, for staff and jury alike. */
function RunSummary({ tally, total, config }: { tally: { allowed: number; waiting: number; blocked: number; leaked: number }; total: number; config: string | undefined }) {
  const parts = [
    `${total} ${total === 1 ? 'step' : 'steps'} on ${config ?? 'this configuration'}`,
    tally.blocked ? `${tally.blocked} blocked at the gateway` : null,
    tally.leaked ? `${tally.leaked} leaked data` : null,
    tally.waiting ? `${tally.waiting} ${tally.waiting === 1 ? 'approval' : 'approvals'} waiting for you` : null,
    !tally.blocked && !tally.leaked && !tally.waiting ? 'nothing blocked, nothing waiting' : null,
  ].filter(Boolean);
  const tone = tally.leaked ? 'text-stop' : tally.blocked ? 'text-ok' : 'text-muted';
  return (
    <p className={cn('eg-msg-in m-0 border-t border-line px-6 py-4 text-sm', tone)}>
      <span className="font-semibold">Run summary: </span>
      <span className="text-text">{parts.join(' · ')}.</span>
    </p>
  );
}
