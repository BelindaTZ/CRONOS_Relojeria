import { describe, it, expect } from 'vitest'
import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import { existsSync } from 'node:fs'

const here = dirname(fileURLToPath(import.meta.url))
const root = resolve(here, '..')

describe('Frontera de módulos del frontend (Principio X)', () => {
  it('ningún módulo importa los internos de otro', () => {
    // El script sale con código 0 si no hay violaciones.
    expect(() =>
      execFileSync('node', ['scripts/check_module_boundaries.mjs'], { cwd: root, stdio: 'pipe' }),
    ).not.toThrow()
  })

  it('existe shared/ y el módulo plantilla health/ con sus capas', () => {
    expect(existsSync(resolve(root, 'src/shared/api/client.js'))).toBe(true)
    expect(existsSync(resolve(root, 'src/shared/ui/dialogs.js'))).toBe(true)
    expect(existsSync(resolve(root, 'src/shared/ui/DialogHost.vue'))).toBe(true)
    expect(existsSync(resolve(root, 'src/shared/exportar.js'))).toBe(true)
    for (const capa of [
      'components/HealthBadge.vue',
      'composables/useHealth.js',
      'services/healthApi.js',
      'routes.js',
    ]) {
      expect(existsSync(resolve(root, 'src/health', capa))).toBe(true)
    }
  })
})
