/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      colors: {
        background: "#0D1117",
        foreground: "#F3F4F6",
        sidebar: "#111827",
        card: {
          DEFAULT: "#161B22",
          secondary: "#1E293B",
        },
        hover: "#21262D",
        border: "#30363D",
        primary: {
          DEFAULT: "#3B82F6",
          foreground: "#ffffff",
        },
        secondary: {
          DEFAULT: "#94A3B8",
          foreground: "#0D1117",
        },
        muted: {
          DEFAULT: "#1E293B",
          foreground: "#64748B",
        },
        destructive: {
          DEFAULT: "#ef4444",
          foreground: "#ffffff",
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        display: ['Sora', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      borderRadius: {
        'card': '8px',
        'table': '8px',
        'btn': '6px',
        'input': '6px',
      },
      boxShadow: {
        'soft': '0 1px 3px rgba(0,0,0,0.2)',
      },
    },
  },
  plugins: [require('tailwind-scrollbar')({ nocompatible: true })],
};
