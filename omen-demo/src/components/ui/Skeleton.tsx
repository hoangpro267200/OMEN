/**
 * Skeleton - Loading skeleton components for perceived performance
 * 
 * Features:
 * - Various pre-built skeleton components
 * - Shimmer animation
 * - Customizable dimensions
 * - Composable building blocks
 */

import React from 'react';
import { cn } from '../../lib/utils';

// ============================================================================
// BASE SKELETON
// ============================================================================

export interface SkeletonProps {
  /** Width (CSS value or number for px) */
  width?: string | number;
  /** Height (CSS value or number for px) */
  height?: string | number;
  /** Border radius variant */
  rounded?: 'none' | 'sm' | 'md' | 'lg' | 'full';
  /** Enable shimmer animation */
  animate?: boolean;
  /** Additional class names */
  className?: string;
}

export function Skeleton({
  width,
  height,
  rounded = 'md',
  animate = true,
  className,
}: SkeletonProps) {
  const roundedClasses = {
    none: 'rounded-none',
    sm: 'rounded-sm',
    md: 'rounded-md',
    lg: 'rounded-lg',
    full: 'rounded-full',
  };

  return (
    <div
      className={cn(
        'bg-[var(--bg-tertiary)]',
        roundedClasses[rounded],
        animate && 'animate-pulse',
        className
      )}
      style={{
        width: typeof width === 'number' ? `${width}px` : width,
        height: typeof height === 'number' ? `${height}px` : height,
      }}
    />
  );
}

// ============================================================================
// SKELETON TEXT
// ============================================================================

export interface SkeletonTextProps {
  /** Number of lines */
  lines?: number;
  /** Width of last line (percentage) */
  lastLineWidth?: number;
  /** Line height */
  lineHeight?: string | number;
  /** Gap between lines */
  gap?: number;
  /** Enable animation */
  animate?: boolean;
  /** Additional class names */
  className?: string;
}

export function SkeletonText({
  lines = 3,
  lastLineWidth = 70,
  lineHeight = 16,
  gap = 8,
  animate = true,
  className,
}: SkeletonTextProps) {
  return (
    <div className={cn('space-y-2', className)} style={{ gap: `${gap}px` }}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          width={i === lines - 1 ? `${lastLineWidth}%` : '100%'}
          height={lineHeight}
          animate={animate}
        />
      ))}
    </div>
  );
}

// ============================================================================
// SKELETON CARD
// ============================================================================

export interface SkeletonCardProps {
  /** Show header skeleton */
  showHeader?: boolean;
  /** Show image/media skeleton */
  showImage?: boolean;
  /** Number of content lines */
  contentLines?: number;
  /** Show footer skeleton */
  showFooter?: boolean;
  /** Enable animation */
  animate?: boolean;
  /** Additional class names */
  className?: string;
}

export function SkeletonCard({
  showHeader = true,
  showImage = false,
  contentLines = 3,
  showFooter = true,
  animate = true,
  className,
}: SkeletonCardProps) {
  return (
    <div
      className={cn(
        'p-4 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-secondary)]',
        className
      )}
    >
      {showHeader && (
        <div className="flex items-center gap-3 mb-4">
          <Skeleton width={40} height={40} rounded="full" animate={animate} />
          <div className="flex-1">
            <Skeleton width="60%" height={16} animate={animate} className="mb-2" />
            <Skeleton width="40%" height={12} animate={animate} />
          </div>
        </div>
      )}

      {showImage && (
        <Skeleton width="100%" height={160} rounded="lg" animate={animate} className="mb-4" />
      )}

      <SkeletonText lines={contentLines} animate={animate} className="mb-4" />

      {showFooter && (
        <div className="flex items-center justify-between pt-4 border-t border-[var(--border-subtle)]">
          <Skeleton width={80} height={24} animate={animate} />
          <Skeleton width={100} height={32} rounded="lg" animate={animate} />
        </div>
      )}
    </div>
  );
}

// ============================================================================
// SKELETON TABLE
// ============================================================================

export interface SkeletonTableProps {
  /** Number of rows */
  rows?: number;
  /** Number of columns */
  columns?: number;
  /** Show header row */
  showHeader?: boolean;
  /** Enable animation */
  animate?: boolean;
  /** Additional class names */
  className?: string;
}

