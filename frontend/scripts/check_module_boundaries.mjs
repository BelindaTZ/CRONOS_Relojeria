/**
 * Verifica la frontera de módulos del frontend (Constitución, Principio X).
 *
 * Regla: un módulo de negocio (`src/<modulo>/`, distinto de las carpetas de
 * infraestructura `shared/` y `router/` y de los archivos raíz de `src/`) NO
 * puede importar archivos internos de OTRO módulo de negocio. Puede importar de
 * `@/shared/...` y de la API pública explícita de otro módulo
 * (`@/<modulo>/index.js` / `@/<modulo>/routes.js`).
 *
 * Uso:  node scripts/check_module_boundaries.mjs
 * Sale con código 1 si detecta un import cruzado prohibido.
 */
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve, relative, sep } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))
const srcDir = resolve(here, '../src')

const PUBLIC_ENTRYPOINTS = new Set(['index.js', 'index.ts', 'routes.js', 'routes.ts'])
// Carpetas de infraestructura (no son módulos de negocio): pueden componer módulos.
const INFRA_ROOTS = new Set(['shared', 'router'])
const IMPORT_RE = /(?:import|export)[^'"]*?from\s*['"]([^'"]+)['"]|import\s*\(\s*['"]([^'"]+)['"]\s*\)/g

function walk(dir) {
  const out = []
  for (const entry of readdirSync(dir)) {
    const full = resolve(dir, entry)
    if (statSync(full).isDirectory()) out.push(...walk(full))
    else if (/\.(vue|js|ts|mjs)$/.test(entry)) out.push(full)
  }
  return out
}

function moduleOf(absPath) {
  const rel = relative(srcDir, absPath)
  const parts = rel.split(sep)
  // Archivo directamente en src/ (App.vue, main.js): infraestructura raíz.
  if (parts.length === 1) return null
  return parts[0]
}

const violations = []

for (const file of walk(srcDir)) {
  const owner = moduleOf(file)
  if (owner === null || INFRA_ROOTS.has(owner)) continue

  const code = readFileSync(file, 'utf8')
  for (const match of code.matchAll(IMPORT_RE)) {
    const spec = match[1] ?? match[2]
    if (!spec) continue

    let target = null
    if (spec.startsWith('@/')) target = spec.slice(2)
    else if (spec.startsWith('src/')) target = spec.slice(4)
    if (!target) continue // dependencia externa o relativa dentro del propio módulo

    const parts = target.split('/')
    const targetModule = parts[0]
    if (INFRA_ROOTS.has(targetModule) || targetModule === owner) continue

    // Import a otro módulo de negocio: solo se permite su entrypoint público.
    const rest = parts.slice(1)
    const isPublicEntry = rest.length === 0 || (rest.length === 1 && PUBLIC_ENTRYPOINTS.has(rest[0]))
    if (!isPublicEntry) {
      violations.push({ file: relative(srcDir, file), spec, targetModule })
    }
  }
}

if (violations.length) {
  console.error('Imports cruzados de internos entre módulos (prohibido — Principio X):\n')
  for (const v of violations) {
    console.error(`  ${v.file}\n    → "${v.spec}"  (interno del módulo "${v.targetModule}")`)
  }
  process.exit(1)
}

console.log('OK: ningún módulo importa los internos de otro.')
