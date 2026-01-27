import { useMemo } from 'react';
import {
  ComposableMap,
  Geographies,
  Geography,
  Line,
  Marker,
  ZoomableGroup,
} from 'react-simple-maps';
import { motion } from 'framer-motion';
import { Card } from '../common/Card';
import type { ProcessedRoute, Chokepoint } from '../../types/omen';
import { cn } from '../../lib/utils';

const TOPOLOGY_URL = 'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json';

interface WorldMapProps {
  routes: ProcessedRoute[];
  chokepoints: Chokepoint[];
  className?: string;
}

const routeStatusColor: Record<string, string> = {
  BLOCKED: 'var(--danger)',
  DELAYED: 'var(--warning)',
  ALTERNATIVE: 'var(--success)',
  NORMAL: 'var(--success)',
};

function routeToCoords(route: ProcessedRoute): [number, number][] {
  const points = [
    route.origin,
    ...route.waypoints,
    route.destination,
  ];
  return points.map((p) => [p.lng, p.lat] as [number, number]);
}

export function WorldMap({ routes, chokepoints, className }: WorldMapProps) {
  const routeCoords = useMemo(
    () => routes.map((r) => ({ route: r, coords: routeToCoords(r) })),
    [routes]
  );

  return (
    <Card className={cn('p-6', className)} hover={false}>
      <div className="flex items-center justify-between mb-4">
        <span className="text-xs font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">
          Bản đồ tuyến đường và điểm nghẽn
        </span>
        <div className="flex items-center gap-4 text-xs text-[var(--text-muted)]">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-[var(--danger)]" /> Bị chặn
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-[var(--warning)]" /> Bị trì hoãn
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-[var(--success)]" /> Thay thế
          </span>
        </div>
      </div>
      <div
        className="relative w-full overflow-hidden rounded-lg border border-[var(--border-subtle)]"
        style={{ background: 'var(--bg-base)', minHeight: 400 }}
      >
        <ComposableMap
          projection="geoMercator"
          projectionConfig={{
            scale: 140,
            center: [20, 20],
          }}
          style={{ width: '100%', height: 'auto', minHeight: 400 }}
        >
          <ZoomableGroup center={[20, 20]} zoom={1}>
            <Geographies geography={TOPOLOGY_URL}>
              {({ geographies }) =>
                geographies.map((geo: object & { rsmKey?: string }, i: number) => (
                  <Geography
                    key={(geo as { rsmKey?: string }).rsmKey ?? `geo-${i}`}
                    geography={geo}
                    fill="var(--bg-elevated)"
                    stroke="var(--border-subtle)"
                    strokeWidth={0.5}
                    style={{
                      default: { outline: 'none' },
                      hover: { fill: 'var(--bg-hover)', outline: 'none' },
                      pressed: { outline: 'none' },
                    }}
                  />
                ))
              }
            </Geographies>

            {routeCoords.map(({ route, coords }) => {
              if (coords.length < 2) return null;
              const color = routeStatusColor[route.status] ?? 'var(--text-muted)';
              const isBlocked = route.status === 'BLOCKED';
              return (
                <Line
                  key={route.route_id}
                  coordinates={coords}
                  stroke={color}
                  strokeWidth={1.5}
                  strokeLinecap="round"
                  strokeDasharray={isBlocked ? '6 4' : route.status === 'DELAYED' ? '4 4' : undefined}
                />
              );
            })}

            {chokepoints.map((cp, i) => {
              const isCritical = cp.risk_level === 'CRITICAL';
              const fill =
                cp.risk_level === 'CRITICAL'
                  ? 'var(--danger)'
                  : cp.risk_level === 'HIGH'
                    ? 'var(--warning)'
                    : 'var(--severity-medium)';
              return (
                <Marker key={`${cp.name}-${i}`} coordinates={[cp.lng, cp.lat]}>
                  <g>
                    {isCritical && (
                      <motion.circle
                        r={12}
                        fill="none"
                        stroke="var(--danger)"
                        strokeWidth={2}
                        style={{ opacity: 0.5 }}
                        initial={{ opacity: 0.5, scale: 1 }}
                        animate={{ opacity: 0, scale: 1.8 }}
                        transition={{ duration: 1.5, repeat: Infinity }}
                      />
                    )}
                    <motion.circle
                      r={isCritical ? 6 : 4}
                      fill={fill}
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ type: 'spring', delay: i * 0.05 }}
                    />
                  </g>
                  <title>
                    {cp.name} — {cp.risk_level}
                  </title>
                </Marker>
              );
            })}
          </ZoomableGroup>
        </ComposableMap>
      </div>
    </Card>
  );
}
