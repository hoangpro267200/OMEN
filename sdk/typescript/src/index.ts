/**
 * OMEN TypeScript SDK
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
 * ```
 */

export * from './client';
export * from './types';
export * from './errors';
