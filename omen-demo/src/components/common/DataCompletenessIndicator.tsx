interface FieldDesc {
  name: string;
  hasData: boolean;
  importance: 'critical' | 'important' | 'optional';
}

interface DataCompletenessIndicatorProps {
  fields: FieldDesc[];
}

export function DataCompletenessIndicator({ fields }: DataCompletenessIndicatorProps) {
  const total = fields.length;
  const filled = fields.filter((f) => f.hasData).length;
  const completeness = total > 0 ? filled / total : 1;
  const criticalMissing = fields.filter(
    (f) => !f.hasData && f.importance === 'critical'
  );

  const color =
    completeness >= 0.8 ? 'text-green-400' : completeness >= 0.5 ? 'text-yellow-400' : 'text-red-400';
  const barColor =
    completeness >= 0.8 ? 'bg-green-500' : completeness >= 0.5 ? 'bg-yellow-500' : 'bg-red-500';

  return (
    <div className="p-3 bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)]">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-[var(--text-muted)]">Độ đầy đủ dữ liệu</span>
        <span className={`text-xs font-medium ${color}`}>
          {Math.round(completeness * 100)}%
        </span>
      </div>
      <div className="h-1.5 bg-[var(--bg-hover)] rounded-full overflow-hidden">
        <div
          className={`h-full transition-all ${barColor}`}
          style={{ width: `${completeness * 100}%` }}
        />
      </div>
      {criticalMissing.length > 0 && (
        <div className="mt-2 text-xs text-red-400">
          ⚠ Thiếu: {criticalMissing.map((f) => f.name).join(', ')}
        </div>
      )}
    </div>
  );
}
