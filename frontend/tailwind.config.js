/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        void:    '#09080A',
        card:    '#100809',
        elevated:'#160B0B',
        muted:   '#1A0D0D',
        border:  '#261414',
        fg:      '#EEE0E0',
        'fg-muted': '#886868',
        'fg-dim':   '#584444',
        'neon-green':  '#CC0000',
        'neon-cyan':   '#FFAA33',
        'neon-violet': '#F04343',
        'neon-magenta':'#F04343',
        'neon-red':    '#FF2020',
        'neon-yellow': '#F5C842',
        'neon-orange': '#FF5522',
      },
      fontFamily: {
        display: ['Orbitron', 'sans-serif'],
        mono:    ['JetBrains Mono', 'monospace'],
      },
      boxShadow: {
        'neon-green':  '0 0 5px #CC0000, 0 0 14px rgba(204,0,0,0.25)',
        'neon-cyan':   '0 0 5px #FFAA33, 0 0 14px rgba(255,170,51,0.25)',
        'neon-violet': '0 0 5px #F04343, 0 0 14px rgba(240,67,67,0.25)',
        'neon-red':    '0 0 5px #FF2020, 0 0 14px rgba(255,32,32,0.25)',
      },
      animation: {
        'neon-pulse':  'neon-pulse 2.5s ease-in-out infinite',
        'radar-sweep': 'radar-sweep 4s linear infinite',
        'cyber-in':    'cyber-in 0.35s ease-out forwards',
        'fade-up':     'fade-up 0.3s ease-out forwards',
      },
      keyframes: {
        'neon-pulse': {
          '0%,100%': { opacity: '1' },
          '50%':     { opacity: '0.5' },
        },
        'radar-sweep': {
          '0%':   { transform: 'rotate(0deg)' },
          '100%': { transform: 'rotate(360deg)' },
        },
        'cyber-in': {
          '0%':   { opacity: '0', transform: 'translateY(12px) scale(0.98)' },
          '100%': { opacity: '1', transform: 'translateY(0) scale(1)' },
        },
        'fade-up': {
          '0%':   { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
}
