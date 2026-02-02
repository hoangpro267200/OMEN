import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';
import { cn } from '../../lib/utils';
import { SignalEnvelopeTab } from './SignalEnvelopeTab';
import { SignalPayloadTab } from './SignalPayloadTab';
import { SignalDeliveryTab } from './SignalDeliveryTab';
import { SignalRawTab } from './SignalRawTab';
import type { SignalBrowserRecord } from '../../data/signalsBrowserMock';

type DrawerTab = 'envelope' | 'payload' | 'delivery' | 'raw';

const TABS: { id: DrawerTab; label: string }[] = [
  { id: 'envelope', label: 'Envelope' },
  { id: 'payload', label: 'Payload' },
  { id: 'delivery', label: 'Delivery' },
  { id: 'raw', label: 'Raw JSON' },
];

export interface SignalDrawerProps {
  record: SignalBrowserRecord | null;
  onClose: () => void;
  className?: string;
}

/**
 * Slide-in drawer from right with full signal details. Tabs: Envelope, Payload, Delivery, Raw JSON.
 */
export function SignalDrawer({ record, onClose, className = '' }: SignalDrawerProps) {
  const [tab, setTab] = useState<DrawerTab>('envelope');

  return (
    <AnimatePresence>
      {record && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-40 bg-black/50"
            aria-hidden
          />
          <motion.aside
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'tween', duration: 0.2, ease: 'easeOut' }}
            className={cn(
              'fixed right-0 top-0 z-50 flex h-full w-full max-w-lg flex-col border-l border-[var(--border-subtle)] bg-[var(--bg-secondary)] shadow-xl',
              className
            )}
          >
            {/* Header */}
            <div className="flex shrink-0 items-center justify-between gap-4 border-b border-[var(--border-subtle)] px-4 py-3">
              <h2 className="font-display text-base font-medium text-[var(--text-primary)] truncate">
                Signal: {record.signal_id}
              </h2>
              <button
                type="button"
                onClick={onClose}
                className="rounded p-2 text-[var(--text-muted)] hover:bg-[var(--bg-tertiary)] hover:text-[var(--text-primary)]"
                aria-label="Close"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Tabs */}
            <div className="flex shrink-0 gap-1 border-b border-[var(--border-subtle)] px-4">
              {TABS.map((t) => (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => setTab(t.id)}
                  className={cn(
                    'px-3 py-2 text-xs font-medium font-mono transition-colors',
                    tab === t.id
                      ? 'border-b-2 border-[var(--accent-blue)] text-[var(--accent-blue)]'
                      : 'text-[var(--text-muted)] hover:text-[var(--text-primary)]'
                  )}
                >
                  {t.label}
                </button>
              ))}
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto overflow-thin-scroll px-4 py-4">
              {tab === 'envelope' && <SignalEnvelopeTab record={record} />}
              {tab === 'payload' && <SignalPayloadTab record={record} />}
              {tab === 'delivery' && <SignalDeliveryTab record={record} />}
              {tab === 'raw' && <SignalRawTab record={record} />}
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
