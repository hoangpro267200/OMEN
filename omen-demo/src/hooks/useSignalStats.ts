import { useMemo } from 'react';
import type { SignalBrowserRecord } from '../data/signalsBrowserMock';

export interface SignalStats {
  total: number;
  byCategory: Record<string, number>;
  byConfidence: Record<string, number>;
  byDeliveryStatus: Record<string, number>;
}

/**
 * Memoized signal statistics. Recomputes only when signals array reference/length changes.
 */
export function useSignalStats(signals: SignalBrowserRecord[]): SignalStats {
  return useMemo(() => {
    const categoryCount = new Map<string, number>();
    const confidenceCount = new Map<string, number>();
    const deliveryCount = new Map<string, number>();

    for (const record of signals) {
      const cat = (record.signal?.category as string) || 'OTHER';
      categoryCount.set(cat, (categoryCount.get(cat) || 0) + 1);

      const conf = (record.signal?.confidence_level as string) || 'MEDIUM';
      confidenceCount.set(conf, (confidenceCount.get(conf) || 0) + 1);

      const status = record.delivery_status ?? 'DELIVERED';
      deliveryCount.set(status, (deliveryCount.get(status) || 0) + 1);
    }

    return {
      total: signals.length,
      byCategory: Object.fromEntries(categoryCount),
      byConfidence: Object.fromEntries(confidenceCount),
      byDeliveryStatus: Object.fromEntries(deliveryCount),
    };
  }, [signals]);
}
