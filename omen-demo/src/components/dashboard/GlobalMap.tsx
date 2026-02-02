/**
 * GlobalMap - Neural Command Center world map visualization
 * Features: Chokepoint markers, shipping routes, pulsing signal indicators
 */
import { ComposableMap, Geographies, Geography, Marker, Line } from 'react-simple-maps';
import { motion } from 'framer-motion';

// Use Natural Earth 110m world map (reliable CDN)
const GEO_URL = 'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json';

// Strategic chokepoints data
interface Chokepoint {
  name: string;
  coordinates: [number, number];
  risk: 'high' | 'medium' | 'low';
  signals: number;
}

const CHOKEPOINTS: Chokepoint[] = [
  { name: 'Suez Canal', coordinates: [32.3, 30.5], risk: 'high', signals: 3 },
  { name: 'Strait of Hormuz', coordinates: [56.3, 26.5], risk: 'medium', signals: 1 },
  { name: 'Malacca Strait', coordinates: [100.5, 2.5], risk: 'low', signals: 0 },
  { name: 'Panama Canal', coordinates: [-79.5, 9.0], risk: 'medium', signals: 1 },
  { name: 'Bab el-Mandeb', coordinates: [43.3, 12.5], risk: 'high', signals: 2 },
  { name: 'Cape of Good Hope', coordinates: [18.5, -34.5], risk: 'low', signals: 0 },
  { name: 'Turkish Straits', coordinates: [29.0, 41.0], risk: 'low', signals: 0 },
  { name: 'Strait of Gibraltar', coordinates: [-5.5, 36.0], risk: 'low', signals: 0 },
];

// Shipping routes (simplified)
const ROUTES: { from: [number, number]; to: [number, number] }[] = [
  { from: [-74, 40.7], to: [32.3, 30.5] },    // NYC to Suez
  { from: [121.5, 31.2], to: [100.5, 2.5] },  // Shanghai to Malacca
  { from: [103.8, 1.3], to: [56.3, 26.5] },   // Singapore to Hormuz
  { from: [139.7, 35.7], to: [100.5, 2.5] },  // Tokyo to Malacca
  { from: [4.9, 52.4], to: [32.3, 30.5] },    // Rotterdam to Suez
  { from: [-122.4, 37.8], to: [-79.5, 9.0] }, // SF to Panama
];

const RISK_COLORS = {
  high: '#ff3366',
  medium: '#ffaa00',
  low: '#00ff88',
};

export interface GlobalMapProps {
  onChokepointClick?: (name: string) => void;
  className?: string;
}

export function GlobalMap({ onChokepointClick, className }: GlobalMapProps) {
  return (
    <div className={`relative w-full h-full min-h-[300px] ${className || ''}`}>
      <ComposableMap
        projection="geoMercator"
        projectionConfig={{
          scale: 130,
          center: [30, 20],
        }}
        style={{ width: '100%', height: '100%' }}
      >
        {/* Country shapes */}
        <Geographies geography={GEO_URL}>
          {({ geographies }) =>
            geographies.map((geo, index) => (
              <Geography
                key={(geo as { rsmKey?: string }).rsmKey || `geo-${index}`}
                geography={geo}
                fill="#1a1a24"
                stroke="#2a2a36"
                strokeWidth={0.5}
                style={{
                  default: { outline: 'none' },
                  hover: { outline: 'none', fill: '#22222e' },
                  pressed: { outline: 'none' },
                }}
              />
            ))
          }
        </Geographies>

        {/* Shipping Routes */}
        {ROUTES.map((route, i) => (
          <Line
            key={i}
            coordinates={[route.from, route.to]}
            stroke="rgba(0, 240, 255, 0.2)"
            strokeWidth={1}
            strokeLinecap="round"
            strokeDasharray="4,4"
          />
        ))}

        {/* Chokepoint Markers */}
        {CHOKEPOINTS.map(({ name, coordinates, risk, signals }) => (
          <Marker key={name} coordinates={coordinates}>
            <g 
              style={{ cursor: 'pointer' }}
              onClick={() => onChokepointClick?.(name)}
            >
              {/* Pulse ring for active signals */}
              {signals > 0 && (
                <motion.circle
                  r={20}
                  fill="none"
                  stroke={RISK_COLORS[risk]}
                  strokeWidth={1}
                  initial={{ scale: 0.5, opacity: 0.8 }}
                  animate={{
                    scale: [0.5, 1.2, 0.5],
                    opacity: [0.8, 0, 0.8],
                  }}
                  transition={{
                    duration: 2,
                    repeat: Infinity,
                    ease: 'easeInOut',
                  }}
                />
              )}

              {/* Main dot */}
              <circle
                r={8}
                fill={RISK_COLORS[risk]}
                stroke="#0a0a0f"
                strokeWidth={2}
                style={{
                  filter: `drop-shadow(0 0 8px ${RISK_COLORS[risk]})`,
                }}
              />

              {/* Signal count badge */}
              {signals > 0 && (
                <g transform="translate(10, -10)">
                  <circle r={10} fill="#0a0a0f" />
                  <circle r={9} fill={RISK_COLORS[risk]} />
                  <text
                    textAnchor="middle"
                    y={4}
                    fontSize={10}
                    fontWeight="bold"
                    fill="#0a0a0f"
                    fontFamily="Fira Code"
                  >
                    {signals}
                  </text>
                </g>
              )}

              {/* Label */}
              <text
                textAnchor="middle"
                y={24}
                fontSize={9}
                fill="#a0a0b0"
                fontFamily="JetBrains Mono"
              >
                {name}
              </text>
            </g>
          </Marker>
        ))}
      </ComposableMap>

      {/* Legend */}
      <div className="absolute bottom-4 right-4 bg-bg-primary/90 backdrop-blur rounded-lg p-3 text-xs border border-border-subtle">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-status-error" />
            <span className="text-text-muted">High Risk</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-status-warning" />
            <span className="text-text-muted">Moderate</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-status-success" />
            <span className="text-text-muted">Normal</span>
          </div>
        </div>
      </div>
    </div>
  );
}
