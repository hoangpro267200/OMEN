import { CodeBlock } from '../ui/CodeBlock';
import { cn } from '../../lib/utils';

export interface PayloadPreviewProps {
  json: string;
  className?: string;
}

/**
 * Code block showing the selected payload JSON.
 */
export function PayloadPreview({ json, className = '' }: PayloadPreviewProps) {
  return (
    <div className={cn('rounded-[var(--radius-card)] border border-[var(--border-subtle)] overflow-hidden', className)}>
      <CodeBlock raw={json} language="json" className="max-h-[240px] overflow-y-auto">
        {' '}
      </CodeBlock>
    </div>
  );
}
