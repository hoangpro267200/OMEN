import { useEffect, useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { AnimatePresence } from 'framer-motion';
import { ShellHeader, HEADER_HEIGHT } from './ShellHeader';
import { AppSidebar } from './AppSidebar';
import { SceneStepper } from './SceneStepper';
import { FallbackMode } from './FallbackMode';
import { OfflineBanner } from '../ui/OfflineBanner';
import { SkipLink } from '../a11y/SkipLink';
import { AnimatedPage } from '../animations/AnimatedPage';
import { useDemoModeContext } from '../../context/DemoModeContext';
import { useKeyboardShortcuts } from '../../hooks/useKeyboardShortcuts';
import { getSceneIndexForPath } from '../../lib/demoScenes';
import { cn } from '../../lib/utils';

export interface AppShellProps {
  /** Show global search in header (hidden when demo mode) */
  showSearch?: boolean;
  className?: string;
}

/**
 * Application shell: fixed Header (56px) + Sidebar (64/240px) + scrollable main.
 */
export function AppShell({ showSearch = true, className = '' }: AppShellProps) {
  const location = useLocation();
  const { isDemoMode, setCurrentScene } = useDemoModeContext();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useKeyboardShortcuts();

  // Sync demo scene index when route changes (e.g. sidebar navigation)
  useEffect(() => {
    const index = getSceneIndexForPath(location.pathname);
    setCurrentScene(index);
  }, [location.pathname, setCurrentScene]);

  return (
    <div className={cn('flex h-full min-h-screen flex-col bg-[var(--bg-primary)]', className)}>
      <SkipLink />
      <OfflineBanner />
      <ShellHeader showSearch={showSearch} onMobileMenuToggle={() => setMobileMenuOpen((v) => !v)} />

      <div className="flex flex-1 min-h-0 pt-14">
        <AppSidebar mobileOpen={mobileMenuOpen} onMobileClose={() => setMobileMenuOpen(false)} />

        <main id="main-content" tabIndex={-1} className="flex-1 min-w-0 overflow-auto overflow-thin-scroll transition-[margin] duration-200 ease-out md:ml-16">
          <AnimatePresence mode="wait">
            <AnimatedPage key={location.pathname}>
              <Outlet />
            </AnimatedPage>
          </AnimatePresence>
        </main>
      </div>

      {isDemoMode && <SceneStepper />}
      <FallbackMode show={false} />
    </div>
  );
}

export { HEADER_HEIGHT };
