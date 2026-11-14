<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import PageHeader from '@/shared/ui/PageHeader.vue'
import FormModal from '@/shared/ui/FormModal.vue'
import FormField from '@/shared/ui/FormField.vue'
import CrIcon from '@/shared/ui/CrIcon.vue'
import { toast } from '@/shared/ui/toast'
import { crearRol, getPermisos, listarModulos, listarRoles, setPermisos } from '@/rbac/services/rbacApi'

const OPERACIONES = ['crear', 'consultar', 'editar', 'eliminar']

const roles = ref([])
const modulos = ref([])
const rolActivo = ref(null)
const matriz = reactive({})
const guardando = ref(false)
const cargando = ref(true)

const nuevo = reactive({ abierto: false, guardando: false, error: '', nombre: '', descripcion: '' })

async function cargar() {
  cargando.value = true
  ;[roles.value, modulos.value] = await Promise.all([listarRoles(), listarModulos()])
  cargando.value = false
  if (roles.value.length && !rolActivo.value) seleccionar(roles.value[0])
}
onMounted(cargar)

async function seleccionar(rol) {
  rolActivo.value = rol
  const permisos = await getPermisos(rol.id)
  for (const m of modulos.value) {
    const p = permisos.find((x) => x.modulo === m.clave)
    matriz[m.clave] = { acceso: !!p?.acceso, operaciones: new Set(p?.operaciones ?? []) }
  }
}

function toggleAcceso(clave) {
  const fila = matriz[clave]
  fila.acceso = !fila.acceso
  if (!fila.acceso) fila.operaciones.clear()
}
function toggleOp(clave, op) {
  const fila = matriz[clave]
  if (fila.operaciones.has(op)) fila.operaciones.delete(op)
  else {
    fila.operaciones.add(op)
    fila.acceso = true
  }
}

async function crear() {
  nuevo.error = ''
  if (nuevo.nombre.trim().length < 2) return (nuevo.error = 'El nombre es obligatorio.')
  nuevo.guardando = true
  try {
    const r = await crearRol({ nombre: nuevo.nombre.trim(), descripcion: nuevo.descripcion.trim() || null })
    roles.value.push(r)
    nuevo.abierto = false
    nuevo.nombre = nuevo.descripcion = ''
    await seleccionar(r)
    toast.success(`Rol «${r.nombre}» creado`)
  } catch (e) {
    nuevo.error = e.status === 409 ? 'Ya existe un rol con ese nombre.' : e.message
  } finally {
    nuevo.guardando = false
  }
}

async function guardar() {
  guardando.value = true
  try {
    const entradas = modulos.value.map((m) => ({
      modulo: m.clave,
      acceso: matriz[m.clave].acceso,
      operaciones: [...matriz[m.clave].operaciones],
    }))
    await setPermisos(rolActivo.value.id, entradas)
    toast.success('Matriz de permisos guardada')
  } catch (e) {
    toast.error(e.status === 422 ? 'Hay operaciones marcadas sin habilitar el acceso al módulo.' : e.message)
  } finally {
    guardando.value = false
  }
}

const hayRol = computed(() => Boolean(rolActivo.value))
</script>

<template>
  <div>
    <PageHeader eyebrow="Sistema · Seguridad" titulo="Roles y permisos" sub="Acceso a módulo + operación por rol (RBAC de dos niveles). El acceso al módulo es prerrequisito.">
      <template #acciones>
        <button class="cr-btn cr-btn-ghost" @click="nuevo.abierto = true">
          <CrIcon name="plus" :size="15" /> Nuevo rol
        </button>
        <button v-if="hayRol" class="cr-btn cr-btn-primary" :disabled="guardando" @click="guardar">
          {{ guardando ? 'Guardando…' : 'Guardar matriz' }}
        </button>
      </template>
    </PageHeader>

    <div class="grid gap-5 lg:grid-cols-[220px_1fr]">
      <aside class="cr-card p-2">
        <button
          v-for="r in roles"
          :key="r.id"
          class="block w-full rounded-lg px-3 py-2 text-left text-sm"
          :class="rolActivo?.id === r.id ? 'bg-surface-sunk font-semibold text-ink' : 'text-ink-2 hover:bg-surface-sunk'"
          @click="seleccionar(r)"
        >
          {{ r.nombre }}
          <span v-if="r.descripcion" class="block truncate text-xs font-normal text-ink-3">{{ r.descripcion }}</span>
        </button>
        <p v-if="!roles.length && !cargando" class="p-3 text-sm text-ink-3">Sin roles.</p>
      </aside>

      <section class="cr-card overflow-hidden p-0">
        <div v-if="hayRol" class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b-2 border-table-head-border bg-surface-head text-left">
                <th class="px-4 py-3 text-[0.7rem] font-semibold uppercase text-ink-2">Módulo</th>
                <th class="px-3 py-3 text-center text-[0.7rem] font-semibold uppercase text-ink-2">Acceso</th>
                <th v-for="op in OPERACIONES" :key="op" class="px-3 py-3 text-center text-[0.7rem] font-semibold uppercase text-ink-2">{{ op }}</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-hairline-soft">
              <tr v-for="m in modulos" :key="m.clave" class="hover:bg-surface-sunk">
                <td class="px-4 py-2.5 text-ink">{{ m.nombre }}</td>
                <td class="px-3 py-2.5 text-center">
                  <input type="checkbox" :checked="matriz[m.clave]?.acceso" @change="toggleAcceso(m.clave)" />
                </td>
                <td v-for="op in OPERACIONES" :key="op" class="px-3 py-2.5 text-center">
                  <input
                    type="checkbox"
                    :checked="matriz[m.clave]?.operaciones.has(op)"
                    :disabled="!matriz[m.clave]?.acceso && !matriz[m.clave]?.operaciones.has(op)"
                    @change="toggleOp(m.clave, op)"
                  />
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-else class="p-10 text-center text-sm text-ink-3">Selecciona o crea un rol.</p>
      </section>
    </div>

    <FormModal v-model="nuevo.abierto" titulo="Nuevo rol" :guardando="nuevo.guardando" ancho="max-w-md" @guardar="crear">
      <FormField label="Nombre" required wide><input v-model="nuevo.nombre" class="cr-input" minlength="2" required /></FormField>
      <FormField label="Descripción" wide helper="Para qué sirve este rol">
        <input v-model="nuevo.descripcion" class="cr-input" />
      </FormField>
      <p v-if="nuevo.error" class="text-sm text-bad sm:col-span-2" role="alert">{{ nuevo.error }}</p>
    </FormModal>
  </div>
</template>
