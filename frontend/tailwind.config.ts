import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        void: '#060914',
        panel: '#0D1330',
        'panel-2': '#141C45',
        line: '#26306A',
        ink: '#E8ECFF',
        'ink-muted': '#8D97C4',
        plasma: '#7C5CFF',
        'plasma-soft': '#A99BFF',
        ion: '#2DE2E6',
        flare: '#FF4D8D',
        ok: '#3DF5A7',
        warn: '#FFC857',
      },
      borderRadius: {
        field: '8px',
        panel: '16px',
        pill: '999px',
      },
      fontFamily: {
        sora: ['var(--font-sora)'],
        manrope: ['var(--font-manrope)'],
        mono: ['var(--font-jetbrains-mono)'],
      },
      animation: {
        spin: 'spin 3s linear infinite',
      },
    },
  },
  plugins: [],
}

export default config
