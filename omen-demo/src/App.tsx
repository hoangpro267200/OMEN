import { useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Play, Loader2, Zap, AlertTriangle } from 'lucide-react';
import { Header } from './components/Layout/Header';
import { DataFlowSection } from './components/DataFlow/DataFlowSection';
import { SignalCard } from './components/SignalDetail/SignalCard';
import { ExplanationChain } from './components/Explanation/ExplanationChain';
import { RouteMap } from './components/Map/RouteMap';
import { useDemoMode } from './hooks/useDemoMode';
import {
  useProcessEvents,
  type ProcessedSignal,
} from './hooks/useOmenApi';

const delay = (ms: number) =>
  new Promise<void>((resolve) => setTimeout(resolve, ms));

function App() {
  const { isProcessing, currentStage, signal, runDemo } = useDemoMode();
  const processEvents = useProcessEvents();
  const [liveStage, setLiveStage] = useState(0);
  const [liveSignal, setLiveSignal] = useState<ProcessedSignal | null>(null);

  const runLiveAnalysis = useCallback(async () => {
    setLiveSignal(null);
    setLiveStage(1);
    await delay(500);
    setLiveStage(2);
    await delay(500);
    setLiveStage(3);
    await delay(500);
    setLiveStage(4);
    try {
      const results = await processEvents.mutateAsync({
        limit: 10,
        min_liquidity: 1000,
      });
      setLiveSignal(results[0] ?? null);
    } catch {
      setLiveSignal(null);
    } finally {
      setLiveStage(0);
    }
  }, [processEvents]);

  const isLiveRunning = liveStage > 0 || processEvents.isPending;
  const hasLiveResult = liveSignal != null;
  const showLiveNoResults =
    processEvents.isSuccess && !liveSignal && !isLiveRunning;

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-white">
      <Header
        isProcessing={isProcessing || isLiveRunning}
        hasSignal={signal != null || hasLiveResult}
      />

      <main className="max-w-6xl mx-auto px-6 py-8">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6 mb-10">
          <div>
            <h1 className="text-2xl md:text-3xl font-bold text-white">
              Signal intelligence demo
            </h1>
            <p className="text-zinc-400 mt-1">
              Run the pipeline to see OMEN process a Red Sea disruption signal.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <motion.button
              onClick={runDemo}
              disabled={isProcessing}
              whileHover={{ scale: isProcessing ? 1 : 1.02 }}
              whileTap={{ scale: isProcessing ? 1 : 0.98 }}
              className={`
                shrink-0 px-6 py-4 rounded-xl font-semibold text-lg flex items-center gap-2
                transition-all duration-200
                ${
                  isProcessing
                    ? 'bg-zinc-700 text-zinc-400 cursor-not-allowed'
                    : 'bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white'
                }
              `}
            >
              {isProcessing ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Processing…
                </>
              ) : (
                <>
                  <Play className="w-5 h-5" />
                  Run OMEN demo
                </>
              )}
            </motion.button>
            <motion.button
              onClick={runLiveAnalysis}
              disabled={isLiveRunning}
              whileHover={{ scale: isLiveRunning ? 1 : 1.02 }}
              whileTap={{ scale: isLiveRunning ? 0.98 : 1 }}
              className={`
                shrink-0 px-6 py-4 rounded-xl font-semibold text-lg flex items-center gap-2
                transition-all duration-200
                ${
                  isLiveRunning
                    ? 'bg-zinc-700 text-zinc-400 cursor-not-allowed'
                    : 'bg-gradient-to-r from-emerald-600 to-emerald-500 hover:from-emerald-500 hover:to-emerald-400 text-white'
                }
              `}
            >
              {isLiveRunning ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  {liveStage > 0 ? `Stage ${liveStage}/4` : 'Processing…'}
                </>
              ) : (
                <>
                  <Zap className="w-5 h-5" />
                  Run OMEN Analysis (Live)
                </>
              )}
            </motion.button>
          </div>
        </div>

        <DataFlowSection
          currentStage={isLiveRunning ? liveStage : currentStage}
          isProcessing={isProcessing || isLiveRunning}
          hasResult={signal != null || hasLiveResult}
        />

        {(signal != null || hasLiveResult) && (
          <>
            <section className="mb-12">
              <h2 className="text-xl font-semibold text-white mb-6 flex items-center gap-2">
                <span className="w-1 h-6 bg-blue-500 rounded-full" />
                {hasLiveResult ? 'Live signal' : 'Signal'}
              </h2>
              <SignalCard signal={(liveSignal ?? signal)!} />
            </section>
            <ExplanationChain
              chain={(liveSignal ?? signal)!.explanation_chain}
            />
            <RouteMap routes={(liveSignal ?? signal)!.affected_routes} />
          </>
        )}

        {showLiveNoResults && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="rounded-2xl border border-amber-500/30 bg-amber-500/5 p-8 flex items-center gap-4"
          >
            <AlertTriangle className="w-8 h-8 text-amber-400 shrink-0" />
            <p className="text-zinc-300">
              No signals generated. Events may have been filtered by validation
              rules or had insufficient liquidity. Try “Run OMEN demo” for a
              simulated result.
            </p>
          </motion.div>
        )}

        {!signal && !hasLiveResult && !isProcessing && !isLiveRunning && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="rounded-2xl border border-dashed border-white/20 bg-white/5 p-12 text-center"
          >
            <p className="text-zinc-500">
              Click “Run OMEN demo” to simulate processing, or “Run OMEN
              Analysis (Live)” to fetch real Polymarket events and process them
              (requires backend at <code className="text-zinc-400">localhost:8000</code>).
            </p>
          </motion.div>
        )}
      </main>
    </div>
  );
}

export default App;
