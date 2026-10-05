const defaultTheme = require("tailwindcss/defaultTheme");

/** @type {import('tailwindcss').Config} */
module.exports = {
  // ต้องสแกนไฟล์ .py ที่เก็บชื่อ class สี (models.py / forms.py) ด้วย
  content: [
    "./templates/**/*.html",
    "./*/templates/**/*.html",
    "./*/models.py",
    "./*/forms.py",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Noto Sans Thai"', ...defaultTheme.fontFamily.sans],
      },
    },
  },
  plugins: [],
};
