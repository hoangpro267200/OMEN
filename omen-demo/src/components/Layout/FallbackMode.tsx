import { useNavigate } from 'react-router-dom';
import { AlertTriangle, SkipForward } from 'lucide-react';
import { useDemoModeContext } from '../../context/DemoModeContext';
import { ROUTES } from '../../lib/routes';
import { Button } from '../ui/Button';
import { cn } from '../../lib/utils';

export interface FallbackModeProps {
  /** When true, show fallback banner (e.g. something failed during demo) */
  show?: boolean;
  /** Optional message */
  message?: string;
  /** Skip to Ledger Proof route */
  skipToProofRoute?: string;
  className?: string;
}

/**
 * Fallback mode: show banner with "Skip to proof" and manual override when demo fails.
 */
export function FallbackMode({
  show = false,
  message = 'Something went wrong. Skip to proof or reset demo.',
  skipToProofRoute = ROUTES.ledgerProof,
  className = '',
}: FallbackModeProps) {
  const navigate = useNavigate();
  const { isDemoMode, resetDemo } = useDemoModeContext();

  if (!show || !isDemoMode) return null;

  const handleSkipToProof = () => {
    navigate(skipToProofRoute);
  };

  const handleResetDemo = () => {
    resetDemo();
    navigate('/');
  };

  return (
    <div
      className={cn(
        'fixed left-4 right-4 top-20 z-50 mx-auto max-w-lg rounded-[var(--radius-card)] border border-[var(--accent-amber)]/50 bg-[var(--accent-amber)]/10 p-4 shadow-lg',
        className
      )}
    >
      <div className="flex items-start gap-3">
        <AlertTriangle className="h-5 w-5 shrink-0 text-[var(--accent-amber)]" />
        <div className="flex-1">
          <p className="text-sm font-medium text-[var(--text-primary)]">{message}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            <Button variant="secondary" onClick={handleSkipToProof} className="gap-1 text-xs">
              <SkipForward className="h-3 w-3" />
              Skip to proof
            </Button>
            <Button variant="ghost" onClick={handleResetDemo} className="text-xs">
              Reset demo (Shift+Esc)
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
