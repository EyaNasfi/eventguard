import {
  CalendarDays,
  ChartColumnBig,
  ClipboardCheck,
  FlaskConical,
  MessagesSquare,
  Presentation,
  ScrollText,
  ShieldHalf,
  Shapes,
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
  /** Paused by PL decision #3; shown with a "coming later" mark. */
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

export function AppShell({ children }: { children: ReactNode }) {
  const { role, setRole, config, pendingApprovals, crumb } = useApp();
  const { pathname } = useLocation();
  const section = pathname.split('/')[1] ?? '';

  return (
    <div className="grid h-dvh grid-cols-[3.5rem_minmax(0,1fr)] grid-rows-[3.25rem_minmax(0,1fr)] xl:grid-cols-[13.5rem_minmax(0,1fr)]">
      <a href="#main" className="sr-only z-50 rounded-sm bg-text px-3 py-2 text-on-accent focus:not-sr-only focus:fixed focus:top-2 focus:left-2">
        Skip to content
      </a>

      <nav aria-label="Main" className="row-span-2 flex flex-col border-r border-line bg-rail">
        <div className="flex h-13 items-center gap-2.5 px-4 xl:px-5">
          <svg aria-hidden viewBox="0 0 16 16" className="size-4 shrink-0 text-text">
            <rect x="1.5" y="1.5" width="13" height="13" rx="1.5" fill="none" stroke="currentColor" strokeWidth="2" />
            <path d="M5 8h6M8 5v6" stroke="currentColor" strokeWidth="2" />
          </svg>
          <span className="hidden text-md font-bold tracking-[0.005em] xl:inline">EventGuard</span>
        </div>
        <ul className="m-0 flex list-none flex-col gap-px p-0 px-2 pt-2">
          {NAV.map((item) => (
            <li key={item.to}>
              <NavLink
                to={item.to}
                title={item.label}
                className={({ isActive }) =>
                  cn(
                    'group relative flex h-9 items-center gap-3 rounded-sm px-2.5 text-sm font-medium transition-colors duration-[var(--dur-fast)]',
                    isActive ? 'bg-surface-2 text-text' : 'text-muted hover:bg-surface-1 hover:text-text',
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    <span aria-hidden className={cn('absolute top-2 bottom-2 left-0 w-0.5 rounded-full', isActive ? 'bg-info' : 'bg-transparent')} />
                    <item.icon aria-hidden className="size-4 shrink-0" strokeWidth={isActive ? 2.2 : 1.8} />
                    <span className="sr-only xl:not-sr-only">{item.label}</span>
                    {item.later ? (
                      <span className="sr-only xl:not-sr-only xl:ml-auto xl:rounded-xs xl:border xl:border-dashed xl:border-line-strong xl:px-1 xl:text-[0.6875rem] xl:leading-4 xl:font-medium xl:text-muted">
                        <span className="xl:hidden">, </span>coming later
                      </span>
                    ) : null}
                    {item.to === '/approvals' && pendingApprovals > 0 ? (
                      <>
                        {/* Icon rail: a dot that clears the icon; wide rail: the count. */}
                        <span aria-hidden className="absolute top-1.5 right-1.5 size-2 rounded-full bg-hold ring-2 ring-rail xl:hidden" />
                        <span className="sr-only xl:not-sr-only xl:ml-auto xl:rounded-xs xl:border xl:border-hold-line xl:bg-hold-bg xl:px-1 xl:font-mono xl:text-xs xl:leading-4 xl:font-semibold xl:text-hold">
                          {pendingApprovals}
                          <span className="sr-only"> pending</span>
                        </span>
                      </>
                    ) : null}
                  </>
                )}
              </NavLink>
            </li>
          ))}
        </ul>

        <div className="mt-auto flex flex-col gap-px border-t border-line px-2 py-2">
          <NavLink to="/demo" title="Demo page" className="flex h-8 items-center gap-3 rounded-sm px-2.5 text-xs text-muted hover:bg-surface-1 hover:text-text">
            <Presentation aria-hidden className="size-4 shrink-0" strokeWidth={1.8} />
            <span className="sr-only xl:not-sr-only">Demo page</span>
          </NavLink>
          <NavLink to="/dev/components" title="Component gallery" className="flex h-8 items-center gap-3 rounded-sm px-2.5 text-xs text-muted hover:bg-surface-1 hover:text-text">
            <Shapes aria-hidden className="size-4 shrink-0" strokeWidth={1.8} />
            <span className="sr-only xl:not-sr-only">Components</span>
          </NavLink>
          <p className="m-0 hidden px-2.5 pt-2 pb-1 text-xs text-muted xl:block">
            {USE_MOCKS ? 'Sample data · all fictional' : 'EventSim live · gateway sample data'}
          </p>
        </div>
      </nav>

      <header className="flex min-w-0 items-center gap-3 border-b border-line bg-bg px-4 lg:px-5">
        <nav aria-label="Breadcrumb" className="min-w-0">
          <ol className="m-0 flex min-w-0 list-none items-center gap-1.5 p-0 text-sm">
            <li className={cn('shrink-0', crumb ? 'text-muted' : 'font-semibold')} aria-current={crumb ? undefined : 'page'}>
              {TITLES[section] ?? 'EventGuard'}
            </li>
            {crumb ? (
              <li className="flex min-w-0 items-center gap-1.5 font-semibold" aria-current="page">
                <span aria-hidden className="text-muted">/</span>
                <span className="truncate">{crumb}</span>
              </li>
            ) : null}
          </ol>
        </nav>
        <div className="ml-auto flex items-center gap-3">
          <DemoGuide />
          <label className="flex items-center gap-2 text-xs text-muted" title={ROLE_HINT[role]}>
            <span>Acting as</span>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value as Role)}
              className="h-9 rounded-sm border border-control bg-surface-1 pr-7 pl-2 text-sm font-semibold text-text hover:border-muted"
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

/** Standard page header: one h1, a sentence of context, actions on the right. */
export function PageHeader({ title, children, actions, className }: { title: string; children?: ReactNode; actions?: ReactNode; className?: string }) {
  return (
    <div className={cn('flex flex-wrap items-end gap-x-6 gap-y-3 px-6 pt-6 pb-4', className)}>
      <div className="min-w-0 flex-1">
        <h1 className="text-xl font-semibold tracking-[-0.01em]">{title}</h1>
        {children ? <div className="mt-1 max-w-[72ch] text-sm text-muted">{children}</div> : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </div>
  );
}

/** Says where a page's data comes from when it is not live. */
export function SampleDataNote({ what }: { what: string }) {
  return (
    <p className="m-0 inline-flex items-center gap-1.5 rounded-xs border border-dashed border-line-strong px-2 py-0.5 text-xs text-muted">
      <span className="font-semibold text-text">Sample data · not measured.</span> {what} is fictional, generated for the demo.
    </p>
  );
}
