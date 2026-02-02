import { Button } from '../ui/Button';
import { cn } from '../../lib/utils';

export interface IngestButtonsProps {
  onSend1: () => void;
  onSend5: () => void;
  onSend20: () => void;
  onClear: () => void;
  disabled?: boolean;
  className?: string;
}

/**
 * Send 1 Request, Send 5 Duplicates, Send 20 Duplicates, Clear.
 */
export function IngestButtons({
  onSend1,
  onSend5,
  onSend20,
  onClear,
  disabled = false,
  className = '',
}: IngestButtonsProps) {
  return (
    <div className={cn('flex flex-wrap items-center gap-3', className)}>
      <Button variant="primary" onClick={onSend1} disabled={disabled} data-demo-target="send-one-button">
        Send 1 Request
      </Button>
      <Button variant="secondary" onClick={onSend5} disabled={disabled} data-demo-target="send-duplicates-button">
        Send 5 Duplicates
      </Button>
      <Button variant="secondary" onClick={onSend20} disabled={disabled}>
        Send 20 Duplicates
      </Button>
      <Button variant="ghost" onClick={onClear}>
        Clear
      </Button>
    </div>
  );
}
