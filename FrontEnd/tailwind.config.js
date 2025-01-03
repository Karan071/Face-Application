
export default {
  content: [
    "./index.html",  // Include your main HTML file
    "./src/**/*.{js,ts,jsx,tsx}",  // Include all JS, TS, JSX, and TSX files in the src folder
  ],
  theme: {
    extend: {
      fontFamily: {
        poppins: ['Poppins', 'sans-serif'],
        raleway: ['Raleway', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
