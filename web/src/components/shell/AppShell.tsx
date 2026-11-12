import {
  CalendarDays,
  ChartColumnBig,
  ClipboardCheck,
  ExternalLink,
  FlaskConical,
  MessagesSquare,
  ScrollText,
  ShieldHalf,
  Shapes,
  ShieldCheck,
  type LucideIcon,
} from 'lucide-react';
import type { ReactNode } from 'react';
import { NavLink, useLocation } from 'react-router';
import { USE_MOCKS } from '../../api';
import { ROLES, type Role } from '../../api/types';
import { cn } from '../../lib/cn';
import { useApp } from '../../state/AppState';
import { ConfigBadge } from './ConfigBadge';
import { DemoGuide } from './DemoGuide';

interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  /** Paused by PL decision #3; listed under Infrastructure with a "Soon" mark. */
  later?: boolean;
}

const NAV: NavItem[] = [
  { to: '/assistant', label: 'Assistant', icon: MessagesSquare },
  { to: '/approvals', label: 'Approvals', icon: ClipboardCheck },
  { to: '/audit', label: 'Audit log', icon: ScrollText },
  { to: '/events', label: 'Events', icon: CalendarDays },
  { to: '/gateway', label: 'Gateway', icon: ShieldHalf, later: true },
  { to: '/attacks', label: 'Attack lab', icon: FlaskConical, later: true },
  { to: '/results', label: 'Results', icon: ChartColumnBig, later: true },
];

const TITLES: Record<string, string> = {
  assistant: 'Assistant',
  approvals: 'Approvals',
  audit: 'Audit log',
  events: 'Events',
  gateway: 'Gateway',
  attacks: 'Attack lab',
  results: 'Results',
  dev: 'Component gallery',
};

const ROLE_HINT: Record<Role, string> = {
  reader: 'reads everything except attendees and internal notes',
  editor: 'writes in draft editions, archives events one at a time',
  admin: 'everything, including attendees and the outbox',
};

/** Pages whose data is sample data in the current mode (Events is live when mocks are off). */
function isSample(section: string): boolean {
  return USE_MOCKS || section === 'assistant' || section === 'approvals' || section === 'audit';
}

