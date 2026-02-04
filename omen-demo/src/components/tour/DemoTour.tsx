/**
 * DemoTour - Guided product tour for investor demos
 * 
 * Features:
 * - Step-by-step walkthrough
 * - Spotlight highlighting
 * - Keyboard navigation
 * - Progress indicator
 * - Skip/exit functionality
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  X,
  ChevronLeft,
  ChevronRight,
  Play,
  SkipForward,
  CheckCircle,
  Sparkles,
  Keyboard,
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { ROUTES } from '../../lib/routes';

// ============================================================================
// TYPES
// ============================================================================

export interface TourStep {
  id: string;
  title: string;
  description: string;
  /** CSS selector for element to highlight */
  target?: string;
  /** Route to navigate to before this step */
  route?: string;
  /** Position of tooltip relative to target */
  position?: 'top' | 'bottom' | 'left' | 'right' | 'center';
  /** Action to perform on this step */
  action?: () => void;
  /** Delay before showing this step (ms) */
  delay?: number;
  /** Custom content to render */
  content?: React.ReactNode;
}

export interface DemoTourProps {
  /** Tour steps */
  steps?: TourStep[];
  /** Whether the tour is active */
  isActive: boolean;
  /** Callback when tour is closed */
  onClose: () => void;
  /** Callback when tour completes */
  onComplete?: () => void;
  /** Starting step index */
  startAt?: number;
}

// ============================================================================
// DEFAULT TOUR STEPS
// ============================================================================

const DEFAULT_TOUR_STEPS: TourStep[] = [
  {
    id: 'welcome',
    title: 'Welcome to OMEN',
    description: 'OMEN transforms prediction market data into validated intelligence signals for supply chain risk management. Let me show you around.',
    position: 'center',
    route: ROUTES.overview,
  },
  {
    id: 'command-palette',
    title: 'Command Palette',
    description: 'Press Cmd+K (or Ctrl+K) to open the command palette. Search for signals, navigate to pages, or run actions instantly.',
    target: '[data-tour="header"]',
    position: 'bottom',
  },
  {
    id: 'data-mode',
    title: 'Data Mode Switcher',
    description: 'Switch between LIVE (real API), DEMO (mock data), and HYBRID (live with fallback) modes seamlessly.',
    target: '[data-tour="data-mode"]',
    position: 'bottom',
  },
  {
    id: 'signals-overview',
    title: 'Signal Feed',
    description: 'Real-time feed of validated signals. Each signal is enriched with geographic context, confidence scores, and actionable metadata.',
    target: '[data-tour="signal-feed"]',
    position: 'right',
    route: ROUTES.signals,
  },
  {
    id: 'signal-detail',
    title: 'Signal Deep Dive',
    description: 'Click any signal to see comprehensive details: probability trends, confidence breakdown, evidence chain, and data lineage.',
    position: 'center',
  },
  {
    id: 'pipeline',
    title: 'Pipeline Monitor',
    description: 'Visualize how raw prediction market events flow through validation, enrichment, and classification stages.',
    target: '[data-tour="pipeline"]',
    position: 'bottom',
    route: ROUTES.pipeline,
  },
  {
    id: 'explainability',
    title: 'Full Explainability',
    description: 'Hover over any metric to see: what it means, where it comes from, how it was calculated, and when it was updated.',
    position: 'center',
  },
  {
    id: 'lineage',
    title: 'Data Lineage',
    description: 'Every signal has a complete data lineage graph showing the transformation from raw event to validated signal.',
    position: 'center',
  },
  {
    id: 'complete',
    title: 'Ready to Explore!',
    description: 'You\'ve seen the key features. OMEN provides the transparency and traceability needed for enterprise decision-making.',
    position: 'center',
  },
];

// ============================================================================
// COMPONENT
// ============================================================================

