/**
 * AppSidebar - Neural Command Center navigation rail
 * Features: Icon-only navigation, glow effects, active state indicators
 */
import { NavLink } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Command,
  Radar,
  GitBranch,
  Database,
  FileText,
  Settings,
  Shield,
  type LucideIcon,
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { ROUTES, type RouteId } from '../../lib/routes';
import { preloadRoutes } from '../../lib/preloadRoutes';

const COLLAPSED_WIDTH = 64;
const EXPANDED_WIDTH = 240;

// Navigation items with Neural Command Center icons
const NAV_ITEMS: { id: RouteId; path: string; label: string; Icon: LucideIcon }[] = [
  { id: 'overview', path: ROUTES.overview, label: 'Command Center', Icon: Command },
  { id: 'signals', path: ROUTES.signals, label: 'Signal Monitor', Icon: Radar },
  { id: 'pipeline', path: ROUTES.pipeline, label: 'Pipeline', Icon: GitBranch },
  { id: 'sources', path: ROUTES.sources, label: 'Data Sources', Icon: Database },
  { id: 'operations', path: ROUTES.operations, label: 'Operations', Icon: Shield },
  { id: 'ledgerProof', path: ROUTES.ledgerProof, label: 'Ledger', Icon: FileText },
];

export interface AppSidebarProps {
  /** Mobile: sidebar drawer open */
  mobileOpen?: boolean;
  /** Mobile: close drawer (e.g. backdrop or after nav) */
  onMobileClose?: () => void;
}

export function AppSidebar({ mobileOpen = false, onMobileClose }: AppSidebarProps) {
  return (
    <>
      {/* Mobile backdrop */}
      {mobileOpen && (
        <button
          type="button"
          aria-label="Close menu"
          onClick={onMobileClose}
          className="fixed inset-0 z-30 bg-black/60 backdrop-blur-sm md:hidden"
        />
      )}

      <aside
        className={cn(
          'fixed left-0 top-14 z-40 flex h-[calc(100vh-56px)] flex-col',
          'w-16 border-r border-border-subtle bg-bg-secondary shrink-0',
          'transition-transform duration-200 ease-out md:!translate-x-0',
          mobileOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        {/* Main navigation */}
        <nav className="flex flex-1 flex-col items-center gap-1 py-3 px-2" aria-label="Main navigation">
          {NAV_ITEMS.map(({ id, path, label, Icon }) => (
            <NavLink
              key={id}
              to={path}
              end={path === ROUTES.overview}
              onMouseEnter={() => preloadRoutes[id]?.()}
              onFocus={() => preloadRoutes[id]?.()}
              data-tour={id === 'pipeline' ? 'pipeline' : undefined}
              className={({ isActive }) =>
                cn(
                  'relative w-12 h-12 flex items-center justify-center rounded-xl transition-all duration-200 group',
                  isActive
                    ? 'bg-accent-cyan/20 text-accent-cyan shadow-glow-cyan'
                    : 'text-text-muted hover:bg-bg-tertiary hover:text-text-primary'
                )
              }
            >
              {({ isActive }) => (
                <>
                  <Icon className="w-5 h-5" aria-hidden strokeWidth={2} />
                  
                  {/* Tooltip */}
                  <span className="absolute left-full ml-3 px-2 py-1 rounded-md bg-bg-elevated text-text-primary text-xs font-mono whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50 shadow-elevated border border-border-subtle">
                    {label}
                  </span>
                  
                  {/* Active indicator line */}
                  {isActive && (
                    <motion.span
                      layoutId="nav-indicator"
                      className="absolute right-0 w-0.5 h-6 bg-accent-cyan rounded-l"
                      transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                    />
                  )}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Bottom section - Settings */}
        <div className="flex flex-col items-center pb-3 px-2 border-t border-border-subtle pt-3">
          <button
            className="w-12 h-12 flex items-center justify-center rounded-xl text-text-muted hover:bg-bg-tertiary hover:text-text-primary transition-colors group relative"
            aria-label="Settings"
          >
            <Settings className="w-5 h-5" />
            <span className="absolute left-full ml-3 px-2 py-1 rounded-md bg-bg-elevated text-text-primary text-xs font-mono whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50 shadow-elevated border border-border-subtle">
              Settings
            </span>
          </button>
        </div>
      </aside>
    </>
  );
}

export { COLLAPSED_WIDTH, EXPANDED_WIDTH };
