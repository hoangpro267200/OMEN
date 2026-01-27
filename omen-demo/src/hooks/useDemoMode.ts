import { useState, useCallback } from 'react';
import { mockSignal } from '../data/mockSignal';
import type { OmenSignal } from '../types/omen';

const delay = (ms: number) =>
  new Promise<void>((resolve) => setTimeout(resolve, ms));

export function useDemoMode() {
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentStage, setCurrentStage] = useState(0);
  const [signal, setSignal] = useState<OmenSignal | null>(null);

  const runDemo = useCallback(async () => {
    setIsProcessing(true);
    setSignal(null);
    setCurrentStage(0);

    setCurrentStage(1);
    await delay(800);

    setCurrentStage(2);
    await delay(800);

    setCurrentStage(3);
    await delay(800);

    setCurrentStage(4);
    await delay(500);

    setSignal(mockSignal);
    setIsProcessing(false);
  }, []);

  return { isProcessing, currentStage, signal, runDemo };
}
