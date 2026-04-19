/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        surface:  '#f5f5f5',
        canvas:   '#ffffff',
        border:   '#e0e0e0',
        muted:    '#999999',
        dim:      '#666666',
        ink:      '#111111',
        black:    '#000000',
      },
      fontFamily: {
        sans: ['"IBM Plex Sans"', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'monospace'],
      },
      fontWeight: {
        light:   '300',
        normal:  '400',
        medium:  '500',
        bold:    '700',
      },
      borderRadius: {
        DEFAULT: '2px',
        sm:      '2px',
        md:      '4px',
        lg:      '4px',
        xl:      '4px',
        '2xl':   '4px',
        full:    '2px',
      },
      transitionTimingFunction: {
        'design': 'cubic-bezier(0.4, 0, 0.2, 1)',
      },
      transitionDuration: {
        'fast': '150ms',
        'base': '200ms',
        'slow': '350ms',
      },
      animation: {
        'scan':    'scan 1.4s ease-in-out infinite',
        'ticker':  'ticker 150ms ease-in-out',
        'slide-in':'slide-in 300ms cubic-bezier(0.4, 0, 0.2, 1)',
        'fade-in': 'fade-in 200ms ease-in-out',
        'scale-in':'scale-in 200ms cubic-bezier(0.4, 0, 0.2, 1)',
      },
      keyframes: {
        scan: {
          '0%':   { transform: 'translateX(-100%)', opacity: '1' },
          '100%': { transform: 'translateX(400%)',  opacity: '0' },
        },
        ticker: {
          '0%':   { transform: 'translateY(-8px)', opacity: '0' },
          '100%': { transform: 'translateY(0)',    opacity: '1' },
        },
        'slide-in': {
          '0%':   { transform: 'translateX(-4px)', opacity: '0' },
          '100%': { transform: 'translateX(0)',    opacity: '1' },
        },
        'fade-in': {
          '0%':   { opacity: '0' },
          '100%': { opacity: '1' },
        },
        'scale-in': {
          '0%':   { transform: 'scale(0.97)', opacity: '0' },
          '100%': { transform: 'scale(1)',    opacity: '1' },
        },
      },
      spacing: {
        '18': '72px',
        '22': '88px',
      },
    },
  },
  plugins: [],
}
