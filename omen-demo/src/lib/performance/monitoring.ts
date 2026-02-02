import { useEffect } from 'react';

/**
 * Web Vitals performance monitoring (LCP, FID, CLS).
 * Call once at app root (e.g. in main.tsx or AppShell).
 */
export function usePerformanceMonitoring(): void {
  useEffect(() => {
    if (typeof window === 'undefined' || !('PerformanceObserver' in window)) return;

    // Largest Contentful Paint (LCP) — target < 2.5s
    const lcpObserver = new PerformanceObserver((list) => {
      const entries = list.getEntries();
      const lastEntry = entries[entries.length - 1];
      if (lastEntry) {
        const lcp = lastEntry.startTime;
        if (process.env.NODE_ENV === 'development') {
          console.log('[Perf] LCP:', lcp.toFixed(2), 'ms');
        }
        // Send to analytics: reportWebVitals?.( { name: 'LCP', value: lcp } )
      }
    });
    try {
      lcpObserver.observe({ entryTypes: ['largest-contentful-paint'] });
    } catch {
      // Some browsers don't support LCP
    }

    // First Input Delay (FID) — target < 100ms
    const fidObserver = new PerformanceObserver((list) => {
      const entries = list.getEntries();
      entries.forEach((entry: PerformanceEntry & { processingStart?: number }) => {
        const delay = entry.processingStart != null ? entry.processingStart - entry.startTime : 0;
        if (process.env.NODE_ENV === 'development') {
          console.log('[Perf] FID:', delay.toFixed(2), 'ms');
        }
      });
    });
    try {
      fidObserver.observe({ entryTypes: ['first-input'] });
    } catch {
      // first-input may not be available
    }

    // Cumulative Layout Shift (CLS) — target < 0.1
    let clsScore = 0;
    const clsObserver = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        const e = entry as PerformanceEntry & { hadRecentInput?: boolean; value?: number };
        if (!e.hadRecentInput && typeof e.value === 'number') {
          clsScore += e.value;
        }
      }
      if (process.env.NODE_ENV === 'development') {
        console.log('[Perf] CLS:', clsScore.toFixed(4));
      }
    });
    try {
      clsObserver.observe({ entryTypes: ['layout-shift'] });
    } catch {
      // layout-shift may not be available
    }

    return () => {
      lcpObserver.disconnect();
      fidObserver.disconnect();
      clsObserver.disconnect();
    };
  }, []);
}
