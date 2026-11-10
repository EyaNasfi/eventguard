import { lazy, Suspense, useEffect } from 'react';
import { Navigate, Route, Routes, useLocation } from 'react-router';
import { AppShell } from './components/shell/AppShell';
import { Skeleton } from './components/ui/Feedback';
import { ToastProvider } from './components/ui/Toast';
import { AppStateProvider } from './state/AppState';

const Assistant = lazy(() => import('./pages/Assistant'));
const Approvals = lazy(() => import('./pages/Approvals'));
const Audit = lazy(() => import('./pages/Audit'));
const Events = lazy(() => import('./pages/Events'));
const Gateway = lazy(() => import('./pages/Gateway'));
const Attacks = lazy(() => import('./pages/Attacks'));
const Results = lazy(() => import('./pages/Results'));
const Gallery = lazy(() => import('./pages/Gallery'));
const Demo = lazy(() => import('./pages/Demo'));
const NotFound = lazy(() => import('./pages/NotFound'));

const TITLES: Record<string, string> = {
  assistant: 'Assistant',
  approvals: 'Approvals',
  audit: 'Audit log',
  events: 'Events',
  gateway: 'Gateway',
  attacks: 'Attack lab',
  results: 'Results',
  dev: 'Components',
  demo: 'How EventGuard works',
};

function DocumentTitle() {
  const { pathname } = useLocation();
  useEffect(() => {
    const t = TITLES[pathname.split('/')[1] ?? ''];
    document.title = t ? `${t} · EventGuard` : 'EventGuard';
  }, [pathname]);
  return null;
}

function PageFallback() {
  return (
    <div className="flex flex-col gap-4 p-6" aria-hidden>
      <Skeleton className="h-7 w-56" />
      <Skeleton lines={4} className="max-w-xl" />
    </div>
  );
}

export function App() {
  return (
    <AppStateProvider>
      <ToastProvider>
        <DocumentTitle />
        <Routes>
          <Route
            path="/demo"
            element={
              <Suspense fallback={null}>
                <Demo />
              </Suspense>
            }
          />
          <Route
            path="*"
            element={
              <AppShell>
                <Suspense fallback={<PageFallback />}>
                  <Routes>
                    <Route index element={<Navigate to="/assistant" replace />} />
                    <Route path="assistant" element={<Assistant />} />
                    <Route path="approvals" element={<Approvals />} />
                    <Route path="audit" element={<Audit />} />
                    <Route path="events" element={<Events />} />
                    <Route path="gateway" element={<Gateway />} />
                    <Route path="attacks" element={<Attacks />} />
                    <Route path="results" element={<Results />} />
                    <Route path="dev/components" element={<Gallery />} />
                    <Route path="*" element={<NotFound />} />
                  </Routes>
                </Suspense>
              </AppShell>
            }
          />
        </Routes>
      </ToastProvider>
    </AppStateProvider>
  );
}
