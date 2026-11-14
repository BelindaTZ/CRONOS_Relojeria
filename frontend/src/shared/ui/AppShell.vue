<script setup>
/**
 * Shell: barra de navegación HORIZONTAL SUPERIOR FIJA (nunca sidebar — Principio XI).
 * Categorías de primer nivel; una categoría con varias sub-opciones se despliega
 * en un menú agrupado. El ítem/categoría activa lleva un filete de oro.
 * Es la única superficie oscura de la app.
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSessionStore } from '@/shared/stores/session'
import { visibleEnPortal } from '@/shared/rbacNav'
import HealthBadge from '@/health/components/HealthBadge.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { confirm } from '@/shared/ui/dialogs'

const session = useSessionStore()
const router = useRouter()
const route = useRoute()

/** ¿El usuario actual puede entrar a la ruta con este `name`? Mismo predicado
 * que aplica el guard — un ítem nunca aparece en el nav si el guard lo iba a
 * rebotar (Const. Ppio IV: el backend sigue siendo la autoridad real). */
function visible(nombreRuta) {
  const r = router.getRoutes().find((x) => x.name === nombreRuta)
  return r ? visibleEnPortal(session, r.meta) : false
}

// Cada entrada es un ítem simple (`to`) o un grupo (`hijos`); ambos se filtran
// por `visible()` — un grupo desaparece si ninguno de sus hijos es visible.
const categorias = computed(() => {
  const base = [
    { label: 'Panel', to: { name: 'inicio' } },
    { label: 'Mis datos', to: { name: 'perfil' } },
  ]
  const negocio = [
      {
        label: 'Citas',
        hijos: [
          { label: 'Citas', to: { name: 'citas' } },
          { label: 'Agenda del día / semana', to: { name: 'citas-agenda' } },
        ],
      },
      {
        label: 'Ventas',
        hijos: [
          { label: 'Ventas', to: { name: 'ventas' } },
          { label: 'Nueva venta', to: { name: 'venta-nueva' } },
          { label: 'Ventas del día', to: { name: 'ventas-dia' } },
          { label: 'Cuentas por cobrar', to: { name: 'cuentas-por-cobrar' } },
        ],
      },
      {
        label: 'Abastecimiento',
        hijos: [
          { label: 'Proveedores', to: { name: 'proveedores' } },
          { label: 'Órdenes de compra', to: { name: 'compras' } },
          { label: 'Compras programadas', to: { name: 'compras-programadas' } },
        ],
      },
      {
        label: 'Inventario',
        hijos: [
          { label: 'Relojes', to: { name: 'inventario' } },
          { label: 'Piezas y repuestos', to: { name: 'piezas' } },
          { label: 'Traslados entre sucursales', to: { name: 'traslados' } },
          { label: 'Alertas de stock', to: { name: 'alertas-stock' } },
          { label: 'Calibres', to: { name: 'calibres' } },
          { label: 'Valor del inventario', to: { name: 'valor-inventario' } },
        ],
      },
      {
        label: 'Taller',
        hijos: [
          { label: 'Órdenes de trabajo', to: { name: 'ordenes-trabajo' } },
          { label: 'Órdenes en curso', to: { name: 'ot-en-curso' } },
          { label: 'Informe de servicios', to: { name: 'informe-servicios' } },
          { label: 'Fichas de lubricación', to: { name: 'fichas-lubricacion' } },
          { label: 'Catálogo Moebius', to: { name: 'moebius' } },
          { label: 'Desviaciones de lubricación', to: { name: 'desviacion-lubricacion' } },
          { label: 'Personal técnico', to: { name: 'tecnicos' } },
          { label: 'Reglas de bono', to: { name: 'reglas-bono' } },
          { label: 'Bonos por periodo', to: { name: 'bonos-periodo' } },
          { label: 'Productividad', to: { name: 'productividad' } },
        ],
      },
      {
        label: 'Clientes',
        hijos: [
          { label: 'Clientes', to: { name: 'clientes' } },
          { label: 'Niveles de fidelización', to: { name: 'niveles-fidelizacion' } },
          { label: 'Descuentos', to: { name: 'descuentos' } },
          { label: 'Cupones', to: { name: 'cupones' } },
          { label: 'Margen mínimo protegido', to: { name: 'margen-minimo' } },
          { label: 'Clientes en riesgo', to: { name: 'clientes-en-riesgo' } },
          { label: 'Reportes de clientes', to: { name: 'reportes-clientes' } },
        ],
      },
      {
        label: 'Contabilidad',
        hijos: [
          { label: 'Libro diario', to: { name: 'libro-diario' } },
          { label: 'Plan de cuentas', to: { name: 'plan-cuentas' } },
          { label: 'Balance de comprobación', to: { name: 'balance-comprobacion' } },
          { label: 'Estado de resultados', to: { name: 'estado-resultados' } },
          { label: 'Caja y bancos', to: { name: 'caja' } },
          { label: 'Cheques', to: { name: 'cheques' } },
          { label: 'Cuentas por cobrar', to: { name: 'aging-cxc' } },
          { label: 'Cuentas por pagar', to: { name: 'aging-cxp' } },
          { label: 'Gastos', to: { name: 'gastos' } },
          { label: 'Gastos recurrentes', to: { name: 'gastos-recurrentes' } },
          { label: 'Rentabilidad por sucursal', to: { name: 'rentabilidad-sucursal' } },
        ],
      },
      {
        label: 'Mermas',
        hijos: [
          { label: 'Mermas y pérdidas', to: { name: 'mermas' } },
          { label: 'Reporte de mermas', to: { name: 'reporte-mermas' } },
        ],
      },
      {
        label: 'Reportes',
        hijos: [
          { label: 'Panel de Gerencia', to: { name: 'panel-gerencia' } },
          { label: 'Índice de reportes', to: { name: 'reportes-indice' } },
        ],
      },
      {
        label: 'Notificaciones',
        hijos: [
          { label: 'Envíos', to: { name: 'notificaciones-envios' } },
          { label: 'Plantillas de correo', to: { name: 'notificaciones-plantillas' } },
          { label: 'Preferencias de cliente', to: { name: 'notificaciones-preferencias' } },
        ],
      },
      {
        label: 'Sistema',
        hijos: [
          { label: 'Usuarios', to: { name: 'usuarios' } },
          { label: 'Roles y permisos', to: { name: 'roles' } },
          { label: 'Sucursales', to: { name: 'sucursales' } },
          { label: 'Configuración', to: { name: 'configuracion' } },
          { label: 'Facturación', to: { name: 'config-facturacion' } },
          { label: 'Parámetros', to: { name: 'parametros' } },
          { label: 'Auditoría', to: { name: 'auditoria' } },
        ],
      },
  ]
  const filtradas = negocio
    .map((cat) => ({ ...cat, hijos: cat.hijos.filter((h) => visible(h.to.name)) }))
    .filter((cat) => cat.hijos.length > 0)
  return [...base, ...filtradas]
})

