import { Compass } from 'lucide-react';
import { Link } from 'react-router';
import { EmptyState } from '../components/ui/Feedback';

export default function NotFoundPage() {
  return (
    <EmptyState icon={Compass} title="This page does not exist" className="p-10">
      Check the address, or go back to the{' '}
      <Link to="/assistant" className="text-text underline">
        Assistant
      </Link>
      .
    </EmptyState>
  );
}
