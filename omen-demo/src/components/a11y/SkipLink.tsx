/**
 * Skip Link
 *
 * Allows keyboard users to skip to main content.
 */

export function SkipLink() {
  return (
    <a
      href="#main-content"
      className="absolute -left-[9999px] top-4 z-[100] px-4 py-2 rounded-[var(--radius-button)] font-medium text-white bg-[var(--accent-blue)] outline-none transition-[left] focus:left-4 focus:fixed focus:top-4"
    >
      Skip to main content
    </a>
  )
}