const abierto = ref(null) // label del grupo abierto
const root = ref(null)

// El menú del grupo se renderiza con <Teleport> fuera de la lista de
// categorías: esa lista tiene overflow-x-auto (ver comentario de
// `actualizarDesbordamiento` más abajo) y, por cómo funciona `overflow`,
// fijar el eje X también clipa el eje Y — el desplegable quedaba recortado
// e invisible aunque el clic sí registraba (feedback del usuario 2026-09-11).
// Al teletransportarlo se posiciona con coordenadas de viewport (`position:
// fixed`) calculadas desde el botón que lo abrió.
const posMenu = ref({ top: 0, left: 0 })
function toggle(label, ev) {
  if (abierto.value === label) {
    abierto.value = null
    return
  }
  const r = ev.currentTarget.getBoundingClientRect()
  posMenu.value = { top: r.bottom + 4, left: r.left }
  abierto.value = label
}
function cerrar() {
  abierto.value = null
}
function onDocClick(e) {
  if (root.value && !root.value.contains(e.target) && !e.target.closest('[data-cr-navmenu]')) cerrar()
}
function onKey(e) {
  if (e.key === 'Escape') cerrar()
}
onMounted(() => {
  document.addEventListener('click', onDocClick)
  document.addEventListener('keydown', onKey)
  window.addEventListener('scroll', cerrar, true)
})
onBeforeUnmount(() => {
  document.removeEventListener('click', onDocClick)
  document.removeEventListener('keydown', onKey)
  window.removeEventListener('scroll', cerrar, true)
  window.removeEventListener('resize', actualizarDesbordamiento)
})

// La barra de categorías no envuelve (Principio XI: horizontal fija) y con
// suficientes módulos habilitados para un rol (p. ej. Gerencia General) deja
// de caber en anchos de portátil comunes. En vez de dejarla desbordar la
// página (bug real: el ítem quedaba clicable "en teoría" pero fuera del
// área visible/interactuable — feedback del usuario 2026-09-11), la lista
// se vuelve desplazable en sí misma y estas flechas dan la pista visual.
const navList = ref(null)
const puedeIzquierda = ref(false)
const puedeDerecha = ref(false)
function actualizarDesbordamiento() {
  const el = navList.value
  if (!el) return
  puedeIzquierda.value = el.scrollLeft > 2
  puedeDerecha.value = el.scrollLeft + el.clientWidth < el.scrollWidth - 2
}
function desplazar(dir) {
  navList.value?.scrollBy({ left: dir * 220, behavior: 'smooth' })
}
onMounted(() => {
  actualizarDesbordamiento()
  window.addEventListener('resize', actualizarDesbordamiento)
})
watch(categorias, () => nextTick(actualizarDesbordamiento))

function grupoActivo(grupo) {
  return grupo.hijos?.some((h) => h.to?.name === route.name)
}

const iniciales = computed(() =>
  (session.perfil?.nombre ?? '?')
    .split(' ')
    .slice(0, 2)
    .map((p) => p[0])
    .join('')
    .toUpperCase(),
)

