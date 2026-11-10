import { CalendarClock } from 'lucide-react';
import { Link } from 'react-router';
import { buttonClass } from '../ui/Button';
import { PageHeader } from './AppShell';

interface ComingLaterProps {
  title: string;
  /** What the page will do, in one sentence. */
  purpose: string;
  /** When it resumes, per PL decision #3. */
  resumes: string;
  /** What it needs from the backend before it can show real data. */
  needs: string[];
}

/** A page paused by PL decision #3: says what it will be, when, and what it waits for. */
export function ComingLater({ title, purpose, resumes, needs }: ComingLaterProps) {
  return (
    <div className="pb-10">
      <PageHeader title={title}>{purpose}</PageHeader>
      <section aria-labelledby="later-title" className="mx-6 max-w-2xl rounded-sm border border-dashed border-line-strong px-5 py-5">
        <h2 id="later-title" className="m-0 flex items-center gap-2 text-md font-semibold">
          <CalendarClock aria-hidden className="size-4 text-muted" />
          Coming later: {resumes}
        </h2>
        <p className="m-0 mt-2 max-w-[62ch] text-sm text-muted">
          This page is paused on purpose (PL decision #3), so it never shows numbers that were not measured. It waits for:
        </p>
        <ul className="mt-2 mb-0 flex flex-col gap-1 pl-5 text-sm">
          {needs.map((n) => (
            <li key={n}>{n}</li>
          ))}
        </ul>
        <p className="m-0 mt-4 text-sm text-muted">The endpoints it will call are listed in docs/frontend/status.md.</p>
        <Link to="/assistant" className={buttonClass('secondary', 'sm', 'mt-4')}>
          Back to the Assistant
        </Link>
      </section>
    </div>
  );
}
