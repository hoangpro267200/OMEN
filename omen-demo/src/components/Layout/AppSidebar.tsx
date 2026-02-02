import { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  LayoutDashboard,
  Database,
  Radio,
  Send,
  FileCode,
  type LucideIcon,
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { ROUTES, ROUTE_LABELS, type RouteId } from '../../lib/routes';
import { preloadRoutes } from '../../lib/preloadRoutes';

const COLLAPSED_WIDTH = 64;
const EXPANDED_WIDTH = 240;
const TRANSITION_MS = 200;

const NAV_ITEMS: { id: RouteId; path: string; label: string; Icon: LucideIcon }[] = [
  { id: 'overview', path: ROUTES.overview, label: ROUTE_LABELS.overview, Icon: LayoutDashboard },
  { id: 'partitions', path: ROUTES.partitions, label: ROUTE_LABELS.partitions, Icon: Database },
  { id: 'signals', path: ROUTES.signals, label: ROUTE_LABELS.signals, Icon: Radio },
  { id: 'ingestDemo', path: ROUTES.ingestDemo, label: ROUTE_LABELS.ingestDemo, Icon: Send },
  { id: 'ledgerProof', path: ROUTES.ledgerProof, label: ROUTE_LABELS.ledgerProof, Icon: FileCode },
];

export interface AppSidebarProps {
  /** Mobile: sidebar drawer open */
  mobileOpen?: boolean;
  /** Mobile: close drawer (e.g. backdrop or after nav) */
  onMobileClose?: () => void;
}

export function AppSidebar({ mobileOpen = false, onMobileClose }: AppSidebarProps) {
  const [isHovered, setIsHovered] = useState(false);
  const isExpanded = isHovered || mobileOpen;
  const width = isExpanded ? EXPANDED_WIDTH : COLLAPSED_WIDTH;

  return (
    <>
      {/* Mobile backdrop */}
      {mobileOpen && (
        <button
          type="button"
          aria-label="Close menu"
          onClick={onMobileClose}
          className="fixed inset-0 z-30 bg-black/50 md:hidden"
        />
      )}

      <motion.aside
        initial={false}
        animate={{ width }}
        transition={{ duration: TRANSITION_MS / 1000, ease: 'easeOut' }}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        className={cn(
          'fixed left-0 top-14 z-40 flex h-[calc(100vh-56px)] flex-col border-r border-[var(--border-subtle)] bg-[var(--bg-secondary)] shrink-0 overflow-hidden',
          'transition-transform duration-200 ease-out md:!translate-x-0',
          mobileOpen ? 'translate-x-0' : '-translate-x-full'
        )}
        style={{ width }}
      >
      <nav className="flex flex-1 flex-col gap-0.5 p-2" aria-label="Main navigation">
        {NAV_ITEMS.map(({ id, path, label, Icon }) => (
          <NavLink
            key={id}
            to={path}
            end={path === ROUTES.overview}
            onMouseEnter={() => preloadRoutes[id]?.()}
            onFocus={() => preloadRoutes[id]?.()}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 rounded-[var(--radius-button)] px-3 py-2.5 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-[var(--bg-tertiary)] text-[var(--text-primary)] border-l-2 border-[var(--accent-blue)] ml-0 -ml-[2px] pl-[14px]'
                  : 'text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)]/50 hover:text-[var(--text-primary)]'
              )
            }
          >
            {({ isActive }) => (
              <>
                <span
                  className={cn(
                    'flex h-9 w-9 shrink-0 items-center justify-center rounded-[var(--radius-button)] transition-colors',
                    isActive && 'bg-[var(--accent-blue)]/15 text-[var(--accent-blue)]'
                  )}
                >
                  <Icon className="h-5 w-5" aria-hidden strokeWidth={2} />
                </span>
                <motion.span
                  initial={false}
                  animate={{
                    opacity: isExpanded ? 1 : 0,
                    width: isExpanded ? 'auto' : 0,
                    overflow: 'hidden',
                  }}
                  transition={{ duration: TRANSITION_MS / 1000, ease: 'easeOut' }}
                  className="whitespace-nowrap font-mono"
                >
                  {label}
                </motion.span>
              </>
            )}
          </NavLink>
        ))}
      </nav>
    </motion.aside>
    </>
  );
}

export { COLLAPSED_WIDTH, EXPANDED_WIDTH };
