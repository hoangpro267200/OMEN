import type { ProcessedSignal } from '../../types/omen';
import { SignalFeed } from '../dashboard/SignalFeed';

interface SidebarProps {
  signals: ProcessedSignal[];
  selectedSignalId: string | null;
  onSelectSignal: (id: string) => void;
  className?: string;
  /** Tổng số tín hiệu thực (stats.signals_generated). Dùng để caption "Nguồn cấp tín hiệu" nhảy theo số đã lọc. */
  totalSignalsCount?: number;
}

const baseClass = 'shrink-0 min-h-0 overflow-hidden flex flex-col';

export function Sidebar({
  signals,
  selectedSignalId,
  onSelectSignal,
  className,
  totalSignalsCount,
}: SidebarProps) {
  return (
    <aside
      className={className ? `${baseClass} ${className}` : baseClass}
      style={{ width: 320 }}
    >
      <SignalFeed
        signals={signals}
        selectedId={selectedSignalId}
        onSelect={onSelectSignal}
        className="flex-1 min-h-0"
        totalSignalsCount={totalSignalsCount}
      />
    </aside>
  );
}
