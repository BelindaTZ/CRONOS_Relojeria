/**
 * Store de sesión (Pinia). Única fuente de verdad del token y del perfil del
 * usuario en el frontend. Registra el proveedor de token en el cliente HTTP
 * compartido (Principio X: nadie más toca el token).
 */
import { defineStore } from 'pinia'
import { apiClient, setTokenProvider } from '@/shared/api/client'

const LS_KEY = 'cronos.session'

function cargar() {
  try {
    return JSON.parse(localStorage.getItem(LS_KEY) || 'null')
  } catch {
    return null
  }
}

function guardar(estado) {
  try {
    if (estado) localStorage.setItem(LS_KEY, JSON.stringify(estado))
    else localStorage.removeItem(LS_KEY)
  } catch {
    /* almacenamiento no disponible */
  }
}

export const useSessionStore = defineStore('session', {
  state: () => {
    const s = cargar() || {}
    return {
      accessToken: s.accessToken ?? null,
      refreshToken: s.refreshToken ?? null,
      mustChangePassword: s.mustChangePassword ?? false,
      perfil: null,
    }
  },

  getters: {
    autenticado: (s) => Boolean(s.accessToken) && !s.mustChangePassword,
    roles: (s) => s.perfil?.roles ?? [],
    esGerencia: (s) => (s.perfil?.roles ?? []).includes('Gerencia General'),
    fotoPerfil: (s) => s.perfil?.foto_perfil_url ?? null,
    nombrePerfil: (s) => s.perfil?.nombre ?? '',
    /** {modulo: [operaciones]} ya resuelto por el backend (roles + excepciones
     * individuales) — ver `shared.guard.permisos_efectivos` (Const. Ppio IV). */
    permisos: (s) => s.perfil?.permisos ?? {},
    /** Los mismos conjuntos de rol "ve costos"/"jefe" que ya usa el backend
     * (`_ROLES_VER_COSTOS`/`_ROLES_JEFE` en tecnicos/inventario/piezas/ventas/
     * servicio_tecnico) — para ocultar en el nav pantallas que son solo cifras
     * monetarias, no una autorización nueva (el backend las sigue ocultando
     * igual si alguien entra por URL directa).
     */
    puedeVerCostos: (s) =>
      ['Gerencia General', 'Gerente de Sucursal', 'Contador', 'Administrador'].some((r) =>
        (s.perfil?.roles ?? []).includes(r),
      ),
    esJefeTecnico: (s) =>
      ['Gerencia General', 'Técnico Jefe'].some((r) => (s.perfil?.roles ?? []).includes(r)),
  },

  actions: {
    _persistir() {
      guardar({
        accessToken: this.accessToken,
        refreshToken: this.refreshToken,
        mustChangePassword: this.mustChangePassword,
      })
    },

    async login(identificacion, password) {
      const r = await apiClient.post('/auth/login', { identificacion, password })
      this.accessToken = r.access_token
      this.refreshToken = r.refresh_token ?? null
      this.mustChangePassword = Boolean(r.must_change_password)
      this._persistir()
      if (!this.mustChangePassword) await this.cargarPerfil()
      return r
    },

    async cargarPerfil() {
      this.perfil = await apiClient.get('/perfil')
    },

    async cambiarContrasena(actual, nueva) {
      await apiClient.post('/auth/cambiar-contrasena', { actual, nueva })
      this.mustChangePassword = false
      this.accessToken = null
      this.refreshToken = null
      this._persistir()
    },

    async logout() {
      try {
        await apiClient.post('/auth/logout', { refresh_token: this.refreshToken })
      } catch {
        /* sesión ya inválida */
      }
      guardar(null)
      this.accessToken = null
      this.refreshToken = null
      this.mustChangePassword = false
      this.perfil = null
    },

    /** ¿Tiene acceso al módulo `modulo` (y, si se indica, a `operacion` dentro
     * de él)? Refleja exactamente `permisos_efectivos` del backend — el
     * backend sigue siendo quien autoriza cada endpoint (Principio V), esto
     * solo evita pintar nav/rutas a las que el usuario no puede entrar. */
    puede(modulo, operacion) {
      const ops = this.permisos[modulo]
      if (!ops) return false
      return operacion ? ops.includes(operacion) : true
    },
  },
})

// Conecta el token al cliente HTTP compartido.
export function conectarSesionAlCliente(pinia) {
  const store = useSessionStore(pinia)
  setTokenProvider(() => store.accessToken)
}
