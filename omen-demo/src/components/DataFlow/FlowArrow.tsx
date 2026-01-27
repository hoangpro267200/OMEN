import { motion } from 'framer-motion';

interface FlowArrowProps {
  active: boolean;
}

export function FlowArrow({ active }: FlowArrowProps) {
  return (
    <div className="relative w-24 h-8 flex items-center shrink-0">
      <div className="w-full h-0.5 bg-white/20 rounded" />
      {active && (
        <motion.div
          className="absolute left-0 w-3 h-3 bg-blue-500 rounded-full shadow-lg shadow-blue-500/50"
          initial={{ left: 0, opacity: 0 }}
          animate={{
            left: ['0%', '100%'],
            opacity: [0, 1, 1, 0],
          }}
          transition={{
            duration: 1.2,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
          style={{ width: 12, height: 12 }}
        />
      )}
      <div
        className="absolute right-0 w-0 h-0 border-t-[6px] border-t-transparent border-l-[10px] border-l-white/40 border-b-[6px] border-b-transparent"
        aria-hidden
      />
    </div>
  );
}
