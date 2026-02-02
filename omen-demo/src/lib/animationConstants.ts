/**
 * Animation constants — durations (ms), easings. Use for Framer Motion and CSS.
 * Keep durations under 300ms for responsive feel. Respect prefers-reduced-motion.
 */

export const DURATION = {
  /** Page / route transition */
  page: 150,
  /** Panel / drawer slide */
  panel: 250,
  /** Backdrop fade */
  backdrop: 200,
  /** Sidebar expand/collapse */
  sidebar: 200,
  /** Button hover/click */
  button: 100,
  /** Table row hover */
  rowHover: 100,
  /** Counter pop / flash */
  pop: 200,
  /** Stagger step between siblings */
  stagger: 50,
  /** Progress bar fill */
  progress: 400,
  /** Success checkmark bounce */
  bounce: 350,
} as const;

export const EASING = {
  /** Default ease-out for most animations */
  easeOut: [0.33, 1, 0.68, 1] as const,
  /** Snappy for micro-interactions */
  snap: [0.25, 0.46, 0.45, 0.94] as const,
  /** Bounce for success states */
  bounce: [0.34, 1.56, 0.64, 1] as const,
  /** Linear for progress */
  linear: [0, 0, 1, 1] as const,
} as const;

/** Framer Motion transition presets */
export const TRANSITION = {
  page: { duration: DURATION.page / 1000, ease: EASING.easeOut },
  panel: { duration: DURATION.panel / 1000, ease: EASING.easeOut },
  pop: { type: 'spring' as const, stiffness: 400, damping: 25 },
  bounce: { type: 'spring' as const, stiffness: 300, damping: 15 },
} as const;
