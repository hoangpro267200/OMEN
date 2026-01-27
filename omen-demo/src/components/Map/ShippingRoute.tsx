import { motion } from 'framer-motion';
import type { AffectedRoute } from '../../types/omen';

interface ShippingRouteProps {
  route: AffectedRoute;
  index: number;
}

export function ShippingRoute({ route, index }: ShippingRouteProps) {
  const isBlocked = route.status === 'blocked';
  const isAlternative = route.status === 'alternative';

  return (
    <motion.div
      initial={{ opacity: 0, x: -12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.15 }}
      className={`
        flex items-center justify-between p-3 rounded-xl border
        ${isBlocked ? 'bg-red-500/10 border-red-500/30' : ''}
        ${isAlternative ? 'bg-amber-500/10 border-amber-500/30' : ''}
        ${!isBlocked && !isAlternative ? 'bg-white/5 border-white/10' : ''}
      `}
    >
      <div>
        <div className="font-medium text-white">{route.route_name}</div>
        <div className="text-sm text-zinc-500">
          {route.origin_region} → {route.destination_region}
        </div>
      </div>
      <div className="flex items-center gap-2">
        {isBlocked && (
          <span className="text-xs font-medium text-red-400 uppercase">
            Blocked
          </span>
        )}
        {isAlternative && (
          <span className="text-xs font-medium text-amber-400 uppercase">
            Alternative
          </span>
        )}
        <span className="text-xs text-zinc-500">
          {(route.impact_severity * 100).toFixed(0)}% impact
        </span>
      </div>
    </motion.div>
  );
}
