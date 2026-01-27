import { motion } from 'framer-motion';
import { InputCard } from './InputCard';
import { ProcessingCard } from './ProcessingCard';
import { OutputCard } from './OutputCard';
import { FlowArrow } from './FlowArrow';

interface DataFlowSectionProps {
  currentStage: number;
  isProcessing: boolean;
  hasResult: boolean;
}

export function DataFlowSection({
  currentStage,
  isProcessing,
  hasResult,
}: DataFlowSectionProps) {
  const flowActive = isProcessing || currentStage > 0;
  const inputActive = flowActive;
  const processingActive = currentStage >= 1 && currentStage <= 4;
  const outputActive = currentStage >= 4 || hasResult;

  return (
    <motion.section
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="mb-12"
    >
      <h2 className="text-xl font-semibold text-white mb-6 flex items-center gap-2">
        <span className="w-1 h-6 bg-blue-500 rounded-full" />
        Data Flow
      </h2>
      <div className="flex flex-wrap items-center justify-center gap-4 md:gap-6">
        <InputCard active={inputActive} />
        <FlowArrow active={currentStage >= 1 && currentStage < 2} />
        <ProcessingCard active={processingActive} stage={currentStage} />
        <FlowArrow active={currentStage >= 3 && currentStage < 4} />
        <OutputCard active={outputActive} hasResult={hasResult} />
      </div>
    </motion.section>
  );
}