function NavRow({ item, pendingApprovals }: { item: NavItem; pendingApprovals: number }) {
  return (
    <NavLink
      to={item.to}
      title={item.label}
      className={({ isActive }) =>
        cn(
          'group relative flex h-9 items-center gap-2.5 rounded-lg border px-3 text-sm transition-colors duration-[var(--dur-fast)]',
          isActive ? 'border-brand-line bg-brand-bg font-medium text-brand' : 'border-transparent text-muted hover:bg-surface-1 hover:text-text',
        )
      }
    >
      {({ isActive }) => (
        <>
          <item.icon aria-hidden className="size-4 shrink-0" strokeWidth={2} />
          <span className="sr-only xl:not-sr-only">{item.label}</span>
          {item.later ? (
            <span className="sr-only xl:not-sr-only xl:ml-auto xl:rounded xl:border xl:border-line xl:bg-surface-2 xl:px-1.5 xl:py-0.5 xl:text-[0.625rem] xl:font-medium xl:text-muted">
              <span className="xl:hidden">, </span>Soon
            </span>
          ) : null}
          {item.to === '/approvals' && pendingApprovals > 0 ? (
            <>
              {/* Icon rail: a dot that clears the icon; wide rail: the count. */}
              <span aria-hidden className="absolute top-1.5 right-1.5 size-2 rounded-full bg-hold ring-2 ring-rail xl:hidden" />
              <span className="sr-only xl:not-sr-only xl:ml-auto xl:rounded-full xl:border xl:border-hold-line xl:bg-hold-bg xl:px-1.5 xl:py-0.5 xl:font-mono xl:text-[0.6875rem] xl:font-medium xl:text-hold">
                {pendingApprovals}
                <span className="sr-only"> pending</span>
              </span>
            </>
          ) : isActive && !item.later ? (
            <span aria-hidden className="ml-auto hidden size-1.5 rounded-full bg-brand xl:block" />
          ) : null}
        </>
      )}
    </NavLink>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const { role, setRole, config, pendingApprovals, crumb } = useApp();
  const { pathname } = useLocation();
  const section = pathname.split('/')[1] ?? '';
  const primary = NAV.filter((n) => !n.later);
  const later = NAV.filter((n) => n.later);

  return (
    <div className="grid h-dvh grid-cols-[3.75rem_minmax(0,1fr)] grid-rows-[4rem_minmax(0,1fr)] xl:grid-cols-[16rem_minmax(0,1fr)]">
      <a href="#main" className="sr-only z-50 rounded-lg bg-brand-fill px-3 py-2 text-on-accent focus:not-sr-only focus:fixed focus:top-2 focus:left-2">
        Skip to content
      </a>

      <nav aria-label="Main" className="row-span-2 flex flex-col justify-between border-r border-line bg-rail select-none">
        <div className="flex flex-col">
          <div className="flex h-16 items-center gap-3 border-b border-line px-3.5 xl:px-5">
            <span aria-hidden className="flex size-8 shrink-0 items-center justify-center rounded-lg border border-brand-line bg-brand-bg text-brand">
              <ShieldCheck className="size-4" strokeWidth={2.2} />
            </span>
            <span className="hidden items-center gap-2 xl:flex">
              <span className="text-base font-semibold tracking-tight text-strong">EventGuard</span>
              <span className="rounded border border-line bg-surface-2 px-1.5 py-0.5 font-mono text-[0.625rem] text-muted uppercase">Ops</span>
            </span>
          </div>
          <ul className="m-0 flex list-none flex-col gap-1 p-2 xl:p-3">
            {primary.map((item) => (
              <li key={item.to}>
                <NavRow item={item} pendingApprovals={pendingApprovals} />
              </li>
            ))}
          </ul>
          <p className="m-0 hidden px-6 pt-3 pb-1 text-[0.6875rem] font-semibold tracking-wider text-muted uppercase xl:block">Infrastructure</p>
          <ul className="m-0 flex list-none flex-col gap-1 border-t border-line p-2 xl:border-t-0 xl:p-3 xl:pt-1">
            {later.map((item) => (
              <li key={item.to}>
                <NavRow item={item} pendingApprovals={0} />
              </li>
            ))}
          </ul>
        </div>

        <div className="flex flex-col gap-1 border-t border-line p-2 xl:p-3">
          <NavLink to="/demo" title="Demo page" className="flex h-8 items-center gap-2.5 rounded-lg px-3 text-[0.8125rem] text-muted hover:bg-surface-1 hover:text-text">
            <ExternalLink aria-hidden className="size-4 shrink-0" />
            <span className="sr-only xl:not-sr-only">Demo page</span>
          </NavLink>
          <NavLink to="/dev/components" title="Component gallery" className="flex h-8 items-center gap-2.5 rounded-lg px-3 text-[0.8125rem] text-muted hover:bg-surface-1 hover:text-text">
            <Shapes aria-hidden className="size-4 shrink-0" />
            <span className="sr-only xl:not-sr-only">Components</span>
          </NavLink>
          <p className="m-0 hidden items-center gap-1.5 px-3 pt-2 text-[0.6875rem] text-muted xl:flex">
            <span aria-hidden className={cn('size-2 rounded-full', USE_MOCKS ? 'bg-muted' : 'bg-ok')} />
            {USE_MOCKS ? 'Sample data · all fictional' : 'EventSim live · gateway sample data'}
          </p>
        </div>
      </nav>

      <header className="flex min-w-0 items-center gap-3 border-b border-line bg-bg px-4 lg:px-6">
        <nav aria-label="Breadcrumb" className="min-w-0">
          <ol className="m-0 flex min-w-0 list-none items-center gap-2 p-0">
            <li className={cn('shrink-0 text-xl font-semibold tracking-tight text-strong', crumb && '2xl:text-muted')} aria-current={crumb ? undefined : 'page'}>
              {TITLES[section] ?? 'EventGuard'}
            </li>
            {crumb ? (
              <li className="hidden min-w-0 items-center gap-2 text-sm font-medium text-text 2xl:flex" aria-current="page">
                <span aria-hidden className="text-muted">/</span>
                <span className="truncate">{crumb}</span>
              </li>
            ) : null}
          </ol>
        </nav>
        {isSample(section) ? (
          <>
            <span aria-hidden className="mx-1 hidden h-4 w-px bg-line lg:block" />
            <SampleDataNote />
          </>
        ) : null}
        <div className="ml-auto flex items-center gap-3">
          <DemoGuide />
          <label className="flex h-9 items-center gap-2 rounded-lg border border-line bg-surface-1 pr-1 pl-3 text-[0.8125rem]" title={ROLE_HINT[role]}>
            <span className="text-muted">Acting as</span>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value as Role)}
              className="h-7 rounded-md border border-transparent bg-transparent pr-7 pl-1 font-medium text-strong hover:border-control focus-visible:border-focus"
            >
              {ROLES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </label>
          <ConfigBadge config={config} />
        </div>
      </header>

      <main id="main" tabIndex={-1} className="min-h-0 min-w-0 overflow-auto focus:outline-none">
        {children}
      </main>
    </div>
  );
}

/** Page header: the visible title lives in the top bar; the h1 stays for assistive tech. */
export function PageHeader({ title, children, actions, className }: { title: string; children?: ReactNode; actions?: ReactNode; className?: string }) {
  return (
    <div className={cn('flex flex-wrap items-end gap-x-6 gap-y-3 px-6 pt-5 pb-4', className)}>
      <div className="min-w-0 flex-1">
        <h1 className="sr-only">{title}</h1>
        {children ? <div className="max-w-[72ch] text-sm text-muted">{children}</div> : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </div>
  );
}

/** Says, in the top bar, that the page's data is sample data. */
export function SampleDataNote({ what }: { what?: string } = {}) {
  return (
    <p
      className="m-0 hidden items-center gap-2 rounded-full border border-line bg-surface-1 px-2.5 py-1 text-xs text-muted lg:inline-flex"
      title={what ? `${what} is fictional, generated for the demo.` : 'Fictional data, generated for the demo.'}
    >
      <span aria-hidden className="size-1.5 rounded-full bg-info" />
      Sample data · not measured
    </p>
  );
}
