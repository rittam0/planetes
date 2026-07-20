/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        space: {
          DEFAULT: '#07090d',
          light: '#101319',
          lighter: '#181b21',
        },
        panel: '#0d1015',
        earth: {
          dark: '#1E3A5F',
          DEFAULT: '#4A90D9',
          glow: '#87CEEB',
        },
        satellite: '#a39f96',
        debris: '#8a372e',
        rocket: '#8a7867',
        bone: '#d2c6ae',
        amber: {
          DEFAULT: '#FFAA00',
          dim: 'rgba(255, 170, 0, 0.3)',
        },
        text: {
          DEFAULT: '#E8E8E8',
          muted: '#888899',
          dim: '#555566',
        }
      },
      fontFamily: {
        display: ['Space Grotesk', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
        body: ['Inter', 'sans-serif'],
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-out',
        'slide-in-right': 'slideInRight 0.3s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideInRight: {
          '0%': { transform: 'translateX(100%)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}
