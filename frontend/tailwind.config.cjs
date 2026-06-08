/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./index.html', './src/**/*.{vue,js}'],
  theme: {
    extend: {
      colors: {
        primary: '#ee2435',
        'primary-dark': '#c81e2c',
        navy: '#011e41',
        'navy-light': '#0a2d5a',
        success: '#28a745',
        warning: '#ffc107',
        error: '#dc3545',
        'light-gray': '#f5f6f7',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        card: '8px',
      },
      boxShadow: {
        card: '0 1px 4px rgba(0,0,0,0.08), 0 2px 8px rgba(0,0,0,0.04)',
      },
    },
  },
  plugins: [],
}
