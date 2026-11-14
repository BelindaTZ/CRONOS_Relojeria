<script setup>
import { onMounted, reactive, ref, watch } from 'vue'
import FormModal from '@/shared/ui/FormModal.vue'
import FormField from '@/shared/ui/FormField.vue'
import ComboBox from '@/shared/ui/ComboBox.vue'
import CheckList from '@/shared/ui/CheckList.vue'
import { toast } from '@/shared/ui/toast'
import { listarUsuarios } from '@/usuarios'
import { listarSucursales } from '@/sucursales'
import {
  actualizarTecnico,
  crearEspecialidad,
  crearTecnico,
  listarEspecialidades,
} from '@/tecnicos/services/tecnicosApi'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  tecnico: { type: Object, default: null }, // si viene, es edición
})
const emit = defineEmits(['update:modelValue', 'guardado'])

function vacio() {
  return { nombre: '', certificaciones: '', usuario_id: null, especialidades: [], sucursales: [] }
}
const f = reactive(vacio())
const guardando = ref(false)
const error = ref('')
const usuarios = ref([])
const sucursales = ref([])
const especialidades = ref([])

onMounted(async () => {
  const [u, s, e] = await Promise.all([
    listarUsuarios({ page: 1, size: 100 }).catch(() => ({ items: [] })),
    listarSucursales().catch(() => ({ items: [] })),
    listarEspecialidades().catch(() => []),
  ])
  usuarios.value = u.items.map((x) => ({ ...x, _label: `${x.nombre} · ${x.identificacion}` }))
  sucursales.value = s.items
  especialidades.value = e
})

watch(
  () => props.modelValue,
  (v) => {
    if (!v) return
    error.value = ''
    if (props.tecnico) {
      Object.assign(f, {
        nombre: props.tecnico.nombre,
        certificaciones: props.tecnico.certificaciones ?? '',
        usuario_id: props.tecnico.usuario_id ?? null,
        especialidades: [...(props.tecnico.especialidad_ids || [])],
        sucursales: [...(props.tecnico.sucursal_ids || [])],
      })
    } else {
      Object.assign(f, vacio())
    }
  },
)

async function nuevaEspecialidad(nombre) {
  try {
    const e = await crearEspecialidad(nombre)
    especialidades.value.push(e)
    f.especialidades = [...f.especialidades, e.id]
    return e
  } catch (err) {
    toast.error(err.message)
    return null
  }
}

async function guardar() {
  error.value = ''
  if (!f.nombre.trim()) return (error.value = 'El nombre es obligatorio.')
  guardando.value = true
  try {
    const payload = {
      nombre: f.nombre.trim(),
      certificaciones: f.certificaciones.trim() || null,
      usuario_id: f.usuario_id,
      especialidades: f.especialidades,
      sucursales: f.sucursales,
    }
    if (props.tecnico) {
      await actualizarTecnico(props.tecnico.id, payload)
      toast.success('Ficha del técnico actualizada')
    } else {
      await crearTecnico(payload)
      toast.success(`${f.nombre.trim()} registrado`)
    }
    emit('update:modelValue', false)
    emit('guardado')
  } catch (e) {
    error.value = e.status === 403 ? 'Requiere Técnico Jefe o Gerencia General.' : e.message
  } finally {
    guardando.value = false
  }
}
</script>

<template>
  <FormModal
    :model-value="modelValue"
    :titulo="tecnico ? 'Editar técnico' : 'Nuevo técnico'"
    subtitulo="Los datos de contacto y la foto los edita el propio técnico en «Mis datos»."
    :guardando="guardando"
    ancho="max-w-2xl"
    :sucio="!!f.nombre"
    @update:model-value="emit('update:modelValue', $event)"
    @guardar="guardar"
  >
    <FormField label="Nombre completo" required>
      <input v-model="f.nombre" class="cr-input" required />
    </FormField>
    <FormField label="Usuario del sistema" helper="Vincula al técnico con su acceso (opcional).">
      <ComboBox v-model="f.usuario_id" :opciones="usuarios" opcion-label="_label" opcion-value="id" placeholder="Sin acceso al sistema" />
    </FormField>

    <FormField label="Certificaciones y formación" wide helper="Texto descriptivo: cursos, certificados de marca, años de experiencia.">
      <textarea v-model="f.certificaciones" rows="3" class="cr-input"></textarea>
    </FormField>

    <FormField label="Especialidades" wide helper="Marcas y complicaciones que domina. Se usan para sugerir la asignación de órdenes de trabajo.">
      <ComboBox
        :opciones="especialidades" opcion-label="nombre" opcion-value="id"
        placeholder="Buscar o crear una especialidad…"
        :crear="nuevaEspecialidad" crear-label="Crear especialidad"
        @update:model-value="(id) => id && !f.especialidades.includes(id) && (f.especialidades = [...f.especialidades, id])"
      />
      <div class="mt-2">
        <CheckList v-model="f.especialidades" :opciones="especialidades" opcion-label="nombre" opcion-value="id" />
      </div>
    </FormField>

    <FormField label="Sucursales donde trabaja" wide>
      <CheckList v-model="f.sucursales" :opciones="sucursales" opcion-label="nombre" opcion-value="id" />
    </FormField>

    <p v-if="error" class="text-sm text-bad sm:col-span-2" role="alert">{{ error }}</p>
  </FormModal>
</template>
