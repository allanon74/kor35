/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        kor: {
          surface: 'var(--kor-surface)',
          raised: 'var(--kor-surface-raised)',
          overlay: 'var(--kor-surface-overlay)',
          border: 'var(--kor-border)',
          text: 'var(--kor-text)',
          muted: 'var(--kor-text-muted)',
          accent: 'var(--kor-accent)',
          danger: 'var(--kor-danger)',
          success: 'var(--kor-success)',
          warning: 'var(--kor-warning)',
        },
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}