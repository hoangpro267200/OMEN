import { Badge } from '../common/Badge';

interface BadgeRowProps {
  confidenceLevel: string;
  severityLabel: string;
  isActionable: boolean;
  urgency: string;
}

export function BadgeRow({
  confidenceLevel,
  severityLabel,
  isActionable,
  urgency,
}: BadgeRowProps) {
  return (
    <div className="flex flex-wrap gap-2">
      <Badge
        variant={
          confidenceLevel === 'HIGH'
            ? 'success'
            : confidenceLevel === 'MEDIUM'
              ? 'warning'
              : 'default'
        }
      >
        Confidence: {confidenceLevel}
      </Badge>
      <Badge
        variant={
          severityLabel === 'CRITICAL' || severityLabel === 'High'
            ? 'danger'
            : severityLabel === 'MEDIUM' || severityLabel === 'Medium'
              ? 'warning'
              : 'info'
        }
      >
        Severity: {severityLabel}
      </Badge>
      {isActionable && (
        <Badge variant="success">Actionable</Badge>
      )}
      <Badge variant="info">Urgency: {urgency}</Badge>
    </div>
  );
}
