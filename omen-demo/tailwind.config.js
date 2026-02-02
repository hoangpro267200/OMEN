/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        /* Mission Control — use with bg-*, text-*, border-* */
        'bg-primary': 'var(--bg-primary)',
        'bg-secondary': 'var(--bg-secondary)',
        'bg-tertiary': 'var(--bg-tertiary)',
        'border-subtle': 'var(--border-subtle)',
        'border-active': 'var(--border-active)',
        'text-primary': 'var(--text-primary)',
        'text-secondary': 'var(--text-secondary)',
        'text-muted': 'var(--text-muted)',
        'accent-blue': 'var(--accent-blue)',
        'accent-green': 'var(--accent-green)',
        'accent-amber': 'var(--accent-amber)',
        'accent-red': 'var(--accent-red)',
        'status-sealed': 'var(--status-sealed)',
        'status-open': 'var(--status-open)',
        'status-late': 'var(--status-late)',
        'status-failed': 'var(--status-failed)',
        'status-completed': 'var(--status-completed)',
        'status-partial': 'var(--status-partial)',
      },
      fontFamily: {
        display: ['"JetBrains Mono"', '"IBM Plex Mono"', 'ui-monospace', 'monospace'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
        body: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      spacing: {
        '1': '4px',
        '2': '8px',
        '3': '12px',
        '4': '16px',
        '6': '24px',
        '8': '32px',
        '12': '48px',
        '16': '64px',
        '24': '96px',
      },
      borderRadius: {
        card: '8px',
        button: '6px',
        badge: '4px',
      },
    },
  },
  plugins: [],
};
