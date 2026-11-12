import { ComingLater } from '../components/shell/ComingLater';

export default function AttacksPage() {
  return (
    <ComingLater
      title="Attack lab"
      purpose="The attack catalogue in its 8 families, runs against a chosen configuration, and each outcome with the oracle's reason and its audit trace."
      resumes="after the first real attack results"
      needs={['The attack bench and its oracle (forbidden action, canary leak, state diff).', 'An endpoint that lists attacks and streams run status.']}
    />
  );
}
