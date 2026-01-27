import { useEffect, useState } from 'react';
import { motion, useSpring } from 'framer-motion';

interface AnimatedNumberProps {
  value: number;
  className?: string;
  decimals?: number;
}

export function AnimatedNumber({
  value,
  className = '',
  decimals = 1,
}: AnimatedNumberProps) {
  const [display, setDisplay] = useState(0);
  const spring = useSpring(0, { stiffness: 50, damping: 30 });

  useEffect(() => {
    spring.set(value);
  }, [value, spring]);

  useEffect(() => {
    const unsub = spring.on('change', (v) => {
      setDisplay(v);
    });
    return () => unsub();
  }, [spring]);

  return (
    <motion.span
      className={className}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
    >
      {display.toFixed(decimals)}
    </motion.span>
  );
}
