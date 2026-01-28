/**
 * Tracks actual data source (live vs demo) for honest UI labeling.
 * Fixes ISSUE-008: never show mock data with "LIVE" badge.
 */

import { useMemo } from 'react';
import type { ProcessedSignal } from '../types/omen';
import { mockSignals } from '../data/mockSignals';

export type DataSourceType = 'live' | 'demo' | 'cached' | 'error';

export interface DataSourceInfo {
  type: DataSourceType;
  source: string;
  timestamp: string | null;
  signalCount: number;
  isStale: boolean;
  message: string;
}

export interface DataWithSource<T> {
  data: T;
  source: DataSourceInfo;
}

const STALE_MS = 5 * 60 * 1000; // 5 minutes

/**
 * Determines the actual data source and provides honest labeling.
 * Use lastFetchTime from useQuery's dataUpdatedAt: lastFetchTime = dataUpdatedAt ? new Date(dataUpdatedAt) : null.
 */
export function useDataSource(
  liveSignals: ProcessedSignal[] | undefined,
  isLoading: boolean,
  error: Error | null,
  lastFetchTime: Date | null
): DataWithSource<ProcessedSignal[]> {
  return useMemo(() => {
    // Case 1: Loading
    if (isLoading && !liveSignals) {
      return {
        data: [],
        source: {
          type: 'live',
          source: 'Loading from Polymarket...',
          timestamp: null,
          signalCount: 0,
          isStale: false,
          message: 'Đang tải dữ liệu...',
        },
      };
    }

    // Case 2: Error — use mock as fallback, label as demo
    if (error) {
      return {
        data: mockSignals,
        source: {
          type: 'demo',
          source: 'Demo data (API error)',
          timestamp: null,
          signalCount: mockSignals.length,
          isStale: false,
          message: `Lỗi API: ${error.message}. Đang hiển thị dữ liệu demo.`,
        },
      };
    }

    // Case 3: Live data available
    if (liveSignals && liveSignals.length > 0) {
      const isStale = lastFetchTime
        ? Date.now() - lastFetchTime.getTime() > STALE_MS
        : false;
      return {
        data: liveSignals,
        source: {
          type: 'live',
          source: 'Polymarket via OMEN',
          timestamp: lastFetchTime?.toISOString() ?? null,
          signalCount: liveSignals.length,
          isStale,
          message: isStale
            ? 'Dữ liệu có thể đã cũ. Nhấn làm mới.'
            : `${liveSignals.length} tín hiệu từ Polymarket`,
        },
      };
    }

    // Case 4: API returned empty — do NOT substitute mock; show empty
    if (liveSignals && liveSignals.length === 0) {
      return {
        data: [],
        source: {
          type: 'live',
          source: 'Polymarket via OMEN',
          timestamp: lastFetchTime?.toISOString() ?? null,
          signalCount: 0,
          isStale: false,
          message: 'Không có tín hiệu logistics nào được tìm thấy.',
        },
      };
    }

    // Case 5: No data yet — show demo explicitly
    return {
      data: mockSignals,
      source: {
        type: 'demo',
        source: 'Demo data',
        timestamp: null,
        signalCount: mockSignals.length,
        isStale: false,
        message:
          'Đang hiển thị dữ liệu demo. Nhấn "Chạy OMEN" hoặc bật live để tải dữ liệu thực.',
      },
    };
  }, [liveSignals, isLoading, error, lastFetchTime]);
}
