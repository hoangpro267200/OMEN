/**
 * OperationsScreen - Enterprise Operations Dashboard
 * 
 * Showcases all new enterprise features:
 * - Audit Trail
 * - Processing Logs
 * - Signal Timeline
 * - Advanced Search
 * - Skeleton Loaders
 */

import { useState } from 'react';
import { motion } from 'framer-motion';
import { 
  Shield, 
  Terminal, 
  Clock, 
  Search,
  Activity,
  RefreshCw,
} from 'lucide-react';
import { GlassCard, GlassCardTitle } from '../components/ui/GlassCard';
import { AuditTrail } from '../components/audit/AuditTrail';
import { ProcessingLogs } from '../components/audit/ProcessingLogs';
import { SignalTimeline } from '../components/timeline/SignalTimeline';
import { AdvancedSearchBar } from '../components/search/AdvancedSearchBar';
import { SkeletonTable, SkeletonChart } from '../components/ui/Skeleton';
import { cn } from '../lib/utils';
import type { ParsedQuery } from '../lib/search-parser';

type TabId = 'audit' | 'logs' | 'timeline';

interface Tab {
  id: TabId;
  label: string;
  icon: React.ReactNode;
}

const TABS: Tab[] = [
  { id: 'audit', label: 'Audit Trail', icon: <Shield className="w-4 h-4" /> },
  { id: 'logs', label: 'Processing Logs', icon: <Terminal className="w-4 h-4" /> },
  { id: 'timeline', label: 'Signal History', icon: <Clock className="w-4 h-4" /> },
];

export function OperationsScreen() {
  const [activeTab, setActiveTab] = useState<TabId>('audit');
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSearch = (value: string, parsed: ParsedQuery) => {
    setSearchQuery(value);
    console.log('Search:', { value, parsed });
  };

  const handleSearchSubmit = (value: string, parsed: ParsedQuery) => {
    console.log('Search submitted:', { value, parsed });
    // Simulate loading
    setIsLoading(true);
    setTimeout(() => setIsLoading(false), 1500);
  };

  const handleRefresh = () => {
    setIsLoading(true);
    setTimeout(() => setIsLoading(false), 1000);
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div>
          <h1 className="text-2xl font-display font-bold text-text-primary tracking-tight">
            Operations Center
          </h1>
          <p className="text-text-muted text-sm mt-1 font-body">
            Enterprise audit, logs, and signal history
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleRefresh}
            disabled={isLoading}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-lg',
              'bg-bg-tertiary text-text-secondary hover:bg-bg-elevated transition-colors',
              isLoading && 'opacity-50'
            )}
          >
            <RefreshCw className={cn('w-4 h-4', isLoading && 'animate-spin')} />
            Refresh
          </button>
        </div>
      </motion.div>

      {/* Search Bar */}
      <GlassCard className="p-4" delay={0.1}>
        <div className="flex items-center gap-3 mb-3">
          <Search className="w-5 h-5 text-accent-cyan" />
          <span className="font-semibold text-text-primary">Advanced Search</span>
          <span className="text-xs text-text-muted">Try: status:ACTIVE confidence:&gt;0.7</span>
        </div>
        <AdvancedSearchBar
          value={searchQuery}
          onChange={handleSearch}
          onSubmit={handleSearchSubmit}
          placeholder="Search signals, audit entries, logs..."
          size="lg"
        />
      </GlassCard>

      {/* Tabs */}
      <div className="flex items-center gap-1 p-1 rounded-xl bg-bg-tertiary/50 w-fit">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all',
              activeTab === tab.id
                ? 'bg-accent-cyan/20 text-accent-cyan shadow-glow-cyan'
                : 'text-text-muted hover:text-text-primary hover:bg-bg-tertiary'
            )}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <motion.div
        key={activeTab}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2 }}
      >
        {isLoading ? (
          <div className="space-y-4">
            <SkeletonTable rows={8} columns={5} />
          </div>
        ) : (
          <>
            {activeTab === 'audit' && (
              <GlassCard className="p-4" delay={0.2}>
                <AuditTrail
                  showFilters
                  showExport
                  maxEntries={30}
                  onRefresh={handleRefresh}
                  isLoading={isLoading}
                />
              </GlassCard>
            )}

            {activeTab === 'logs' && (
              <GlassCard className="p-0 overflow-hidden" delay={0.2}>
                <ProcessingLogs
                  showFilters
                  showExport
                  maxLogs={200}
                  height={500}
                  autoScroll
                />
              </GlassCard>
            )}

            {activeTab === 'timeline' && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <GlassCard className="p-4" delay={0.2}>
                  <SignalTimeline
                    signalId="OMEN-9C4860"
                    showChart
                    maxEvents={15}
                    onRefresh={handleRefresh}
                    isLoading={isLoading}
                  />
                </GlassCard>
                <GlassCard className="p-4" delay={0.25}>
                  <SignalTimeline
                    signalId="OMEN-ABC123"
                    showChart
                    maxEvents={15}
                    onRefresh={handleRefresh}
                    isLoading={isLoading}
                  />
                </GlassCard>
              </div>
            )}
          </>
        )}
      </motion.div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <GlassCard className="p-4" delay={0.3}>
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-accent-cyan/10">
              <Activity className="w-5 h-5 text-accent-cyan" />
            </div>
            <div>
              <p className="text-2xl font-display font-bold text-text-primary">1,247</p>
              <p className="text-xs text-text-muted">Events Today</p>
            </div>
          </div>
        </GlassCard>
        <GlassCard className="p-4" delay={0.35}>
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-status-success/10">
              <Shield className="w-5 h-5 text-status-success" />
            </div>
            <div>
              <p className="text-2xl font-display font-bold text-text-primary">98.5%</p>
              <p className="text-xs text-text-muted">Audit Compliance</p>
            </div>
          </div>
        </GlassCard>
        <GlassCard className="p-4" delay={0.4}>
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-accent-amber/10">
              <Terminal className="w-5 h-5 text-accent-amber" />
            </div>
            <div>
              <p className="text-2xl font-display font-bold text-text-primary">2.3ms</p>
              <p className="text-xs text-text-muted">Avg Log Latency</p>
            </div>
          </div>
        </GlassCard>
        <GlassCard className="p-4" delay={0.45}>
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-status-error/10">
              <Clock className="w-5 h-5 text-status-error" />
            </div>
            <div>
              <p className="text-2xl font-display font-bold text-text-primary">3</p>
              <p className="text-xs text-text-muted">Alerts Active</p>
            </div>
          </div>
        </GlassCard>
      </div>
    </div>
  );
}

export default OperationsScreen;
