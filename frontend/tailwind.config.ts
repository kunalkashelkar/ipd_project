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
        // High-end Security Operations Workstation surfaces
        background: "#090D12",
        foreground: "#F1F5F9",
        sidebar: "#0D1219",
        card: {
          DEFAULT: "#131923",
          secondary: "#18202D",
          elevated: "#18202D",
          hover: "#1C2534",
        },
        hover: "#1C2534",
        border: {
          DEFAULT: "#212C3D",
          subtle: "#16202C",
          strong: "#334155",
        },
        // VulnScan brand accents inspired by the logo
        brand: {
          orange: "#F97316",
          amber: "#F59E0B",
          violet: "#8B5CF6",
          purple: "#7C3AED",
          cyan: "#06B6D4",
        },
        primary: {
          DEFAULT: "#0EA5E9",
          hover: "#0284C7",
          foreground: "#ffffff",
        },
        secondary: {
          DEFAULT: "#94A3B8",
          foreground: "#090D12",
        },
        muted: {
          DEFAULT: "#18202D",
          foreground: "#64748B",
        },
        destructive: {
          DEFAULT: "#EF4444",
          foreground: "#ffffff",
        },
        // Canonical Severity Tokens
        severity: {
          critical: "#EF4444",
          high: "#F97316",
          medium: "#F59E0B",
          low: "#3B82F6",
          info: "#06B6D4",
          success: "#10B981",
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
        'soft': '0 1px 3px rgba(0,0,0,0.3)',
        'elevated': '0 4px 12px rgba(0,0,0,0.45)',
        'glow-brand': '0 0 20px rgba(249,115,22,0.15)',
        'glow-primary': '0 0 20px rgba(14,165,233,0.15)',
      },
    },
  },
  plugins: [require('tailwind-scrollbar')({ nocompatible: true })],
};
