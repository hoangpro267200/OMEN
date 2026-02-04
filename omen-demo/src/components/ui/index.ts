/**
 * OMEN Signal Intelligence Engine — UI primitives (Neural Command Center design system)
 */

// Core cards
export { Card } from './Card';
export type { CardProps } from './Card';

export { GlassCard, GlassCardHeader, GlassCardContent, GlassCardTitle } from './GlassCard';
export type { GlassCardProps } from './GlassCard';

// Badges & Status
export { Badge } from './Badge';
export type { BadgeProps, BadgeVariant } from './Badge';

export { StatusDot } from './StatusDot';
export type { StatusDotProps, StatusDotVariant } from './StatusDot';

export { StatusIndicator, StatusBadge } from './StatusIndicator';
export type { StatusIndicatorProps, StatusType } from './StatusIndicator';

// Buttons
export { Button } from './Button';
export type { ButtonProps, ButtonVariant } from './Button';

// Tables
export {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from './Table';
export type { TableProps, TableHeaderProps, TableBodyProps, TableRowProps, TableHeadProps, TableCellProps } from './Table';

// Metrics & Data Display
export { KPICard } from './KPICard';
export type { KPICardProps } from './KPICard';

export { MetricCard, MetricValue } from './MetricCard';
export type { MetricCardProps } from './MetricCard';

// Progress & Gauges
export { ProgressBar, SegmentedProgressBar } from './ProgressBar';
export type { ProgressBarProps } from './ProgressBar';

export { Gauge, MiniGauge, ConfidenceGauge } from './Gauge';
export type { GaugeProps } from './Gauge';

// Code & Text
export { CodeBlock } from './CodeBlock';
export type { CodeBlockProps } from './CodeBlock';

// Animation & Counter
export { AnimatedCounter, SimpleAnimatedCounter } from './AnimatedCounter';

// States & Loading
export { QueryState, ErrorState, QueryEmptyState } from './QueryState';
export { OfflineBanner } from './OfflineBanner';
export { LoadingSpinner } from './LoadingSpinner';
export type { LoadingSpinnerProps } from './LoadingSpinner';

// Utility
export { LanguageSwitcher } from './LanguageSwitcher';
export { OptimizedImage } from './OptimizedImage';
export type { OptimizedImageProps } from './OptimizedImage';

// Data Mode Switcher (New unified mode system)
export {
  DataModeSwitcherCompact,
  DataModeSwitcherFull,
  DataModeTransitionOverlay,
  DataModeStatusBadge,
  ConnectionBanner,
} from './DataModeSwitcher';
export type {
  DataModeSwitcherCompactProps,
  DataModeSwitcherFullProps,
  DataModeStatusBadgeProps,
  ConnectionBannerProps,
} from './DataModeSwitcher';

// Explain Popover (Data traceability system)
export { ExplainPopover } from './ExplainPopover';
export type { ExplainPopoverProps, ExplainContext } from './ExplainPopover';

// Error State
export { ErrorState } from './ErrorState';
export type { ErrorStateProps } from './ErrorState';

// Data State Wrapper (for consistent loading/error/empty handling)
export { DataStateWrapper, DataSourceBadge } from './DataStateWrapper';
export type { DataStateWrapperProps } from './DataStateWrapper';

// Skeleton Loaders
export {
  Skeleton,
  SkeletonText,
  SkeletonCard,
  SkeletonTable,
  SkeletonSignalRow,
  SkeletonStatsGrid,
  SkeletonChart,
  SkeletonSidebar,
  SkeletonPage,
} from './Skeleton';
export type {
  SkeletonProps,
  SkeletonTextProps,
  SkeletonCardProps,
  SkeletonTableProps,
  SkeletonSignalRowProps,
  SkeletonStatsGridProps,
  SkeletonChartProps,
  SkeletonSidebarProps,
  SkeletonPageProps,
} from './Skeleton';
