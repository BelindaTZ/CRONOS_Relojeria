/**
 * Verifica el contraste WCAG AA (>=4.5:1 texto normal) para los pares canónicos
 * de texto sobre superficie Primary y sobre superficie Secondary, leyendo los
 * valores directamente de src/shared/tokens.css (fuente única — Principio XI/XII).
 *
 * Uso:  node scripts/check_contrast.mjs
 * Sale con código 1 si algún par no cumple AA.
 */
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))
const tokensPath = resolve(here, '../src/shared/tokens.css')
const css = readFileSync(tokensPath, 'utf8')

/** Extrae `--nombre: #hex;` del CSS de tokens. */
function token(name) {
  const m = css.match(new RegExp(`--${name}:\\s*(#[0-9A-Fa-f]{6})`))
  if (!m) throw new Error(`Token no encontrado: --${name}`)
  return m[1]
}

function channel(c) {
  const s = c / 255
  return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4)
}

function luminance(hex) {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)
}

function contrast(a, b) {
  const l1 = luminance(a)
  const l2 = luminance(b)
  const [hi, lo] = l1 > l2 ? [l1, l2] : [l2, l1]
  return (hi + 0.05) / (lo + 0.05)
}

const AA_NORMAL = 4.5

const pairs = [
  {
    label: 'Texto sobre Primary (barra de navegación)',
    fg: token('color-primary-50'),
    bg: token('color-primary-900'),
  },
  {
    label: 'Texto sobre Secondary (insignias / acentos de valor)',
    fg: token('color-secondary-50'),
    bg: token('color-secondary-800'),
  },
  {
    label: 'Acento Secondary sobre Primary (estado activo de navegación)',
    fg: token('color-secondary-300'),
    bg: token('color-primary-900'),
  },
  {
    label: 'Texto de oro sobre marfil (--gold = secondary-700 sobre --canvas)',
    fg: token('color-secondary-700'),
    bg: token('canvas'),
  },
  {
    label: 'Texto de oro sobre tarjeta blanca (secondary-700 sobre surface)',
    fg: token('color-secondary-700'),
    bg: token('surface'),
  },
  {
    label: 'Encabezado de tabla (ink-2 sobre --surface-head)',
    fg: token('ink-2'),
    bg: token('surface-head'),
  },
]

let failed = false
for (const { label, fg, bg } of pairs) {
  const ratio = contrast(fg, bg)
  const ok = ratio >= AA_NORMAL
  if (!ok) failed = true
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${ratio.toFixed(2)}:1  ${fg} sobre ${bg}  — ${label}`)
}

if (failed) {
  console.error('\nContraste AA NO cumplido en algún par.')
  process.exit(1)
}
console.log('\nTodos los pares cumplen WCAG AA (>=4.5:1).')
