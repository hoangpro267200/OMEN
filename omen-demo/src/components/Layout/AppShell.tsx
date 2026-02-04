/**
 * AppShell - Neural Command Center main layout
 * Features: Fixed header, icon navigation rail, main content area, status bar, command palette, demo tour
 */
import { useEffect, useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { AnimatePresence } from 'framer-motion';
import { ShellHeader, HEADER_HEIGHT } from './ShellHeader';
import { AppSidebar } from './AppSidebar';
import { StatusBar } from './StatusBar';
import { SceneStepper } from './SceneStepper';
import { FallbackMode } from './FallbackMode';
import { OfflineBanner } from '../ui/OfflineBanner';
import { SkipLink } from '../a11y/SkipLink';
import { AnimatedPage } from '../animations/AnimatedPage';
import { CommandPalette, useCommandPalette } from '../command-palette';
import { DemoTour, useDemoTour } from '../tour';
import { useDemoModeContext } from '../../context/DemoModeContext';
import { useKeyboardShortcuts } from '../../hooks/useKeyboardShortcuts';
import { getSceneIndexForPath } from '../../lib/demoScenes';
import { cn } from '../../lib/utils';

export interface AppShellProps {
  /** Show global search in header (hidden when demo mode) */
  showSearch?: boolean;
  /** Show bottom status bar */
  showStatusBar?: boolean;
  className?: string;
}

/**
 * Neural Command Center Application Shell
 * Layout: Header (56px) + Sidebar (64px) + Main Content + Status Bar (32px)
 */
export function AppShell({ 
  showSearch = true, 
  showStatusBar = true,
  className = '' 
}: AppShellProps) {
  const location = useLocation();
  const { isDemoMode, setCurrentScene } = useDemoModeContext();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  
  // Command Palette (Cmd+K)
  const { isOpen: commandPaletteOpen, setIsOpen: setCommandPaletteOpen } = useCommandPalette();
  
  // Demo Tour
  const { isActive: tourActive, closeTour, completeTour, startTour, hasSeenTour } = useDemoTour();

  useKeyboardShortcuts();
  
  // Auto-start tour disabled for now - users can click "Tour" button manually
  // useEffect(() => {
  //   if (!hasSeenTour && location.pathname === '/') {
  //     const timer = setTimeout(() => startTour(), 1500);
  //     return () => clearTimeout(timer);
  //   }
  // }, [hasSeenTour, location.pathname, startTour]);

  // Sync demo scene index when route changes (e.g. sidebar navigation)
  useEffect(() => {
    const index = getSceneIndexForPath(location.pathname);
    setCurrentScene(index);
  }, [location.pathname, setCurrentScene]);

  return (
    <div className={cn('flex h-full min-h-screen flex-col bg-bg-primary', className)}>
      <SkipLink />
      <OfflineBanner />
      
      {/* Command Palette (Cmd+K) */}
      <CommandPalette 
        isOpen={commandPaletteOpen} 
        onClose={() => setCommandPaletteOpen(false)} 
      />
      
      {/* Demo Tour (for investor presentations) */}
      <DemoTour
        isActive={tourActive}
        onClose={closeTour}
        onComplete={completeTour}
      />
      
      {/* Fixed Header */}
      <ShellHeader 
        showSearch={showSearch} 
        onMobileMenuToggle={() => setMobileMenuOpen((v) => !v)} 
      />

      {/* Main layout below header */}
      <div className="flex flex-1 min-h-0 pt-14">
        {/* Sidebar Navigation Rail */}
        <AppSidebar 
          mobileOpen={mobileMenuOpen} 
          onMobileClose={() => setMobileMenuOpen(false)} 
        />

        {/* Main Content Area */}
        <main 
          id="main-content" 
          tabIndex={-1} 
          className={cn(
            'flex-1 min-w-0 overflow-auto overflow-thin-scroll',
            'transition-[margin] duration-200 ease-out',
            'md:ml-16', // Sidebar width
            showStatusBar && 'pb-8' // Status bar height
          )}
        >
          <AnimatePresence mode="wait">
            <AnimatedPage key={location.pathname}>
              <Outlet />
            </AnimatedPage>
          </AnimatePresence>
        </main>
      </div>

      {/* Bottom Status Bar */}
      {showStatusBar && <StatusBar />}

      {/* Demo Mode Stepper (for presentations) */}
      {isDemoMode && <SceneStepper />}
      
      <FallbackMode show={false} />
    </div>
  );
}

export { HEADER_HEIGHT };
