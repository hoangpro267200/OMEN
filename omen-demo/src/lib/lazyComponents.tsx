/**
 * Lazy Loading Configuration - Code splitting for heavy components
 * 
 * This file sets up React.lazy() for heavy components that should be
 * loaded on-demand to improve initial bundle size and time-to-interactive.
 */

import React, { lazy, Suspense, ComponentType } from 'react';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { SkeletonPage, SkeletonChart, SkeletonTable } from '../components/ui/Skeleton';

// ============================================================================
// LOADING FALLBACKS
// ============================================================================

export function PageLoadingFallback() {
  return <SkeletonPage type="dashboard" />;
}

export function ChartLoadingFallback() {
  return <SkeletonChart type="line" height={300} />;
}

export function TableLoadingFallback() {
  return <SkeletonTable rows={5} columns={4} />;
}

export function SpinnerFallback() {
  return (
    <div className="flex items-center justify-center min-h-[200px]">
      <LoadingSpinner size="lg" />
    </div>
  );
}

// ============================================================================
// LAZY WRAPPER HOC
// ============================================================================

interface LazyWrapperOptions {
  fallback?: React.ReactNode;
  preload?: boolean;
}

/**
 * Creates a lazy-loaded component with a custom fallback
 */
export function createLazyComponent<T extends ComponentType<any>>(
  importFn: () => Promise<{ default: T }>,
  options: LazyWrapperOptions = {}
): React.LazyExoticComponent<T> & { preload: () => Promise<{ default: T }> } {
  const LazyComponent = lazy(importFn) as React.LazyExoticComponent<T> & {
    preload: () => Promise<{ default: T }>;
  };

  // Add preload capability
  LazyComponent.preload = importFn;

  return LazyComponent;
}

/**
 * Wraps a lazy component with Suspense
 */
export function withLazySuspense<P extends object>(
  LazyComponent: React.LazyExoticComponent<ComponentType<P>>,
  fallback: React.ReactNode = <SpinnerFallback />
): React.FC<P> {
  return function LazyWrapper(props: P) {
    return (
      <Suspense fallback={fallback}>
        <LazyComponent {...props} />
      </Suspense>
    );
  };
}

// ============================================================================
// LAZY SCREEN COMPONENTS
// ============================================================================

// Heavy screens that benefit from code splitting
export const LazySignalDeepDive = createLazyComponent(
  () => import('../screens/SignalDeepDive')
);

export const LazyPipelineMonitor = createLazyComponent(
  () => import('../screens/PipelineMonitor')
);

export const LazySourcesObservatory = createLazyComponent(
  () => import('../screens/SourcesObservatory')
);

export const LazyPartitionsScreen = createLazyComponent(
  () => import('../screens/PartitionsScreen')
);

export const LazyLedgerProofScreen = createLazyComponent(
  () => import('../screens/LedgerProofScreen')
);

export const LazyIngestDemoScreen = createLazyComponent(
  () => import('../screens/IngestDemoScreen')
);

// ============================================================================
// LAZY HEAVY COMPONENTS
// ============================================================================

// Components that are heavy due to dependencies (charts, graphs, etc.)
export const LazyLineageGraph = createLazyComponent(
  () => import('../components/lineage/LineageGraph')
);

export const LazyAuditTrail = createLazyComponent(
  () => import('../components/audit/AuditTrail')
);

export const LazyProcessingLogs = createLazyComponent(
  () => import('../components/audit/ProcessingLogs')
);

export const LazySignalTimeline = createLazyComponent(
  () => import('../components/timeline/SignalTimeline')
);

// ============================================================================
// PRELOAD UTILITIES
// ============================================================================

/**
 * Preload a lazy component on hover or focus
 */
export function preloadOnInteraction(
  LazyComponent: { preload: () => Promise<unknown> },
  event: 'hover' | 'focus' | 'both' = 'hover'
) {
  const handlers: Record<string, () => void> = {};

  if (event === 'hover' || event === 'both') {
    handlers.onMouseEnter = () => LazyComponent.preload();
  }

  if (event === 'focus' || event === 'both') {
    handlers.onFocus = () => LazyComponent.preload();
  }

  return handlers;
}

/**
 * Preload components after initial render (during idle time)
 */
export function preloadInIdle(components: Array<{ preload: () => Promise<unknown> }>) {
  if (typeof window !== 'undefined' && 'requestIdleCallback' in window) {
    (window as any).requestIdleCallback(() => {
      components.forEach((component) => component.preload());
    });
  } else {
    // Fallback for browsers without requestIdleCallback
    setTimeout(() => {
      components.forEach((component) => component.preload());
    }, 2000);
  }
}

/**
 * Preload components based on route
 */
export function preloadForRoute(route: string) {
  const preloadMap: Record<string, Array<{ preload: () => Promise<unknown> }>> = {
    '/signals': [LazySignalDeepDive],
    '/pipeline': [LazyPipelineMonitor],
    '/sources': [LazySourcesObservatory],
    '/partitions': [LazyPartitionsScreen],
    '/ledger': [LazyLedgerProofScreen],
  };

  const componentsToPreload = preloadMap[route];
  if (componentsToPreload) {
    componentsToPreload.forEach((component) => component.preload());
  }
}

// ============================================================================
// WRAPPED COMPONENTS (ready to use with Suspense)
// ============================================================================

export const SignalDeepDiveWithSuspense = withLazySuspense(
  LazySignalDeepDive,
  <PageLoadingFallback />
);

export const PipelineMonitorWithSuspense = withLazySuspense(
  LazyPipelineMonitor,
  <PageLoadingFallback />
);

export const LineageGraphWithSuspense = withLazySuspense(
  LazyLineageGraph,
  <ChartLoadingFallback />
);

export const AuditTrailWithSuspense = withLazySuspense(
  LazyAuditTrail,
  <TableLoadingFallback />
);

// ============================================================================
// EXPORTS
// ============================================================================

export default {
  createLazyComponent,
  withLazySuspense,
  preloadOnInteraction,
  preloadInIdle,
  preloadForRoute,
};
