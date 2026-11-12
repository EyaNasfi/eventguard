import { ComingLater } from '../components/shell/ComingLater';

export default function ResultsPage() {
  return (
    <ComingLater
      title="Results"
      purpose="C0 to C4 compared on attack success, task success, false refusals and approvals per task, with confidence intervals."
      resumes="after the first real attack results"
      needs={['Measured bench runs for each configuration (no sample numbers are shown here).', 'An endpoint that serves the latest results set with intervals.']}
    />
  );
}
