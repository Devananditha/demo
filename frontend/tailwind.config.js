/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        beige: {
          50: '#faf8f5',
          100: '#f5f2ea',
          200: '#ebe5d8',
          300: '#ded5c2',
          400: '#cfc2a8',
          500: '#bfae8e',
          600: '#a89472',
          700: '#8c7a5c',
          800: '#73644d',
          900: '#5e523f',
        },
        brand: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
          950: '#0f172a',
        },
        surface: {
          DEFAULT: '#ffffff',
          beige: '#f5f2ea',
          card: '#ffffff',
          inset: '#f0ebdf',
          border: '#e5dfd5',
          subtle: '#ebe5d8',
        }
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      boxShadow: {
        xs: '0 1px 2px 0 rgba(0, 0, 0, 0.04)',
        card: '0 1px 3px 0 rgba(60, 50, 30, 0.05), 0 1px 2px 0 rgba(60, 50, 30, 0.03)',
      }
    },
  },
  plugins: [],
}
