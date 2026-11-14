/**
 * Tailwind — CRONOS. Paleta del Principio XI (constitución v1.7.0).
 * Fuente única de color: src/shared/tokens.css. Aquí solo se referencian los tokens.
 * Tipografía: Cormorant Garamond (display + cifras) + Hanken Grotesk (UI).
 */

/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts}'],
  theme: {
    extend: {
      fontFamily: {
        serif: ['Cormorant Garamond', 'Georgia', 'serif'],
        sans: ['Hanken Grotesk', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
      },
      colors: {
        canvas: 'var(--canvas)',
        surface: 'var(--surface)',
        'surface-sunk': 'var(--surface-sunk)',
        'surface-head': 'var(--surface-head)',
        'table-head-border': 'var(--table-head-border)',
        hairline: 'var(--hairline)',
        'hairline-soft': 'var(--hairline-soft)',
        ink: { DEFAULT: 'var(--ink)', 2: 'var(--ink-2)', 3: 'var(--ink-3)' },
        nav: { DEFAULT: 'var(--nav)', ink: 'var(--nav-ink)', 'ink-2': 'var(--nav-ink-2)' },
        gold: {
          DEFAULT: 'var(--gold)',
          strong: 'var(--gold-strong)',
          'on-navy': 'var(--gold-on-navy)',
          deep: 'var(--gold-deep)',
          pale: 'var(--gold-pale)',
        },
        good: { DEFAULT: 'var(--good)', bg: 'var(--good-bg)' },
        warn: { DEFAULT: 'var(--warn)', bg: 'var(--warn-bg)' },
        bad: { DEFAULT: 'var(--bad)', bg: 'var(--bad-bg)' },
        primary: mapScale('primary'),
        secondary: mapScale('secondary'),
        tertiary: mapScale('tertiary'),
        neutral: mapScale('neutral'),
        danger: mapScale('danger'),
        warning: mapScale('warning'),
      },
      boxShadow: {
        sm: 'var(--shadow-sm)',
        md: 'var(--shadow-md)',
      },
    },
  },
  plugins: [],
}

function mapScale(name) {
  const steps = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950]
  return Object.fromEntries(steps.map((s) => [s, `var(--color-${name}-${s})`]))
}
