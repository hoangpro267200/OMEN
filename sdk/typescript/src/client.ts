/**
 * OMEN TypeScript Client
 *
 * Official TypeScript/JavaScript client for the OMEN Signal Intelligence API.
 *
 * @example
 * ```typescript
 * import { OmenClient } from 'omen-client';
 *
 * const client = new OmenClient({ apiKey: 'your-api-key' });
 *
 * // Get partner signals
 * const signals = await client.partnerSignals.list();
 * for (const partner of signals.partners) {
 *   console.log(`${partner.symbol}: ${partner.signals.price_change_percent}%`);
 * }
 *
 * // Get specific partner
 * const hah = await client.partnerSignals.get('HAH');
 * console.log(`Price: ${hah.signals.price_current}`);
 * ```
 */

import {
  PartnerSignalResponse,
  PartnerSignalsListResponse,
  OmenSignal,
  PaginatedResponse,
  HealthResponse,
} from './types';
import { handleResponseError } from './errors';

/**
 * Client configuration options
 */
export interface OmenClientOptions {
  /**
   * OMEN API key
   */
  apiKey: string;

  /**
   * Base URL for the API (default: https://api.omen.io)
   */
  baseUrl?: string;

  /**
   * Request timeout in milliseconds (default: 30000)
   */
  timeout?: number;

  /**
   * Custom fetch implementation (for Node.js or testing)
   */
  fetch?: typeof fetch;
}

/**
 * Partner signals list options
 */
export interface PartnerSignalsListOptions {
  /**
   * Filter by symbols
   */
  symbols?: string[];

  /**
   * Include signal evidence (default: true)
   */
  includeEvidence?: boolean;

  /**
   * Include market context (default: true)
   */
  includeMarketContext?: boolean;
}

/**
 * Partner signal get options
 */
export interface PartnerSignalGetOptions {
  /**
   * Include signal evidence (default: true)
   */
  includeEvidence?: boolean;

  /**
   * Include historical data
   */
  includeHistory?: boolean;

  /**
   * Days of history (max 90)
   */
  historyDays?: number;
}

/**
 * Signals list options
 */
export interface SignalsListOptions {
  /**
   * Number of signals to return (max 100)
   */
  limit?: number;

  /**
   * Pagination cursor
   */
  cursor?: string;

  /**
   * Filter by signal type
   */
  signalType?: string;
}

/**
 * Partner Signals API client
 */
class PartnerSignalsClient {
  constructor(private client: OmenClient) {}

  /**
   * List partner signals
   *
   * @example
   * ```typescript
   * const signals = await client.partnerSignals.list({ symbols: ['HAH', 'GMD'] });
   * for (const partner of signals.partners) {
   *   console.log(`${partner.symbol}: ${partner.signals.price_change_percent}%`);
   * }
   * ```
   */
  async list(options?: PartnerSignalsListOptions): Promise<PartnerSignalsListResponse> {
    const params = new URLSearchParams();

    if (options?.symbols?.length) {
      params.set('symbols', options.symbols.join(','));
    }
    if (options?.includeEvidence !== undefined) {
      params.set('include_evidence', String(options.includeEvidence));
    }
    if (options?.includeMarketContext !== undefined) {
      params.set('include_market_context', String(options.includeMarketContext));
    }

    return this.client.get<PartnerSignalsListResponse>(
      `/api/v1/partner-signals/?${params.toString()}`
    );
  }

  /**
   * Get signals for a specific partner
   *
   * @example
   * ```typescript
   * const hah = await client.partnerSignals.get('HAH');
   * console.log(`Price: ${hah.signals.price_current}`);
   * console.log(`Confidence: ${hah.confidence.overall_confidence}`);
   * ```
   */
  async get(symbol: string, options?: PartnerSignalGetOptions): Promise<PartnerSignalResponse> {
    const params = new URLSearchParams();

    if (options?.includeEvidence !== undefined) {
      params.set('include_evidence', String(options.includeEvidence));
    }
    if (options?.includeHistory !== undefined) {
      params.set('include_history', String(options.includeHistory));
    }
    if (options?.historyDays !== undefined) {
      params.set('history_days', String(Math.min(options.historyDays, 90)));
    }

    const query = params.toString();
    const path = query ? `/api/v1/partner-signals/${symbol}?${query}` : `/api/v1/partner-signals/${symbol}`;

    return this.client.get<PartnerSignalResponse>(path);
  }
}

