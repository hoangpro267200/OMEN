/**
 * SourcesObservatory - Neural Command Center data sources monitoring
 * Features: Constellation view, source cards, live data preview
 * 
 * Uses useDataSources hook for real-time data from backend.
 */
import { useState, useMemo, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { Radio, Grid, RefreshCw } from 'lucide-react';
import { GlassCard, GlassCardTitle } from '../components/ui/GlassCard';
import { SourceConstellation, type DataSource } from '../components/sources/SourceConstellation';
import { SourceCard } from '../components/sources/SourceCard';
import { DataPreview } from '../components/sources/DataPreview';
import { useDataModeSafe } from '../context/DataModeContext';
import { cn } from '../lib/utils';
import { OMEN_API_BASE } from '../lib/apiBase';

// Fallback sources when API is not available
const DEFAULT_SOURCES: DataSource[] = [
  { id: 'polymarket', name: 'Polymarket', status: 'healthy', latency: 120, type: 'real' },
  { id: 'ais', name: 'AIS Marine', status: 'healthy', latency: 450, type: 'real' },
  { id: 'commodity', name: 'Commodity', status: 'healthy', latency: 200, type: 'real' },
  { id: 'weather', name: 'Weather', status: 'healthy', latency: 300, type: 'real' },
  { id: 'news', name: 'News', status: 'healthy', latency: 150, type: 'real' },
  { id: 'stock', name: 'Stock', status: 'healthy', latency: 180, type: 'real' },
  { id: 'freight', name: 'Freight', status: 'healthy', latency: 250, type: 'real' },
];

export interface SourcesObservatoryProps {
  className?: string;
}

export function SourcesObservatory({ className }: SourcesObservatoryProps) {
  const [selectedSource, setSelectedSource] = useState<string | null>('polymarket');
  const [apiSources, setApiSources] = useState<DataSource[] | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const { isLive, isDemo, canUseLiveData } = useDataModeSafe();
  
  // Use ref for error count to avoid re-triggering effect
  const errorCountRef = useRef(0);

  // Fetch sources from backend health endpoint
  useEffect(() => {
    let isMounted = true;
    
    async function fetchSources() {
      // Use mock data when in demo mode OR when backend is not available
      if (isDemo || !canUseLiveData) {
        if (isMounted) {
          setApiSources(DEFAULT_SOURCES.map(s => ({ 
            ...s, 
            status: isDemo ? 'healthy' as const : 'mock' as const,
            type: isDemo ? 'real' as const : 'mock' as const 
          })));
          setIsLoading(false);
          errorCountRef.current = 0;
        }
        return;
      }

      try {
        // Use /health/sources endpoint for real source health status
        const baseUrl = OMEN_API_BASE.replace(/\/api\/v1\/?$/, '');
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000);
        
        const response = await fetch(`${baseUrl}/health/sources`, {
          signal: controller.signal,
        });
        clearTimeout(timeoutId);
        
        if (!isMounted) return;
        
        if (response.ok) {
          const data = await response.json();
          
          // Transform health check response to DataSource format
          const transformed: DataSource[] = Object.entries(data.sources || {}).map(([name, info]: [string, any]) => ({
            id: name.toLowerCase().replace(/\s+/g, '-'),
            name: name,
            status: info.status === 'healthy' ? 'healthy' : 
                    info.status === 'degraded' ? 'warning' : 
                    info.status === 'unhealthy' ? 'error' : 'mock',
            latency: info.latency_ms ?? 0,
            type: info.status === 'healthy' || info.status === 'degraded' ? 'real' : 'mock',
            lastCheck: info.last_check,
            error: info.error,
          }));
          
          if (transformed.length > 0) {
            setApiSources(transformed);
          } else {
            // If no sources registered, show defaults with 'mock' status
            setApiSources(DEFAULT_SOURCES.map(s => ({ ...s, status: 'mock' as const, type: 'mock' as const })));
          }
          errorCountRef.current = 0;
        } else {
          throw new Error(`HTTP ${response.status}`);
        }
      } catch (error) {
        if (!isMounted) return;
        
        // Only log first few errors to avoid console spam
        errorCountRef.current += 1;
        if (errorCountRef.current <= 3) {
          console.warn('[SourcesObservatory] Failed to fetch sources:', (error as Error).message);
        }
        
        // Fall back to default sources on first error
        setApiSources(prev => prev ?? DEFAULT_SOURCES.map(s => ({ ...s, status: 'mock' as const, type: 'mock' as const })));
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    fetchSources();
    
    // Only poll if in live mode and can use live data
    const interval = (isLive && canUseLiveData) 
      ? setInterval(fetchSources, 10000) 
      : null;
    
    return () => {
      isMounted = false;
      if (interval) clearInterval(interval);
    };
  }, [isLive, isDemo, canUseLiveData]);

  const sources = apiSources || DEFAULT_SOURCES;

  // Calculate summary stats
  const healthySources = sources.filter((s) => s.status === 'healthy').length;
  const totalSources = sources.length;
  const avgLatency = Math.round(
    sources.filter((s) => s.type === 'real').reduce((sum, s) => sum + s.latency, 0) /
      sources.filter((s) => s.type === 'real').length
  );

  return (
    <div className={cn('p-6 space-y-6', className)}>
      {/* Page Header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div>
          <h1 className="text-2xl font-display font-bold text-text-primary tracking-tight">
            Data Sources Observatory
          </h1>
          <p className="text-text-muted text-sm mt-1 font-body">
            Monitor all {totalSources} intelligence sources feeding into OMEN
          </p>
        </div>
        <div className="flex items-center gap-4 text-sm">
          <div className="flex items-center gap-2">
            <span className="text-text-muted">Active:</span>
            <span className="font-mono text-status-success">
              {healthySources}/{totalSources}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-text-muted">Avg Latency:</span>
            <span className="font-mono text-accent-cyan">{avgLatency}ms</span>
          </div>
        </div>
      </motion.div>

      {/* Constellation View */}
      <GlassCard className="p-6" delay={0.1}>
        <GlassCardTitle icon={<Radio className="w-4 h-4" />}>
          Source Constellation
        </GlassCardTitle>
        <div className="mt-4">
          <SourceConstellation
            sources={sources}
            selectedSource={selectedSource}
            onSelectSource={setSelectedSource}
          />
        </div>
      </GlassCard>

      {/* Source Cards Grid */}
      <GlassCard className="p-6" delay={0.2}>
        <GlassCardTitle icon={<Grid className="w-4 h-4" />}>
          Source Status
        </GlassCardTitle>
        <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {sources.map((source, index) => (
            <SourceCard
              key={source.id}
              source={source}
              isSelected={selectedSource === source.id}
              onClick={() => setSelectedSource(source.id)}
              delay={0.25 + index * 0.05}
            />
          ))}
        </div>
      </GlassCard>

      {/* Data Preview */}
      <GlassCard className="p-6" delay={0.5}>
        <GlassCardTitle>Live Data Preview</GlassCardTitle>
        <div className="mt-4">
          <DataPreview sourceId={selectedSource} />
        </div>
      </GlassCard>
    </div>
  );
}

export default SourcesObservatory;
