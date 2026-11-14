import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'

vi.mock('@/health/services/healthApi', () => ({
  fetchHealth: vi.fn().mockResolvedValue({ status: 'ok', db: 'up', storage: 'up', version: '0.1.0' }),
}))

import AppShell from '@/shared/ui/AppShell.vue'
import App from '@/App.vue'
import DialogHost from '@/shared/ui/DialogHost.vue'

function router() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'inicio', component: { template: '<div/>' } },
      { path: '/mis-datos', name: 'perfil', component: { template: '<div/>' } },
      { path: '/login', name: 'login', component: { template: '<div/>' }, meta: { sinShell: true } },
    ],
  })
}

beforeEach(() => setActivePinia(createPinia()))

describe('AppShell', () => {
  it('renderiza una barra de navegación superior fija (no sidebar)', async () => {
    const r = router()
    r.push('/')
    await r.isReady()
    const wrapper = mount(AppShell, { global: { plugins: [r] } })
    const header = wrapper.find('header')
    expect(header.exists()).toBe(true)
    expect(header.classes()).toContain('sticky')
    expect(wrapper.find('nav[aria-label="Navegación principal"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('CRONOS')
  })
})

describe('App', () => {
  it('monta <DialogHost> exactamente una vez', async () => {
    const r = router()
    r.push('/')
    await r.isReady()
    const wrapper = mount(App, { global: { plugins: [r] } })
    expect(wrapper.findAllComponents(DialogHost)).toHaveLength(1)
  })

  it('oculta la barra de navegación en rutas con meta.sinShell', async () => {
    const r = router()
    r.push('/login')
    await r.isReady()
    const wrapper = mount(App, { global: { plugins: [r] } })
    expect(wrapper.find('nav[aria-label="Navegación principal"]').exists()).toBe(false)
  })
})
