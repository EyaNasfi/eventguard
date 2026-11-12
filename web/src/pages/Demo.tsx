import { ComingLater } from '../components/shell/ComingLater';

export default function DemoPage() {
  return (
    <main id="main" className="min-h-dvh bg-bg pt-6">
      <ComingLater
        title="How EventGuard works"
        purpose="The public page for the jury: the problem, how the gateway works, the headline result, and a button that launches the guided demo."
        resumes="Sprint 8 (with motion and polish)"
        needs={['Measured results for the headline (no sample numbers on a public page).', 'The final demo script agreed with the project lead.']}
      />
    </main>
  );
}
