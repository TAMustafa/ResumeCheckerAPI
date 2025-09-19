/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./popup.html",
    "./options.html",
    "./js/**/*.js"
  ],
  darkMode: 'media',
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#1a73e8',
          hover: '#1765cc'
        }
      },
      boxShadow: {
        elev1: '0 1px 2px rgba(15, 23, 42, 0.06), 0 1px 1px rgba(15, 23, 42, 0.04)'
      }
    }
  },
  plugins: []
};
