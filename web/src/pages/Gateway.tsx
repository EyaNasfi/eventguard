import { ComingLater } from '../components/shell/ComingLater';

export default function GatewayPage() {
  return (
    <ComingLater
      title="Gateway"
      purpose="One switch per protection layer, with what each one blocks, and the C0–C4 presets that set them."
      resumes="Sprint 5"
      needs={['The gateway merged to main and exposing its active configuration (GET /gateway/config).', 'The protection layers C1–C4 implemented, so a switch changes real behaviour.']}
    />
  );
}
