/**
 * OMEN API - TypeScript Example
 * 
 * This example shows how to:
 * 1. Connect to OMEN API
 * 2. Fetch signals
 * 3. Handle responses with proper typing
 * 
 * Prerequisites:
 *   npm install @omen/sdk
 *   or use fetch with types below
 */

// ═══════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════

interface OmenSignal {
    signal_id: string;
    title: string;
    description: string | null;
    probability: number;
    confidence_score: number;
    confidence_level: 'HIGH' | 'MEDIUM' | 'LOW';
    category: string;
    tags: string[];
    trace_id: string;
    generated_at: string;
    geographic: {
        regions: string[];
        chokepoints: string[];
    };
    temporal: {
        event_horizon: string | null;
        resolution_date: string | null;
    };
}

interface SignalListResponse {
    signals: OmenSignal[];
    total: number;
    processed: number;
    passed: number;
    rejected: number;
    pass_rate: number;
}

interface HealthResponse {
    status: string;
    timestamp: string;
    components: Record<string, unknown>;
}

// ═══════════════════════════════════════════════════════════════════════════
// CLIENT
// ═══════════════════════════════════════════════════════════════════════════

class OmenClient {
    private baseUrl: string;
    private apiKey: string;

    constructor(config: { baseUrl?: string; apiKey: string }) {
        this.baseUrl = (config.baseUrl || 'http://localhost:8000').replace(/\/$/, '');
        this.apiKey = config.apiKey;
    }

    private async request<T>(
        endpoint: string,
        options?: RequestInit
    ): Promise<T> {
        const url = `${this.baseUrl}${endpoint}`;
        const response = await fetch(url, {
            ...options,
            headers: {
                'X-API-Key': this.apiKey,
                'Content-Type': 'application/json',
                ...options?.headers,
            },
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(
                `OMEN API Error: ${response.status} - ${error.message || response.statusText}`
            );
        }

        return response.json();
    }

    async healthCheck(): Promise<HealthResponse> {
        return this.request<HealthResponse>('/health/ready');
    }

    async getSignals(params?: {
        limit?: number;
        category?: string;
        minConfidence?: number;
    }): Promise<OmenSignal[]> {
        const searchParams = new URLSearchParams();
        if (params?.limit) searchParams.set('limit', params.limit.toString());
        if (params?.category) searchParams.set('category', params.category);
        if (params?.minConfidence !== undefined) {
            searchParams.set('min_confidence', params.minConfidence.toString());
        }

        const query = searchParams.toString();
        const endpoint = `/api/v1/signals${query ? `?${query}` : ''}`;
        
        const response = await this.request<SignalListResponse | { data: OmenSignal[] }>(endpoint);
        return 'signals' in response ? response.signals : response.data || [];
    }

    async getSignal(signalId: string): Promise<OmenSignal> {
        return this.request<OmenSignal>(`/api/v1/signals/${signalId}`);
    }

    async getExplanation(signalId: string): Promise<Record<string, unknown>> {
        return this.request<Record<string, unknown>>(`/api/v1/explanations/${signalId}`);
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// EXAMPLES
// ═══════════════════════════════════════════════════════════════════════════

async function basicExample() {
    console.log('=== Basic Usage Example ===\n');

    const client = new OmenClient({
        baseUrl: 'http://localhost:8000',
        apiKey: 'demo-key',
    });

    // Health check
    const health = await client.healthCheck();
    console.log(`API Status: ${health.status}`);

    // Get signals
    const signals = await client.getSignals({ limit: 5 });
    console.log(`\nFound ${signals.length} signals:`);

    signals.forEach((signal) => {
        console.log(
            `  - ${signal.signal_id}: ${signal.title.slice(0, 50)}... ` +
            `(confidence: ${(signal.confidence_score * 100).toFixed(1)}%)`
        );
    });
}

async function filterExample() {
    console.log('\n=== Filter by Category Example ===\n');

    const client = new OmenClient({ apiKey: 'demo-key' });

    // Get high-confidence geopolitical signals
    const signals = await client.getSignals({
        category: 'geopolitical',
        minConfidence: 0.7,
        limit: 10,
    });

    console.log(`High-confidence geopolitical signals: ${signals.length}`);
}

async function parallelExample() {
    console.log('\n=== Parallel Requests Example ===\n');

    const client = new OmenClient({ apiKey: 'demo-key' });
    const categories = ['geopolitical', 'weather', 'economic'];

    const results = await Promise.allSettled(
        categories.map((category) =>
            client.getSignals({ category, limit: 5 })
        )
    );

    results.forEach((result, index) => {
        const category = categories[index];
        if (result.status === 'fulfilled') {
            console.log(`  ${category}: ${result.value.length} signals`);
        } else {
            console.log(`  ${category}: Error - ${result.reason}`);
        }
    });
}

// ═══════════════════════════════════════════════════════════════════════════
// MAIN
// ═══════════════════════════════════════════════════════════════════════════

async function main() {
    console.log('OMEN API TypeScript Examples\n');
    console.log('='.repeat(60));

    try {
        await basicExample();
    } catch (error) {
        console.log(`Basic example error: ${error}`);
    }

    try {
        await filterExample();
    } catch (error) {
        console.log(`Filter example error: ${error}`);
    }

    try {
        await parallelExample();
    } catch (error) {
        console.log(`Parallel example error: ${error}`);
    }

    console.log('\n' + '='.repeat(60));
    console.log('Examples complete!');
}

main().catch(console.error);
