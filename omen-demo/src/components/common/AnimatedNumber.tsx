import { useEffect, useState } from 'react';
import { motion, useSpring } from 'framer-motion';

interface AnimatedNumberProps {
  value: number;
  className?: string;
  decimals?: number;
  prefix?: string;
  suffix?: string;
  format?: (n: number) => string;
}

export function AnimatedNumber({
  value,
  className = '',
  decimals = 0,
  prefix = '',
  suffix = '',
  format,
}: AnimatedNumberProps) {
  const [display, setDisplay] = useState(value);
  const spring = useSpring(value, { stiffness: 80, damping: 25 });

  useEffect(() => {
    spring.set(value);
  }, [value, spring]);

  useEffect(() => {
    const unsub = spring.on('change', (v) => setDisplay(v));
    return () => unsub();
  }, [spring]);

  const str = format
    ? format(display)
    : decimals > 0
      ? display.toFixed(decimals)
      : Math.round(display).toLocaleString();

  return (
    <motion.span
      className={className}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.2 }}
      key={value}
    >
      {prefix}
      {str}
      {suffix}
    </motion.span>
  );
}
