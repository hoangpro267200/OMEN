import { motion } from 'framer-motion';
import { MapPin } from 'lucide-react';
import { Card } from '../common/Card';
import { ShippingRoute } from './ShippingRoute';
import type { AffectedRoute } from '../../types/omen';

interface RouteMapProps {
  routes: AffectedRoute[];
}

export function RouteMap({ routes }: RouteMapProps) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="mb-12"
    >
      <h2 className="text-xl font-semibold text-white mb-6 flex items-center gap-2">
        <span className="w-1 h-6 bg-blue-500 rounded-full" />
        Affected routes
      </h2>
      <Card className="p-6">
        <div className="flex items-center gap-2 text-zinc-500 text-sm mb-4">
          <MapPin className="w-4 h-4" />
          <span>Shipping corridors</span>
        </div>
        <div className="space-y-3">
          {routes.map((r, i) => (
            <ShippingRoute key={r.route_id} route={r} index={i} />
          ))}
        </div>
        <div className="mt-4 pt-4 border-t border-white/10 flex gap-6 text-xs text-zinc-500">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-red-500/60" /> Blocked
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-amber-500/60" /> Alternative
          </span>
        </div>
      </Card>
    </motion.section>
  );
}
