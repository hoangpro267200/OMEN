/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        /* Neural Command Center — Deep Space Theme */
        'bg-primary': 'var(--bg-primary)',
        'bg-secondary': 'var(--bg-secondary)',
        'bg-tertiary': 'var(--bg-tertiary)',
        'bg-elevated': 'var(--bg-elevated)',

        /* Borders */
        'border-subtle': 'var(--border-subtle)',
        'border-active': 'var(--border-active)',
        'border-focus': 'var(--border-focus)',

        /* Text */
        'text-primary': 'var(--text-primary)',
        'text-secondary': 'var(--text-secondary)',
        'text-muted': 'var(--text-muted)',

        /* Accent colors */
        'accent-cyan': 'var(--accent-cyan)',
        'accent-amber': 'var(--accent-amber)',

        /* Status colors */
        'status-success': 'var(--status-success)',
        'status-warning': 'var(--status-warning)',
        'status-error': 'var(--status-error)',
        'status-info': 'var(--status-info)',

        /* Legacy status (compatibility) */
        'status-sealed': 'var(--status-sealed)',
        'status-open': 'var(--status-open)',
        'status-late': 'var(--status-late)',
        'status-failed': 'var(--status-failed)',
        'status-completed': 'var(--status-completed)',
        'status-partial': 'var(--status-partial)',
        
        /* Legacy accent (compatibility) */
        'accent-blue': 'var(--accent-cyan)',
        'accent-green': 'var(--status-success)',
        'accent-red': 'var(--status-error)',
      },
      fontFamily: {
        display: ['"Orbitron"', 'sans-serif'],
        heading: ['"JetBrains Mono"', 'monospace'],
        body: ['"Outfit"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['"Fira Code"', 'ui-monospace', 'monospace'],
      },
      spacing: {
        '1': '4px',
        '2': '8px',
        '3': '12px',
        '4': '16px',
        '5': '20px',
        '6': '24px',
        '8': '32px',
        '10': '40px',
        '12': '48px',
        '16': '64px',
        '24': '96px',
      },
      borderRadius: {
        'sm': '4px',
        'md': '6px',
        'lg': '8px',
        'xl': '12px',
        '2xl': '16px',
        'card': '12px',
        'button': '8px',
        'badge': '4px',
      },
      boxShadow: {
        'glow-cyan': '0 0 20px rgba(0, 240, 255, 0.3)',
        'glow-amber': '0 0 20px rgba(255, 170, 0, 0.3)',
        'glow-success': '0 0 20px rgba(0, 255, 136, 0.3)',
        'glow-error': '0 0 20px rgba(255, 51, 102, 0.3)',
        'elevated': '0 4px 20px rgba(0, 0, 0, 0.5)',
        'card': '0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -2px rgba(0, 0, 0, 0.2)',
      },
      animation: {
        'pulse-glow': 'pulse-glow 2s ease-in-out infinite',
        'glow': 'glow 1.5s ease-in-out infinite alternate',
        'slide-up': 'slide-up 0.3s ease-out forwards',
        'fade-in': 'fade-in 0.2s ease-out forwards',
        'shimmer': 'shimmer 1.5s infinite',
        'flow': 'flow 3s linear infinite',
        'spin-slow': 'spin 3s linear infinite',
      },
      keyframes: {
        'pulse-glow': {
          '0%, 100%': { boxShadow: '0 0 0 0 rgba(0, 240, 255, 0.4)' },
          '50%': { boxShadow: '0 0 0 10px rgba(0, 240, 255, 0)' },
        },
        'glow': {
          'from': { boxShadow: '0 0 5px var(--glow-color, rgba(0, 240, 255, 0.3))' },
          'to': { boxShadow: '0 0 20px var(--glow-color, rgba(0, 240, 255, 0.3)), 0 0 30px var(--glow-color, rgba(0, 240, 255, 0.3))' },
        },
        'slide-up': {
          'from': { opacity: '0', transform: 'translateY(20px)' },
          'to': { opacity: '1', transform: 'translateY(0)' },
        },
        'fade-in': {
          'from': { opacity: '0' },
          'to': { opacity: '1' },
        },
        'shimmer': {
          '0%': { backgroundPosition: '200% 0' },
          '100%': { backgroundPosition: '-200% 0' },
        },
        'flow': {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(100%)' },
        },
      },
      backdropBlur: {
        'xs': '2px',
      },
    },
  },
  plugins: [],
};
