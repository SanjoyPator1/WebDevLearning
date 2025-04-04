/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#00B4D8',
          dark: '#0096C7',
          light: '#90E0EF',
        },
        secondary: {
          DEFAULT: '#6C63FF',
          dark: '#5A56E0',
          light: '#8F89FF',
        },
        background: {
          light: '#F8FAFC',
          dark: '#0F172A',
        },
        text: {
          light: '#64748B',
          dark: '#1E293B',
        },
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
