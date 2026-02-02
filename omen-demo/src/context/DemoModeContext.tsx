import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { DEMO_SCENES, DEMO_SCENE_COUNT, type DemoScene } from '../lib/demoScenes';

export interface DemoModeContextValue {
  isDemoMode: boolean;
  setDemoMode: (on: boolean) => void;
  currentScene: number;
  setCurrentScene: (index: number) => void;
  goToScene: (index: number) => void;
  scenes: DemoScene[];
  sceneCount: number;
  /** Panic reset: go back to scene 1 (caller should also navigate to overview) */
  resetDemo: () => void;
  /** Whether auto-actions are currently playing */
  isPlayingActions: boolean;
  setPlayingActions: (playing: boolean) => void;
}

const DemoModeContext = createContext<DemoModeContextValue | null>(null);

export function DemoModeProvider({ children }: { children: ReactNode }) {
  const [isDemoMode, setDemoModeState] = useState(false);
  const [currentScene, setCurrentScene] = useState(0);
  const [isPlayingActions, setPlayingActions] = useState(false);

  const setDemoMode = useCallback((on: boolean) => {
    setDemoModeState(on);
    if (!on) {
      setCurrentScene(0);
      setPlayingActions(false);
    }
  }, []);

  const goToScene = useCallback((index: number) => {
    const clamped = Math.max(0, Math.min(DEMO_SCENE_COUNT - 1, index));
    setCurrentScene(clamped);
  }, []);

  const resetDemo = useCallback(() => {
    setCurrentScene(0);
    setPlayingActions(false);
  }, []);

  const value = useMemo<DemoModeContextValue>(
    () => ({
      isDemoMode,
      setDemoMode,
      currentScene,
      setCurrentScene,
      goToScene,
      scenes: DEMO_SCENES,
      sceneCount: DEMO_SCENE_COUNT,
      resetDemo,
      isPlayingActions,
      setPlayingActions,
    }),
    [isDemoMode, setDemoMode, currentScene, goToScene, resetDemo, isPlayingActions]
  );

  return (
    <DemoModeContext.Provider value={value}>
      {children}
    </DemoModeContext.Provider>
  );
}

export function useDemoModeContext(): DemoModeContextValue {
  const ctx = useContext(DemoModeContext);
  if (!ctx) throw new Error('useDemoModeContext must be used within DemoModeProvider');
  return ctx;
}
