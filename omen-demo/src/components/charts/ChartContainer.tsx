import { useRef, useState, useEffect, type ReactNode } from 'react';

interface ChartContainerProps {
  width?: string | number;
  height: number;
  minHeight?: number;
  minWidth?: number;
  className?: string;
  style?: React.CSSProperties;
  children: (size: { width: number; height: number }) => ReactNode;
}

/**
 * Wrapper that only renders children (e.g. ResponsiveContainer) once the
 * container has positive dimensions, avoiding Recharts "width(-1) height(-1)" warnings.
 */
export function ChartContainer({
  width = '100%',
  height,
  minHeight,
  minWidth,
  className,
  style,
  children,
}: ChartContainerProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 0, height: 0 });

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const ro = new ResizeObserver(([e]) => {
      const { width: w, height: h } = e.contentRect;
      setSize({ width: Math.round(w), height: Math.round(h) });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      className={className}
      style={{ width, height, minHeight, minWidth, ...style }}
    >
      {size.width > 0 && size.height > 0 ? children(size) : null}
    </div>
  );
}
