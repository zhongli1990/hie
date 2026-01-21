import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // NHS color palette
        nhs: {
          blue: "#005eb8",
          "dark-blue": "#003087",
          "bright-blue": "#0072ce",
          "light-blue": "#41b6e6",
          "aqua-blue": "#00a9ce",
          black: "#231f20",
          "dark-grey": "#425563",
          "mid-grey": "#768692",
          "pale-grey": "#e8edee",
          white: "#ffffff",
          green: "#007f3b",
          "light-green": "#78be20",
          yellow: "#ffb81c",
          orange: "#ed8b00",
          red: "#da291c",
          "dark-red": "#8a1538",
          pink: "#ae2573",
          "light-purple": "#704c9c",
          purple: "#330072",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
