import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('@/shared/api/client', () => {
  const calls = []
  return {
    calls,
    setTokenProvider: vi.fn(),
    apiClient: {
      post: vi.fn(async (path, body) => {
        calls.push([path, body])
        if (path === '/auth/login')
          return { access_token: 'AT', refresh_token: 'RT', must_change_password: false }
        return {}
      }),
      get: vi.fn(async () => ({ nombre: 'Ana Gómez', roles: ['Gerencia General'], sucursales: [] })),
    },
  }
})

import { useSessionStore } from '@/shared/stores/session'

beforeEach(() => {
  setActivePinia(createPinia())
  try {
    localStorage.clear()
  } catch {
    /* noop */
  }
})

describe('session store', () => {
  it('login guarda el token, carga el perfil y marca autenticado', async () => {
    const s = useSessionStore()
    expect(s.autenticado).toBe(false)
    await s.login('123', 'clave')
    expect(s.accessToken).toBe('AT')
    expect(s.autenticado).toBe(true)
    expect(s.esGerencia).toBe(true)
  })

  it('mustChangePassword bloquea el estado autenticado', async () => {
    const { apiClient } = await import('@/shared/api/client')
    apiClient.post.mockResolvedValueOnce({ access_token: 'AT', must_change_password: true })
    const s = useSessionStore()
    await s.login('123', 'temporal')
    expect(s.mustChangePassword).toBe(true)
    expect(s.autenticado).toBe(false)
  })

  it('logout limpia el estado', async () => {
    const s = useSessionStore()
    await s.login('123', 'clave')
    await s.logout()
    expect(s.accessToken).toBeNull()
    expect(s.autenticado).toBe(false)
  })
})