export function DemoTour({
  steps = DEFAULT_TOUR_STEPS,
  isActive,
  onClose,
  onComplete,
  startAt = 0,
}: DemoTourProps) {
  const [currentStep, setCurrentStep] = useState(startAt);
  const [targetRect, setTargetRect] = useState<DOMRect | null>(null);
  const navigate = useNavigate();
  const location = useLocation();
  const overlayRef = useRef<HTMLDivElement>(null);

  const step = steps[currentStep];
  const isFirstStep = currentStep === 0;
  const isLastStep = currentStep === steps.length - 1;

  // Update target element position
  const updateTargetPosition = useCallback(() => {
    if (step?.target) {
      const element = document.querySelector(step.target);
      if (element) {
        setTargetRect(element.getBoundingClientRect());
      } else {
        setTargetRect(null);
      }
    } else {
      setTargetRect(null);
    }
  }, [step]);

  // Navigate to route if needed
  useEffect(() => {
    if (isActive && step?.route && location.pathname !== step.route) {
      navigate(step.route);
    }
  }, [isActive, step, location.pathname, navigate]);

  // Update position on step change and resize
  useEffect(() => {
    if (!isActive) return;

    const timeout = setTimeout(updateTargetPosition, step?.delay || 100);
    window.addEventListener('resize', updateTargetPosition);
    window.addEventListener('scroll', updateTargetPosition);

    return () => {
      clearTimeout(timeout);
      window.removeEventListener('resize', updateTargetPosition);
      window.removeEventListener('scroll', updateTargetPosition);
    };
  }, [isActive, currentStep, updateTargetPosition, step]);

  // Execute step action
  useEffect(() => {
    if (isActive && step?.action) {
      step.action();
    }
  }, [isActive, step]);

  // Keyboard navigation
  useEffect(() => {
    if (!isActive) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      switch (e.key) {
        case 'ArrowRight':
        case 'Enter':
          if (!isLastStep) goNext();
          else handleComplete();
          break;
        case 'ArrowLeft':
          if (!isFirstStep) goPrev();
          break;
        case 'Escape':
          onClose();
          break;
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isActive, isFirstStep, isLastStep]);

  const goNext = () => setCurrentStep((s) => Math.min(s + 1, steps.length - 1));
  const goPrev = () => setCurrentStep((s) => Math.max(s - 1, 0));
  const goTo = (index: number) => setCurrentStep(index);

  const handleComplete = () => {
    onComplete?.();
    onClose();
  };

  if (!isActive) return null;

  // Calculate tooltip position
  const getTooltipStyle = (): React.CSSProperties => {
    if (!targetRect || step?.position === 'center') {
      return {
        position: 'fixed',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
      };
    }

    const padding = 16;
    const tooltipWidth = 400;
    const tooltipHeight = 200;

    switch (step?.position) {
      case 'top':
        return {
          position: 'fixed',
          top: targetRect.top - tooltipHeight - padding,
          left: targetRect.left + targetRect.width / 2 - tooltipWidth / 2,
        };
      case 'bottom':
        return {
          position: 'fixed',
          top: targetRect.bottom + padding,
          left: targetRect.left + targetRect.width / 2 - tooltipWidth / 2,
        };
      case 'left':
        return {
          position: 'fixed',
          top: targetRect.top + targetRect.height / 2 - tooltipHeight / 2,
          left: targetRect.left - tooltipWidth - padding,
        };
      case 'right':
        return {
          position: 'fixed',
          top: targetRect.top + targetRect.height / 2 - tooltipHeight / 2,
          left: targetRect.right + padding,
        };
      default:
        return {
          position: 'fixed',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
        };
    }
  };

  return createPortal(
    <AnimatePresence>
      <motion.div
        ref={overlayRef}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-[9999]"
      >
        {/* Backdrop with spotlight */}
        <div className="absolute inset-0">
          <svg className="w-full h-full">
            <defs>
              <mask id="spotlight-mask">
                <rect width="100%" height="100%" fill="white" />
                {targetRect && (
                  <rect
                    x={targetRect.left - 8}
                    y={targetRect.top - 8}
                    width={targetRect.width + 16}
                    height={targetRect.height + 16}
                    rx="8"
                    fill="black"
                  />
                )}
              </mask>
            </defs>
            <rect
              width="100%"
              height="100%"
              fill="rgba(0, 0, 0, 0.75)"
              mask="url(#spotlight-mask)"
            />
          </svg>
        </div>

        {/* Spotlight border */}
        {targetRect && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="absolute rounded-lg border-2 border-[var(--accent-cyan)] shadow-[0_0_0_4px_rgba(0,240,255,0.2)]"
            style={{
              top: targetRect.top - 8,
              left: targetRect.left - 8,
              width: targetRect.width + 16,
              height: targetRect.height + 16,
            }}
          />
        )}

        {/* Tooltip */}
        <motion.div
          key={currentStep}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          transition={{ duration: 0.3 }}
          style={getTooltipStyle()}
          className={cn(
            'w-[400px] rounded-2xl overflow-hidden',
            'bg-[var(--bg-secondary)]/95 backdrop-blur-xl',
            'border border-[var(--border-subtle)]',
            'shadow-2xl shadow-black/50'
          )}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--border-subtle)] bg-[var(--accent-cyan)]/5">
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-[var(--accent-cyan)]" />
              <span className="font-semibold text-[var(--text-primary)]">{step?.title}</span>
            </div>
            <button
              onClick={onClose}
              className="p-1 rounded-lg hover:bg-[var(--bg-tertiary)] text-[var(--text-muted)]"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Content */}
          <div className="p-4">
            {step?.content || (
              <p className="text-[var(--text-secondary)] leading-relaxed">{step?.description}</p>
            )}
          </div>

          {/* Progress */}
          <div className="px-4 py-2 border-t border-[var(--border-subtle)] bg-[var(--bg-tertiary)]/30">
            <div className="flex items-center gap-1 mb-3">
              {steps.map((_, idx) => (
                <button
                  key={idx}
                  onClick={() => goTo(idx)}
                  className={cn(
                    'h-1.5 rounded-full transition-all',
                    idx === currentStep
                      ? 'w-6 bg-[var(--accent-cyan)]'
                      : idx < currentStep
                      ? 'w-1.5 bg-[var(--accent-cyan)]/50'
                      : 'w-1.5 bg-[var(--bg-tertiary)]'
                  )}
                />
              ))}
            </div>

            {/* Actions */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs text-[var(--text-muted)]">
                <Keyboard className="w-3 h-3" />
                <span>Use ← → or Enter</span>
              </div>

              <div className="flex items-center gap-2">
                {!isFirstStep && (
                  <button
                    onClick={goPrev}
                    className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-[var(--bg-tertiary)] text-[var(--text-secondary)] hover:bg-[var(--bg-elevated)] text-sm transition-colors"
                  >
                    <ChevronLeft className="w-4 h-4" />
                    Back
                  </button>
                )}

                {isLastStep ? (
                  <button
                    onClick={handleComplete}
                    className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-[var(--accent-cyan)] text-black hover:bg-[var(--accent-cyan)]/90 text-sm font-medium transition-colors"
                  >
                    <CheckCircle className="w-4 h-4" />
                    Complete
                  </button>
                ) : (
                  <button
                    onClick={goNext}
                    className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-[var(--accent-cyan)] text-black hover:bg-[var(--accent-cyan)]/90 text-sm font-medium transition-colors"
                  >
                    Next
                    <ChevronRight className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>
          </div>
        </motion.div>

        {/* Skip button */}
        {!isLastStep && (
          <button
            onClick={onClose}
            className="fixed bottom-6 right-6 flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--bg-secondary)] border border-[var(--border-subtle)] text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
          >
            <SkipForward className="w-4 h-4" />
            Skip Tour
          </button>
        )}
      </motion.div>
    </AnimatePresence>,
    document.body
  );
}

// ============================================================================
// HOOK: useDemoTour
// ============================================================================

export function useDemoTour() {
  const [isActive, setIsActive] = useState(false);
  const [hasSeenTour, setHasSeenTour] = useState(() => {
    return localStorage.getItem('omen-tour-completed') === 'true';
  });

  const startTour = () => setIsActive(true);

  const closeTour = () => {
    setIsActive(false);
  };

  const completeTour = () => {
    setIsActive(false);
    setHasSeenTour(true);
    localStorage.setItem('omen-tour-completed', 'true');
  };

  const resetTour = () => {
    localStorage.removeItem('omen-tour-completed');
    setHasSeenTour(false);
  };

  return {
    isActive,
    hasSeenTour,
    startTour,
    closeTour,
    completeTour,
    resetTour,
  };
}

// ============================================================================
// TOUR TRIGGER BUTTON
// ============================================================================

export function TourTriggerButton({ className }: { className?: string }) {
  const { startTour } = useDemoTour();

  return (
    <button
      onClick={startTour}
      className={cn(
        'flex items-center gap-2 px-3 py-1.5 rounded-lg',
        'bg-[var(--accent-cyan)]/10 text-[var(--accent-cyan)]',
        'hover:bg-[var(--accent-cyan)]/20 transition-colors',
        'text-sm font-medium',
        className
      )}
    >
      <Play className="w-4 h-4" />
      Start Tour
    </button>
  );
}

// ============================================================================
// EXPORTS
// ============================================================================

export default DemoTour;