export function SkeletonTable({
  rows = 5,
  columns = 4,
  showHeader = true,
  animate = true,
  className,
}: SkeletonTableProps) {
  return (
    <div className={cn('rounded-xl border border-[var(--border-subtle)] overflow-hidden', className)}>
      {showHeader && (
        <div className="flex items-center gap-4 px-4 py-3 bg-[var(--bg-tertiary)]">
          {Array.from({ length: columns }).map((_, i) => (
            <Skeleton
              key={i}
              width={i === 0 ? 120 : 80}
              height={14}
              animate={animate}
              className="flex-shrink-0"
            />
          ))}
        </div>
      )}
      <div className="divide-y divide-[var(--border-subtle)]">
        {Array.from({ length: rows }).map((_, rowIdx) => (
          <div key={rowIdx} className="flex items-center gap-4 px-4 py-3">
            {Array.from({ length: columns }).map((_, colIdx) => (
              <Skeleton
                key={colIdx}
                width={colIdx === 0 ? 140 : colIdx === columns - 1 ? 60 : 80}
                height={16}
                animate={animate}
                className="flex-shrink-0"
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

// ============================================================================
// SKELETON SIGNAL ROW
// ============================================================================

export interface SkeletonSignalRowProps {
  /** Enable animation */
  animate?: boolean;
  /** Additional class names */
  className?: string;
}

export function SkeletonSignalRow({ animate = true, className }: SkeletonSignalRowProps) {
  return (
    <div
      className={cn(
        'flex items-center gap-4 p-4 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-secondary)]',
        className
      )}
    >
      {/* Status indicator */}
      <Skeleton width={8} height={8} rounded="full" animate={animate} />

      {/* ID */}
      <Skeleton width={120} height={16} animate={animate} className="font-mono" />

      {/* Title */}
      <div className="flex-1">
        <Skeleton width="80%" height={16} animate={animate} className="mb-2" />
        <Skeleton width="50%" height={12} animate={animate} />
      </div>

      {/* Metrics */}
      <div className="flex items-center gap-6">
        <Skeleton width={60} height={24} animate={animate} />
        <Skeleton width={50} height={24} animate={animate} />
        <Skeleton width={70} height={24} rounded="full" animate={animate} />
      </div>
    </div>
  );
}

// ============================================================================
// SKELETON STATS GRID
// ============================================================================

export interface SkeletonStatsGridProps {
  /** Number of stat cards */
  count?: number;
  /** Enable animation */
  animate?: boolean;
  /** Additional class names */
  className?: string;
}

export function SkeletonStatsGrid({ count = 4, animate = true, className }: SkeletonStatsGridProps) {
  return (
    <div className={cn('grid grid-cols-2 md:grid-cols-4 gap-4', className)}>
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="p-4 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-secondary)]"
        >
          <div className="flex items-center justify-between mb-3">
            <Skeleton width={100} height={12} animate={animate} />
            <Skeleton width={24} height={24} rounded="md" animate={animate} />
          </div>
          <Skeleton width={80} height={32} animate={animate} className="mb-2" />
          <Skeleton width={60} height={12} animate={animate} />
        </div>
      ))}
    </div>
  );
}

// ============================================================================
// SKELETON CHART
// ============================================================================

export interface SkeletonChartProps {
  /** Chart type */
  type?: 'line' | 'bar' | 'pie';
  /** Height */
  height?: number;
  /** Enable animation */
  animate?: boolean;
  /** Additional class names */
  className?: string;
}

export function SkeletonChart({
  type = 'line',
  height = 200,
  animate = true,
  className,
}: SkeletonChartProps) {
  return (
    <div
      className={cn(
        'p-4 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-secondary)]',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <Skeleton width={120} height={16} animate={animate} />
        <div className="flex items-center gap-2">
          <Skeleton width={60} height={24} rounded="md" animate={animate} />
          <Skeleton width={60} height={24} rounded="md" animate={animate} />
        </div>
      </div>

      {/* Chart Area */}
      <div style={{ height }} className="relative">
        {type === 'line' && (
          <div className="absolute inset-0 flex items-end justify-between gap-1">
            {Array.from({ length: 12 }).map((_, i) => (
              <Skeleton
                key={i}
                width="100%"
                height={`${30 + Math.random() * 60}%`}
                rounded="sm"
                animate={animate}
              />
            ))}
          </div>
        )}
        {type === 'bar' && (
          <div className="absolute inset-0 flex items-end justify-around gap-2">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton
                key={i}
                width={40}
                height={`${40 + Math.random() * 50}%`}
                rounded="sm"
                animate={animate}
              />
            ))}
          </div>
        )}
        {type === 'pie' && (
          <div className="flex items-center justify-center h-full">
            <Skeleton width={height - 40} height={height - 40} rounded="full" animate={animate} />
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="flex items-center justify-center gap-4 mt-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="flex items-center gap-2">
            <Skeleton width={12} height={12} rounded="sm" animate={animate} />
            <Skeleton width={50} height={12} animate={animate} />
          </div>
        ))}
      </div>
    </div>
  );
}

// ============================================================================
// SKELETON SIDEBAR
// ============================================================================

export interface SkeletonSidebarProps {
  /** Number of menu items */
  items?: number;
  /** Enable animation */
  animate?: boolean;
  /** Additional class names */
  className?: string;
}

export function SkeletonSidebar({ items = 6, animate = true, className }: SkeletonSidebarProps) {
  return (
    <div className={cn('p-4 space-y-2', className)}>
      {/* Logo */}
      <div className="flex items-center gap-3 p-2 mb-4">
        <Skeleton width={32} height={32} rounded="lg" animate={animate} />
        <Skeleton width={80} height={20} animate={animate} />
      </div>

      {/* Menu Items */}
      {Array.from({ length: items }).map((_, i) => (
        <div key={i} className="flex items-center gap-3 p-2">
          <Skeleton width={20} height={20} rounded="md" animate={animate} />
          <Skeleton width={`${60 + Math.random() * 30}%`} height={16} animate={animate} />
        </div>
      ))}

      {/* Footer */}
      <div className="pt-4 mt-4 border-t border-[var(--border-subtle)]">
        <div className="flex items-center gap-3 p-2">
          <Skeleton width={32} height={32} rounded="full" animate={animate} />
          <div className="flex-1">
            <Skeleton width="70%" height={14} animate={animate} className="mb-1" />
            <Skeleton width="50%" height={10} animate={animate} />
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// SKELETON PAGE
// ============================================================================

export interface SkeletonPageProps {
  /** Page type */
  type?: 'dashboard' | 'detail' | 'list' | 'form';
  /** Enable animation */
  animate?: boolean;
  /** Additional class names */
  className?: string;
}

export function SkeletonPage({ type = 'dashboard', animate = true, className }: SkeletonPageProps) {
  return (
    <div className={cn('p-6 space-y-6', className)}>
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <Skeleton width={200} height={28} animate={animate} className="mb-2" />
          <Skeleton width={300} height={16} animate={animate} />
        </div>
        <div className="flex items-center gap-3">
          <Skeleton width={100} height={36} rounded="lg" animate={animate} />
          <Skeleton width={100} height={36} rounded="lg" animate={animate} />
        </div>
      </div>

      {type === 'dashboard' && (
        <>
          <SkeletonStatsGrid animate={animate} />
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <SkeletonChart type="line" animate={animate} />
            <SkeletonChart type="bar" animate={animate} />
          </div>
          <SkeletonTable rows={5} animate={animate} />
        </>
      )}

      {type === 'detail' && (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2">
              <SkeletonCard showImage contentLines={5} animate={animate} />
            </div>
            <div className="space-y-4">
              <SkeletonCard showHeader={false} contentLines={4} showFooter={false} animate={animate} />
              <SkeletonCard showHeader={false} contentLines={3} showFooter={false} animate={animate} />
            </div>
          </div>
        </>
      )}

      {type === 'list' && (
        <div className="space-y-3">
          {Array.from({ length: 8 }).map((_, i) => (
            <SkeletonSignalRow key={i} animate={animate} />
          ))}
        </div>
      )}

      {type === 'form' && (
        <div className="max-w-2xl space-y-6">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="space-y-2">
              <Skeleton width={100} height={14} animate={animate} />
              <Skeleton width="100%" height={40} rounded="lg" animate={animate} />
            </div>
          ))}
          <div className="flex items-center justify-end gap-3 pt-4">
            <Skeleton width={80} height={40} rounded="lg" animate={animate} />
            <Skeleton width={100} height={40} rounded="lg" animate={animate} />
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// EXPORTS
// ============================================================================

export default Skeleton;