/**
 * Signals API client
 */
class SignalsClient {
  constructor(private client: OmenClient) {}

  /**
   * List recent signals
   *
   * @example
   * ```typescript
   * const result = await client.signals.list({ limit: 10 });
   * for (const signal of result.items) {
   *   console.log(`${signal.signal_id}: ${signal.title}`);
   * }
   * ```
   */
  async list(options?: SignalsListOptions): Promise<PaginatedResponse<OmenSignal>> {
    const params = new URLSearchParams();

    if (options?.limit !== undefined) {
      params.set('limit', String(Math.min(options.limit, 100)));
    }
    if (options?.cursor) {
      params.set('cursor', options.cursor);
    }
    if (options?.signalType) {
      params.set('signal_type', options.signalType);
    }

    return this.client.get<PaginatedResponse<OmenSignal>>(
      `/api/v1/signals/?${params.toString()}`
    );
  }

  /**
   * Get a specific signal by ID
   *
   * @example
   * ```typescript
   * const signal = await client.signals.get('OMEN-123');
   * console.log(signal.title);
   * ```
   */
  async get(signalId: string): Promise<OmenSignal> {
    return this.client.get<OmenSignal>(`/api/v1/signals/${signalId}`);
  }
}

/**
 * Official OMEN TypeScript Client
 *
 * @example
 * ```typescript
 * import { OmenClient } from 'omen-client';
 *
 * const client = new OmenClient({ apiKey: 'your-api-key' });
 *
 * // Get partner signals
 * const signals = await client.partnerSignals.list();
 * for (const partner of signals.partners) {
 *   console.log(`${partner.symbol}: ${partner.signals.price_change_percent}%`);
 *   console.log(`  Confidence: ${partner.confidence.overall_confidence}`);
 * }
 *
 * // Get specific partner
 * const hah = await client.partnerSignals.get('HAH');
 * console.log(`HAH Volatility: ${hah.signals.volatility_20d}`);
 * ```
 */
export class OmenClient {
  private apiKey: string;
  private baseUrl: string;
  private timeout: number;
  private fetchFn: typeof fetch;

  /**
   * Partner signals API
   */
  public readonly partnerSignals: PartnerSignalsClient;

  /**
   * Signals API
   */
  public readonly signals: SignalsClient;

  constructor(options: OmenClientOptions) {
    if (!options.apiKey) {
      throw new Error('API key is required');
    }

    this.apiKey = options.apiKey;
    this.baseUrl = options.baseUrl || 'https://api.omen.io';
    this.timeout = options.timeout || 30000;
    this.fetchFn = options.fetch || fetch;

    // Initialize sub-clients
    this.partnerSignals = new PartnerSignalsClient(this);
    this.signals = new SignalsClient(this);
  }

  /**
   * Make a GET request
   * @internal
   */
  async get<T>(path: string): Promise<T> {
    return this.request<T>('GET', path);
  }

  /**
   * Make a POST request
   * @internal
   */
  async post<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>('POST', path, body);
  }

  /**
   * Make an HTTP request
   * @internal
   */
  private async request<T>(method: string, path: string, body?: unknown): Promise<T> {
    const url = `${this.baseUrl}${path}`;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await this.fetchFn(url, {
        method,
        headers: {
          'X-API-Key': this.apiKey,
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          'User-Agent': 'omen-typescript-sdk/2.0.0',
        },
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });

      const data = await response.json();

      if (!response.ok) {
        handleResponseError(response, data);
      }

      return data as T;
    } finally {
      clearTimeout(timeoutId);
    }
  }

  /**
   * Check API health
   *
   * @example
   * ```typescript
   * const health = await client.health();
   * console.log(`Status: ${health.status}`);
   * ```
   */
  async health(): Promise<HealthResponse> {
    return this.get<HealthResponse>('/health');
  }
}

export default OmenClient;
