/**
 * Tests for OMEN TypeScript SDK
 *
 * @vitest-environment node
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { OmenClient, OmenClientOptions } from '../src/client';
import {
  PartnerSignalResponse,
  PartnerSignalsListResponse,
  OmenSignal,
  PaginatedResponse,
} from '../src/types';

// Mock fetch globally
const mockFetch = vi.fn();

describe('OmenClient', () => {
  let client: OmenClient;

  beforeEach(() => {
    mockFetch.mockClear();
    client = new OmenClient({
      apiKey: 'test_api_key',
      baseUrl: 'http://localhost:8002',
      fetch: mockFetch as unknown as typeof fetch,
    });
  });

  describe('initialization', () => {
    it('should initialize with api key', () => {
      const testClient = new OmenClient({
        apiKey: 'test_key',
        fetch: mockFetch as unknown as typeof fetch,
      });
      expect(testClient).toBeDefined();
    });

    it('should use default base URL when not provided', () => {
      const defaultClient = new OmenClient({
        apiKey: 'test_key',
        fetch: mockFetch as unknown as typeof fetch,
      });
      expect(defaultClient).toBeDefined();
    });

    it('should throw error without api key', () => {
      expect(() => new OmenClient({ apiKey: '' })).toThrow('API key is required');
    });
  });

  describe('partnerSignals.list', () => {
    const mockPartnerResponse: PartnerSignalsListResponse = {
      timestamp: '2026-02-01T10:00:00Z',
      total_partners: 2,
      partners: [
        {
          symbol: 'GMD',
          company_name: 'Gemadept Corporation',
          sector: 'logistics',
          exchange: 'HOSE',
          signals: {
            price_current: 68.5,
            price_change_percent: 0.88,
            volume: 1901300,
            volatility_20d: 0.023,
          },
          confidence: {
            overall_confidence: 0.85,
            data_completeness: 0.9,
            data_freshness_seconds: 120,
            price_data_confidence: 1.0,
            fundamental_data_confidence: 0.0,
            volume_data_confidence: 1.0,
            missing_fields: [],
            data_source: 'vnstock',
            data_source_reliability: 0.95,
          },
          evidence: [],
          signal_id: 'gmd-001',
          timestamp: '2026-02-01T10:00:00Z',
          suggestion_disclaimer: 'This is OMEN signal only.',
          omen_version: '2.0.0',
          schema_version: '2.0.0',
        },
        {
          symbol: 'HAH',
          company_name: 'Hai An Transport',
          sector: 'logistics',
          exchange: 'HOSE',
          signals: {
            price_current: 34.2,
            price_change_percent: 0.59,
            volume: 500000,
            volatility_20d: 0.018,
          },
          confidence: {
            overall_confidence: 0.82,
            data_completeness: 0.85,
            data_freshness_seconds: 180,
            price_data_confidence: 1.0,
            fundamental_data_confidence: 0.0,
            volume_data_confidence: 1.0,
            missing_fields: ['market_cap'],
            data_source: 'vnstock',
            data_source_reliability: 0.95,
          },
          evidence: [],
          signal_id: 'hah-001',
          timestamp: '2026-02-01T10:00:00Z',
          suggestion_disclaimer: 'This is OMEN signal only.',
          omen_version: '2.0.0',
          schema_version: '2.0.0',
        },
      ],
      market_context: {},
      aggregated_metrics: {},
      data_quality: {},
    };

    it('should fetch all partner signals', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockPartnerResponse,
      });

      const result = await client.partnerSignals.list();

      expect(result.partners).toHaveLength(2);
      expect(result.partners[0].symbol).toBe('GMD');
      expect(result.partners[1].symbol).toBe('HAH');
    });

    it('should filter by symbols', async () => {
      const filteredResponse = {
        ...mockPartnerResponse,
        partners: [mockPartnerResponse.partners[0]],
        total_partners: 1,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => filteredResponse,
      });

      const result = await client.partnerSignals.list({ symbols: ['GMD'] });

      expect(result.partners).toHaveLength(1);
      expect(result.partners[0].symbol).toBe('GMD');
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('symbols=GMD'),
        expect.any(Object)
      );
    });

    it('should include signal metrics', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockPartnerResponse,
      });

      const result = await client.partnerSignals.list();

      expect(result.partners[0].signals.price_current).toBe(68.5);
      expect(result.partners[0].signals.price_change_percent).toBe(0.88);
      expect(result.partners[0].signals.volatility_20d).toBe(0.023);
    });

    it('should include confidence metrics', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockPartnerResponse,
      });

      const result = await client.partnerSignals.list();

      expect(result.partners[0].confidence.overall_confidence).toBe(0.85);
      expect(result.partners[0].confidence.data_completeness).toBe(0.9);
    });
  });

  describe('partnerSignals.get', () => {
    const mockSingleResponse: PartnerSignalResponse = {
      symbol: 'GMD',
      company_name: 'Gemadept Corporation',
      sector: 'logistics',
      exchange: 'HOSE',
      signals: {
        price_current: 68.5,
        price_change_percent: 0.88,
      },
      confidence: {
        overall_confidence: 0.85,
        data_completeness: 0.9,
        data_freshness_seconds: 120,
        price_data_confidence: 1.0,
        fundamental_data_confidence: 0.0,
        volume_data_confidence: 1.0,
        missing_fields: [],
        data_source: 'vnstock',
        data_source_reliability: 0.95,
      },
      evidence: [],
      signal_id: 'gmd-001',
      timestamp: '2026-02-01T10:00:00Z',
      suggestion_disclaimer: 'This is OMEN signal only.',
      omen_version: '2.0.0',
      schema_version: '2.0.0',
    };

    it('should fetch single partner signal', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockSingleResponse,
      });

      const result = await client.partnerSignals.get('GMD');

      expect(result.symbol).toBe('GMD');
      expect(result.signals.price_current).toBe(68.5);
    });

    it('should include path parameter', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockSingleResponse,
      });

      await client.partnerSignals.get('GMD');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/partner-signals/GMD'),
        expect.any(Object)
      );
    });
  });

  describe('signals.list', () => {
    const mockSignalsResponse: PaginatedResponse<OmenSignal> = {
      items: [
        {
          signal_id: 'sig-001',
          signal_type: 'stock',
          title: 'GMD price increased',
          confidence_score: 0.85,
          created_at: '2026-02-01T10:00:00Z',
          tags: [],
          evidence: [],
        },
        {
          signal_id: 'sig-002',
          signal_type: 'stock',
          title: 'HAH volume spike',
          confidence_score: 0.78,
          created_at: '2026-02-01T09:30:00Z',
          tags: [],
          evidence: [],
        },
      ],
      has_more: false,
      page_size: 50,
    };

    it('should fetch signals list', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockSignalsResponse,
      });

      const result = await client.signals.list();

      expect(result.items).toHaveLength(2);
      expect(result.items[0].signal_id).toBe('sig-001');
    });

    it('should support pagination parameters', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockSignalsResponse,
      });

      await client.signals.list({ limit: 10, cursor: 'abc123' });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('limit=10'),
        expect.any(Object)
      );
    });
  });

  describe('health', () => {
    it('should check API health', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          status: 'healthy',
          service: 'omen',
          timestamp: '2026-02-01T10:00:00Z',
        }),
      });

      const result = await client.health();

      expect(result.status).toBe('healthy');
    });
  });

  describe('error handling', () => {
    it('should throw on authentication error (401)', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({
          error: 'UNAUTHORIZED',
          message: 'Invalid API key',
        }),
      });

      await expect(client.partnerSignals.list()).rejects.toThrow();
    });

    it('should throw on rate limit error (429)', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 429,
        headers: new Map([['Retry-After', '60']]),
        json: async () => ({
          error: 'RATE_LIMITED',
          message: 'Rate limit exceeded',
        }),
      });

      await expect(client.partnerSignals.list()).rejects.toThrow();
    });

    it('should throw on not found error (404)', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: async () => ({
          error: 'NOT_FOUND',
          message: 'Partner not found',
        }),
      });

      await expect(client.partnerSignals.get('INVALID')).rejects.toThrow();
    });

    it('should handle network errors', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      await expect(client.partnerSignals.list()).rejects.toThrow('Network error');
    });
  });

  describe('request headers', () => {
    it('should include API key header', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ partners: [], total_partners: 0, timestamp: '' }),
      });

      await client.partnerSignals.list();

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            'X-API-Key': 'test_api_key',
          }),
        })
      );
    });

    it('should include content type header', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ partners: [], total_partners: 0, timestamp: '' }),
      });

      await client.partnerSignals.list();

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            Accept: 'application/json',
          }),
        })
      );
    });
  });
});

describe('OmenClient types', () => {
  it('should have correct PartnerSignal type structure', () => {
    // Type checking test - if this compiles, types are correct
    const signal: PartnerSignalResponse = {
      symbol: 'GMD',
      company_name: 'Test',
      sector: 'logistics',
      exchange: 'HOSE',
      signals: {
        price_current: 100,
        price_change_percent: 1.5,
      },
      confidence: {
        overall_confidence: 0.9,
        data_completeness: 0.95,
        data_freshness_seconds: 60,
        price_data_confidence: 1.0,
        fundamental_data_confidence: 0.0,
        volume_data_confidence: 1.0,
        missing_fields: [],
        data_source: 'vnstock',
        data_source_reliability: 0.95,
      },
      evidence: [],
      signal_id: 'test-001',
      timestamp: '2026-02-01T10:00:00Z',
      suggestion_disclaimer: 'This is OMEN signal only.',
      omen_version: '2.0.0',
      schema_version: '2.0.0',
    };

    expect(signal.symbol).toBe('GMD');
  });
});