async function salir() {
  if (!(await confirm({ title: 'Cerrar sesión', message: '¿Salir del sistema?' }))) return
  await session.logout()
  router.push({ name: 'login' })
}
</script>

<template>
  <div class="min-h-screen bg-canvas">
    <header class="sticky top-0 z-20 bg-nav text-nav-ink">
      <nav
        ref="root"
        class="mx-auto flex h-[60px] max-w-[1200px] items-center gap-2 px-7"
        aria-label="Navegación principal"
      >
        <span class="serif mr-4 shrink-0 text-[1.35rem] tracking-[0.14em]">CRONOS</span>
        <button
          v-if="puedeIzquierda"
          type="button"
          aria-label="Ver categorías anteriores"
          class="shrink-0 rounded-full p-1 text-nav-ink-2 hover:bg-white/10 hover:text-nav-ink"
          @click="desplazar(-1)"
        >
          <CrIcon name="chevron-left" :size="15" />
        </button>
        <ul
          ref="navList"
          class="flex min-w-0 flex-1 items-center gap-1 overflow-x-auto scroll-smooth [&::-webkit-scrollbar]:hidden"
          style="scrollbar-width: none; -ms-overflow-style: none"
          @scroll="actualizarDesbordamiento"
        >
          <li v-for="c in categorias" :key="c.label" class="relative">
            <!-- ítem simple -->
            <RouterLink
              v-if="c.to"
              :to="c.to"
              class="relative block whitespace-nowrap px-3 py-2 text-[0.82rem] font-medium text-nav-ink-2 hover:text-nav-ink"
              active-class="!text-gold-on-navy [&>span]:block"
            >
              {{ c.label }}
              <span class="absolute inset-x-3 -bottom-px hidden h-0.5 bg-gold-on-navy"></span>
            </RouterLink>

            <!-- grupo con menú -->
            <template v-else>
              <button
                type="button"
                class="relative flex items-center gap-1 whitespace-nowrap px-3 py-2 text-[0.82rem] font-medium hover:text-nav-ink"
                :class="grupoActivo(c) || abierto === c.label ? 'text-gold-on-navy' : 'text-nav-ink-2'"
                :aria-expanded="abierto === c.label"
                @click.stop="toggle(c.label, $event)"
              >
                {{ c.label }}
                <CrIcon name="chevron-down" :size="13" class="transition-transform" :class="{ 'rotate-180': abierto === c.label }" />
                <span class="absolute inset-x-3 -bottom-px h-0.5 bg-gold-on-navy" :class="grupoActivo(c) ? 'block' : 'hidden'"></span>
              </button>
              <Teleport to="body">
                <div
                  v-if="abierto === c.label"
                  data-cr-navmenu
                  class="fixed z-30 min-w-[15rem] rounded-xl border border-hairline bg-surface py-1.5 shadow-md"
                  :style="{ top: posMenu.top + 'px', left: posMenu.left + 'px' }"
                >
                  <RouterLink
                    v-for="h in c.hijos"
                    :key="h.label"
                    :to="h.to"
                    class="block px-4 py-2 text-sm text-ink-2 hover:bg-surface-sunk hover:text-ink"
                    active-class="!text-gold-strong font-medium"
                    @click="cerrar"
                  >
                    {{ h.label }}
                  </RouterLink>
                </div>
              </Teleport>
            </template>
          </li>
        </ul>
        <button
          v-if="puedeDerecha"
          type="button"
          aria-label="Ver más categorías"
          class="shrink-0 rounded-full p-1 text-nav-ink-2 hover:bg-white/10 hover:text-nav-ink"
          @click="desplazar(1)"
        >
          <CrIcon name="chevron-right" :size="15" />
        </button>
        <div class="flex shrink-0 items-center gap-3 border-l border-white/10 pl-4">
          <HealthBadge />
          <RouterLink
            :to="{ name: 'perfil' }"
            class="flex items-center gap-2 text-[0.8rem] text-nav-ink-2 hover:text-nav-ink"
            title="Mis datos"
          >
            <img
              v-if="session.fotoPerfil"
              :src="session.fotoPerfil"
              alt="Foto de perfil"
              class="h-[30px] w-[30px] rounded-full border border-gold-on-navy object-cover"
            />
            <span
              v-else
              class="serif grid h-[30px] w-[30px] place-items-center rounded-full border border-gold-on-navy text-[0.72rem] text-gold-on-navy"
            >
              {{ iniciales }}
            </span>
          </RouterLink>
          <button class="text-[0.8rem] text-nav-ink-2 hover:text-nav-ink" @click="salir">
            <span class="hidden sm:inline">Salir</span>
            <CrIcon name="log-out" :size="16" class="sm:hidden" />
          </button>
        </div>
      </nav>
    </header>

    <main class="mx-auto max-w-[1200px] px-7 pb-16 pt-9">
      <slot />
    </main>
  </div>
</template>
