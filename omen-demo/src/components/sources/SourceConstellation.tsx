/**
 * SourceConstellation - Neural Command Center data sources orbital visualization
 * Features: OMEN at center, sources orbiting with animated data flow particles
 */
import { motion } from 'framer-motion';
import { cn } from '../../lib/utils';

export interface DataSource {
  id: string;
  name: string;
  status: 'healthy' | 'warning' | 'error' | 'mock';
  latency: number;
  type: 'real' | 'mock';
}

const STATUS_COLORS: Record<string, string> = {
  healthy: '#00ff88',
  warning: '#ffaa00',
  error: '#ff3366',
  mock: '#6b7280',
};

interface SourceConstellationProps {
  sources: DataSource[];
  selectedSource: string | null;
  onSelectSource: (id: string) => void;
  className?: string;
}

export function SourceConstellation({
  sources,
  selectedSource,
  onSelectSource,
  className,
}: SourceConstellationProps) {
  const centerX = 300;
  const centerY = 150;
  const radius = 110;

  return (
    <div className={cn('relative h-[300px] w-full', className)}>
      <svg width="100%" height="100%" viewBox="0 0 600 300">
        {/* Background grid pattern */}
        <defs>
          <pattern id="constellation-grid" width="30" height="30" patternUnits="userSpaceOnUse">
            <path
              d="M 30 0 L 0 0 0 30"
              fill="none"
              stroke="rgba(255,255,255,0.03)"
              strokeWidth="1"
            />
          </pattern>
          
          {/* Glow filter */}
          <filter id="glow-filter">
            <feGaussianBlur stdDeviation="3" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          
          {/* Radial gradient for center */}
          <radialGradient id="centerGradient">
            <stop offset="0%" stopColor="#1a1a24" />
            <stop offset="100%" stopColor="#0a0a0f" />
          </radialGradient>
        </defs>

        <rect width="100%" height="100%" fill="url(#constellation-grid)" />

        {/* Orbital rings */}
        {[1, 0.7, 0.4].map((scale, i) => (
          <motion.circle
            key={i}
            cx={centerX}
            cy={centerY}
            r={radius * scale}
            fill="none"
            stroke="rgba(0, 240, 255, 0.1)"
            strokeWidth="1"
            strokeDasharray="5,5"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: i * 0.2 }}
          />
        ))}

        {/* Connection lines to sources */}
        {sources.map((source, index) => {
          const angle = (index / sources.length) * 2 * Math.PI - Math.PI / 2;
          const x = centerX + Math.cos(angle) * radius;
          const y = centerY + Math.sin(angle) * radius;
          const isSelected = selectedSource === source.id;

          return (
            <motion.line
              key={`line-${source.id}`}
              x1={centerX}
              y1={centerY}
              x2={x}
              y2={y}
              stroke={isSelected ? '#00f0ff' : 'rgba(0, 240, 255, 0.2)'}
              strokeWidth={isSelected ? 2 : 1}
              initial={{ pathLength: 0 }}
              animate={{ pathLength: 1 }}
              transition={{ delay: 0.5 + index * 0.1, duration: 0.5 }}
            />
          );
        })}

        {/* Data flow particles */}
        {sources
          .filter((s) => s.status === 'healthy')
          .map((source, index) => {
            const sourceIndex = sources.findIndex((s) => s.id === source.id);
            const angle = (sourceIndex / sources.length) * 2 * Math.PI - Math.PI / 2;
            const x = centerX + Math.cos(angle) * radius;
            const y = centerY + Math.sin(angle) * radius;

            return (
              <motion.circle
                key={`particle-${source.id}`}
                r={3}
                fill="#00f0ff"
                filter="url(#glow-filter)"
                initial={{ cx: x, cy: y }}
                animate={{
                  cx: [x, centerX],
                  cy: [y, centerY],
                  opacity: [1, 0],
                }}
                transition={{
                  duration: 2,
                  repeat: Infinity,
                  delay: index * 0.4,
                  ease: 'linear',
                }}
              />
            );
          })}

        {/* Center OMEN node */}
        <motion.g
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ delay: 0.3, type: 'spring' }}
        >
          <circle
            cx={centerX}
            cy={centerY}
            r={40}
            fill="url(#centerGradient)"
            stroke="#00f0ff"
            strokeWidth="2"
            filter="url(#glow-filter)"
          />
          <text
            x={centerX}
            y={centerY + 5}
            textAnchor="middle"
            fill="white"
            fontSize="14"
            fontFamily="Orbitron"
            fontWeight="bold"
          >
            OMEN
          </text>
        </motion.g>

        {/* Source nodes */}
        {sources.map((source, index) => {
          const angle = (index / sources.length) * 2 * Math.PI - Math.PI / 2;
          const x = centerX + Math.cos(angle) * radius;
          const y = centerY + Math.sin(angle) * radius;
          const color = STATUS_COLORS[source.status];
          const isSelected = selectedSource === source.id;

          return (
            <motion.g
              key={source.id}
              initial={{ opacity: 0, scale: 0 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.5 + index * 0.1 }}
              style={{ cursor: 'pointer' }}
              onClick={() => onSelectSource(source.id)}
            >
              {/* Pulse ring for active sources */}
              {source.status === 'healthy' && (
                <motion.circle
                  cx={x}
                  cy={y}
                  r={24}
                  fill="none"
                  stroke={color}
                  strokeWidth={1}
                  initial={{ scale: 0.7, opacity: 0.8 }}
                  animate={{
                    scale: [0.7, 1.1, 0.7],
                    opacity: [0.8, 0, 0.8],
                  }}
                  transition={{
                    duration: 2,
                    repeat: Infinity,
                    ease: 'easeInOut',
                  }}
                  style={{ transformOrigin: `${x}px ${y}px` }}
                />
              )}

              {/* Main node */}
              <circle
                cx={x}
                cy={y}
                r={isSelected ? 22 : 18}
                fill="#12121a"
                stroke={isSelected ? '#00f0ff' : color}
                strokeWidth={isSelected ? 3 : 2}
                style={{
                  filter: isSelected
                    ? 'drop-shadow(0 0 10px #00f0ff)'
                    : `drop-shadow(0 0 5px ${color})`,
                }}
              />

              {/* Status indicator */}
              <circle cx={x} cy={y} r={6} fill={color} />

              {/* Label */}
              <text
                x={x}
                y={y + 35}
                textAnchor="middle"
                fill="#a0a0b0"
                fontSize="10"
                fontFamily="JetBrains Mono"
              >
                {source.name}
              </text>

              {/* Latency */}
              <text
                x={x}
                y={y + 47}
                textAnchor="middle"
                fill="#6b7280"
                fontSize="9"
                fontFamily="Fira Code"
              >
                {source.type === 'mock' ? 'MOCK' : `${source.latency}ms`}
              </text>
            </motion.g>
          );
        })}
      </svg>
    </div>
  );
}
