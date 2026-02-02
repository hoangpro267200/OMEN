/**
 * OMEN Signal Intelligence Engine — Neural Command Center
 * Main application entry point with routing
 */
import { StrictMode, lazy, Suspense } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import { DemoModeProvider } from './context/DemoModeContext'
import { WebSocketProvider } from './lib/websocket'
import { createQueryClientWithErrorHandling } from './lib/api/errorHandling'
import { ScreenErrorBoundary } from './components/ErrorBoundary'
import { ToastProvider } from './components/providers/ToastProvider'
import { AnnouncerProvider } from './components/a11y'
import { AppShell } from './components/Layout/AppShell'
import { LoadingSpinner } from './components/ui/LoadingSpinner'
import { ROUTES } from './lib/routes'
import { usePerformanceMonitoring } from './lib/performance/monitoring'
import './lib/i18n/i18n'
import './styles/globals.css'

function AppWithMonitoring() {
  usePerformanceMonitoring()
  return null
}

// Lazy-loaded screens
const CommandCenter = lazy(() => import('./screens/CommandCenter'))
const PipelineMonitor = lazy(() => import('./screens/PipelineMonitor'))
const SourcesObservatory = lazy(() => import('./screens/SourcesObservatory'))
const SignalDeepDive = lazy(() => import('./screens/SignalDeepDive'))
const OverviewPage = lazy(() => import('./screens/OverviewPage').then((m) => ({ default: m.OverviewPage })))
const PartitionsPage = lazy(() => import('./screens/PartitionsPage').then((m) => ({ default: m.PartitionsPage })))
const PartitionDetailPage = lazy(() => import('./screens/PartitionDetailPage').then((m) => ({ default: m.PartitionDetailPage })))
const SignalsPage = lazy(() => import('./screens/SignalsPage').then((m) => ({ default: m.SignalsPage })))
const IngestDemoPage = lazy(() => import('./screens/IngestDemoPage').then((m) => ({ default: m.IngestDemoPage })))
const LedgerProofPage = lazy(() => import('./screens/LedgerProofPage').then((m) => ({ default: m.LedgerProofPage })))

const queryClient = createQueryClientWithErrorHandling()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ScreenErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <AppWithMonitoring />
        <ToastProvider />
        <AnnouncerProvider>
          <WebSocketProvider>
            <BrowserRouter>
            <DemoModeProvider>
              <Suspense fallback={<LoadingSpinner fullscreen />}>
                <Routes>
                  <Route path={ROUTES.overview} element={<AppShell />}>
                    {/* Command Center is the new default home screen */}
                    <Route index element={<CommandCenter />} />
                    <Route path="pipeline" element={<PipelineMonitor />} />
                    <Route path="sources" element={<SourcesObservatory />} />
                    <Route path="signals/:signalId" element={<SignalDeepDive />} />
                    <Route path="overview-legacy" element={<OverviewPage />} />
                    <Route path="partitions" element={<PartitionsPage />} />
                    <Route path="partitions/:partitionId" element={<PartitionDetailPage />} />
                    <Route path="signals" element={<SignalsPage />} />
                    <Route path="ingest-demo" element={<IngestDemoPage />} />
                    <Route path="ledger-proof" element={<LedgerProofPage />} />
                  </Route>
                </Routes>
              </Suspense>
              </DemoModeProvider>
            </BrowserRouter>
          </WebSocketProvider>
        </AnnouncerProvider>
      </QueryClientProvider>
    </ScreenErrorBoundary>
  </StrictMode>,
)
