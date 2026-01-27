import { motion } from 'framer-motion';
import { Database } from 'lucide-react';
import { Card } from '../common/Card';

interface InputCardProps {
  active: boolean;
}

export function InputCard({ active }: InputCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0.6, scale: 0.98 }}
      animate={{
        opacity: active ? 1 : 0.7,
        scale: active ? 1 : 0.98,
        boxShadow: active ? '0 0 40px rgba(59, 130, 246, 0.15)' : 'none',
      }}
      transition={{ duration: 0.3 }}
    >
      <Card glow={active} className="p-6 min-w-[160px] text-center">
        <Database className="w-10 h-10 mx-auto mb-3 text-blue-400" />
        <div className="text-sm font-medium text-white">Input</div>
        <div className="text-xs text-zinc-500 mt-1">Prediction markets</div>
      </Card>
    </motion.div>
  );
}
