import { useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDemoModeContext } from '../context/DemoModeContext';
import { runSceneActions } from '../lib/autoActionRunner';

/**
 * Keyboard shortcuts for Demo Mode:
 * - → or Space: Next scene
 * - ←: Previous scene
 * - P: Play current scene
 * - Escape: Exit demo mode
 * - Shift+Escape: Panic — reset to scene 1 and navigate home (no F5)
 */
export function useKeyboardShortcuts() {
  const navigate = useNavigate();
  const {
    isDemoMode,
    setDemoMode,
    currentScene,
    goToScene,
    scenes,
    sceneCount,
    setPlayingActions,
    resetDemo,
  } = useDemoModeContext();

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!isDemoMode) return;

      // Panic: Shift+Esc — reset to scene 1, navigate home
      if (e.shiftKey && e.key === 'Escape') {
        e.preventDefault();
        resetDemo();
        navigate(scenes[0].route);
        return;
      }

      // Exit demo
      if (e.key === 'Escape') {
        e.preventDefault();
        setDemoMode(false);
        return;
      }

      // Next: → or Space (when not in an input)
      if (e.key === 'ArrowRight' || (e.key === ' ' && !isInputTarget(e.target))) {
        e.preventDefault();
        if (e.key === ' ' && (e.target as HTMLElement).tagName === 'BUTTON') return;
        if (currentScene < sceneCount - 1) {
          const next = currentScene + 1;
          goToScene(next);
          navigate(scenes[next].route);
        }
        return;
      }

      // Prev: ←
      if (e.key === 'ArrowLeft') {
        e.preventDefault();
        if (currentScene > 0) {
          const prev = currentScene - 1;
          goToScene(prev);
          navigate(scenes[prev].route);
        }
        return;
      }

      // Play: P (when not in an input)
      if ((e.key === 'p' || e.key === 'P') && !isInputTarget(e.target)) {
        e.preventDefault();
        const scene = scenes[currentScene];
        navigate(scene.route);
        setPlayingActions(true);
        runSceneActions(scene).finally(() => setPlayingActions(false));
      }
    },
    [
      isDemoMode,
      setDemoMode,
      currentScene,
      goToScene,
      scenes,
      sceneCount,
      setPlayingActions,
      resetDemo,
      navigate,
    ]
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);
}

function isInputTarget(target: EventTarget | null): boolean {
  if (!target || !(target instanceof HTMLElement)) return false;
  const tag = target.tagName.toLowerCase();
  const role = target.getAttribute('role');
  const isEditable = target.isContentEditable;
  return (
    tag === 'input' ||
    tag === 'textarea' ||
    tag === 'select' ||
    role === 'textbox' ||
    role === 'searchbox' ||
    isEditable
  );
}
