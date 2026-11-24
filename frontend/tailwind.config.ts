import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        'grafito-oscuro': '#0B0C10',
        grafito: '#1C1F26',
        'grafito-claro': '#2A2F38',
        borde: '#3A3F46',
        texto: '#E8ECF0',
        'texto-secundario': '#8D97A8',
        cobalto: '#2563EB',
        'cobalto-suave': '#3B82F6',
        exito: '#059669',
        alerta: '#D97706',
        error: '#DC2626',
      },
      borderRadius: {
        campo: '8px',
        panel: '12px',
        pill: '999px',
      },
      fontFamily: {
        sans: ['var(--font-ibm-plex-sans)', 'system-ui', 'sans-serif'],
        mono: ['var(--font-ibm-plex-mono)', 'monospace'],
      },
      animation: {
        spin: 'spin 3s linear infinite',
      },
    },
  },
  plugins: [],
}

export default config
