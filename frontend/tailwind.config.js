/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        border: "hsl(215 27.9% 16.9%)",
        input: "hsl(215 27.9% 16.9%)",
        ring: "hsl(216 12.2% 83.9%)",
        background: "hsl(224 71.4% 4.1%)",
        foreground: "hsl(210 20% 98%)",
        primary: {
          DEFAULT: "hsl(210 20% 98%)",
          foreground: "hsl(220.9 39.3% 11%)",
        },
        secondary: {
          DEFAULT: "hsl(215 27.9% 16.9%)",
          foreground: "hsl(210 20% 98%)",
        },
        destructive: {
          DEFAULT: "hsl(0 62.8% 30.6%)",
          foreground: "hsl(210 20% 98%)",
        },
        muted: {
          DEFAULT: "hsl(215 27.9% 16.9%)",
          foreground: "hsl(217.9 10.6% 64.9%)",
        },
        accent: {
          DEFAULT: "hsl(215 27.9% 16.9%)",
          foreground: "hsl(210 20% 98%)",
        },
        card: {
          DEFAULT: "hsl(224 71.4% 4.1%)",
          foreground: "hsl(210 20% 98%)",
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
}
