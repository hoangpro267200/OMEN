import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ChevronLeft, ChevronRight, Play, X } from 'lucide-react';
import { useDemoModeContext } from '../../context/DemoModeContext';
import { runSceneActions } from '../../lib/autoActionRunner';
import { cn } from '../../lib/utils';

/**
 * Scene Stepper overlay at bottom when Demo Mode is ON.
 * Scene N of 6, title, script, progress dots, Prev / Play Scene / Next / Exit Demo Mode.
 */
export function SceneStepper() {
  const navigate = useNavigate();
  const {
    isDemoMode,
    setDemoMode,
    currentScene,
    goToScene,
    scenes,
    sceneCount,
    isPlayingActions,
    setPlayingActions,
  } = useDemoModeContext();

  const scene = scenes[currentScene];

  const handlePrev = useCallback(() => {
    const next = Math.max(0, currentScene - 1);
    goToScene(next);
    navigate(scenes[next].route);
  }, [currentScene, goToScene, navigate, scenes]);

  const handleNext = useCallback(() => {
    const next = Math.min(sceneCount - 1, currentScene + 1);
    goToScene(next);
    navigate(scenes[next].route);
  }, [currentScene, goToScene, navigate, sceneCount, scenes]);

  const handleSceneClick = useCallback(
    (index: number) => {
      goToScene(index);
      navigate(scenes[index].route);
    },
    [goToScene, navigate, scenes]
  );

  const handlePlayScene = useCallback(async () => {
    navigate(scene.route);
    setPlayingActions(true);
    try {
      await runSceneActions(scene);
    } finally {
      setPlayingActions(false);
    }
  }, [navigate, scene, setPlayingActions]);

  const handleExitDemo = useCallback(() => {
    setDemoMode(false);
  }, [setDemoMode]);

  if (!isDemoMode || !scene) return null;

  return (
    <motion.div
      initial={{ y: 24, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      exit={{ y: 24, opacity: 0 }}
      transition={{ duration: 0.2, ease: 'easeOut' }}
      className="fixed bottom-0 left-0 right-0 z-50 border-t border-[var(--border-subtle)] bg-[var(--bg-secondary)]/98 backdrop-blur-sm shadow-[0_-4px_24px_rgba(0,0,0,0.3)]"
    >
      <div className="mx-auto max-w-4xl px-4 py-4">
        <div className="mb-3 flex items-center justify-between">
          <span className="font-mono text-xs font-medium uppercase tracking-wider text-[var(--text-muted)]">
            DEMO MODE
          </span>
        </div>

        <div className="mb-3">
          <p className="font-mono text-sm font-medium text-[var(--text-primary)]">
            Scene {currentScene + 1} of {sceneCount}: {scene.title}
          </p>
          <p className="mt-1 text-xs text-[var(--text-secondary)]">&quot;{scene.script}&quot;</p>
        </div>

        {/* Progress dots */}
        <div className="mb-4 flex items-center justify-center gap-1">
          {scenes.map((_, index) => (
            <button
              key={index}
              type="button"
              onClick={() => handleSceneClick(index)}
              aria-label={`Go to scene ${index + 1}: ${scenes[index].title}`}
              aria-current={currentScene === index ? 'step' : undefined}
              className={cn(
                'flex items-center gap-1 rounded-[var(--radius-badge)] px-1 py-0.5 transition-colors',
                currentScene === index
                  ? 'text-[var(--accent-blue)]'
                  : 'text-[var(--text-muted)] hover:text-[var(--text-secondary)]'
              )}
            >
              <span
                className={cn(
                  'h-2 w-2 rounded-full border',
                  currentScene === index
                    ? 'border-[var(--accent-blue)] bg-[var(--accent-blue)]'
                    : 'border-[var(--border-subtle)] bg-transparent'
                )}
              />
              {index < sceneCount - 1 && index !== currentScene && (
                <span className="h-px w-3 bg-[var(--border-subtle)]" aria-hidden />
              )}
              {index < sceneCount - 1 && index === currentScene && (
                <span className="h-px w-3 bg-[var(--accent-blue)]" aria-hidden />
              )}
            </button>
          ))}
        </div>
        <div className="mb-4 flex justify-center gap-1 font-mono text-xs text-[var(--text-muted)]">
          {scenes.map((_, index) => (
            <span key={index} className="w-6 text-center">
              {index + 1}
            </span>
          ))}
        </div>

        {/* Buttons */}
        <div className="flex flex-wrap items-center justify-center gap-3">
          <button
            type="button"
            onClick={handlePrev}
            disabled={currentScene === 0}
            aria-label="Previous scene"
            className="inline-flex items-center gap-1.5 rounded-[var(--radius-button)] border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] px-3 py-2 text-sm font-medium text-[var(--text-primary)] transition-colors hover:bg-[var(--border-subtle)]/50 disabled:opacity-40 disabled:pointer-events-none"
          >
            <ChevronLeft className="h-4 w-4" />
            Prev
          </button>
          <button
            type="button"
            onClick={handlePlayScene}
            disabled={isPlayingActions}
            aria-label="Play scene actions"
            className="inline-flex items-center gap-1.5 rounded-[var(--radius-button)] border border-[var(--accent-blue)] bg-[var(--accent-blue)]/20 px-3 py-2 text-sm font-medium text-[var(--accent-blue)] transition-colors hover:bg-[var(--accent-blue)]/30 disabled:opacity-50 disabled:pointer-events-none"
          >
            <Play className="h-4 w-4" />
            {isPlayingActions ? 'Playing…' : 'Play Scene'}
          </button>
          <button
            type="button"
            onClick={handleNext}
            disabled={currentScene === sceneCount - 1}
            aria-label="Next scene"
            className="inline-flex items-center gap-1.5 rounded-[var(--radius-button)] border border-[var(--border-subtle)] bg-[var(--bg-tertiary)] px-3 py-2 text-sm font-medium text-[var(--text-primary)] transition-colors hover:bg-[var(--border-subtle)]/50 disabled:opacity-40 disabled:pointer-events-none"
          >
            Next
            <ChevronRight className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={handleExitDemo}
            aria-label="Exit demo mode"
            className="ml-2 inline-flex items-center gap-1.5 rounded-[var(--radius-button)] border border-[var(--border-subtle)] px-3 py-2 text-sm font-medium text-[var(--text-muted)] transition-colors hover:bg-[var(--bg-tertiary)] hover:text-[var(--text-primary)]"
          >
            <X className="h-4 w-4" />
            Exit Demo Mode
          </button>
        </div>
      </div>
    </motion.div>
  );
}
