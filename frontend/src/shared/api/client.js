/**
 * Cliente HTTP único de CRONOS (Principio V y X).
 *
 * NINGUNA llamada a la API vive fuera de una capa `services/` de un módulo, y
 * todas esas capas usan este cliente. Aquí se centraliza: base URL, cabeceras,
 * el interceptor de error (formato `{ error: { code, message, field } }` del
 * backend) y el punto donde 001 inyectará el token JWT.
 */

const BASE_URL = (import.meta.env?.VITE_API_BASE_URL ?? 'http://localhost:8000').replace(/\/$/, '')

/** Error normalizado que lanzan todas las llamadas al fallar. */
export class ApiError extends Error {
  constructor(message, { status, code, field, data } = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code ?? 'error'
    this.field = field ?? null
    this.data = data ?? null
  }
}

// Punto de extensión para 001: proveedor del token de acceso.
let tokenProvider = () => null

/** 001 registra aquí cómo obtener el JWT actual. */
export function setTokenProvider(fn) {
  tokenProvider = typeof fn === 'function' ? fn : () => null
}

async function request(method, path, { body, params, headers } = {}) {
  const url = new URL(BASE_URL + path)
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null) url.searchParams.set(k, String(v))
    }
  }

  const finalHeaders = { Accept: 'application/json', ...headers }
  const token = tokenProvider()
  if (token) finalHeaders.Authorization = `Bearer ${token}`

  let payload
  if (body !== undefined) {
    finalHeaders['Content-Type'] = 'application/json'
    payload = JSON.stringify(body)
  }

  let response
  try {
    response = await fetch(url, { method, headers: finalHeaders, body: payload })
  } catch (cause) {
    throw new ApiError('No se pudo contactar al servidor.', { status: 0, code: 'network_error' })
  }

  const isJson = (response.headers.get('content-type') ?? '').includes('application/json')
  const data = isJson ? await response.json().catch(() => null) : null

  if (!response.ok) {
    const err = data?.error ?? {}
    throw new ApiError(err.message ?? `Error ${response.status}`, {
      status: response.status,
      code: err.code,
      field: err.field,
      data,
    })
  }

  return data
}

/** Envío multipart (subida de archivos). Reutiliza el token del cliente. */
async function requestForm(method, path, formData) {
  const headers = { Accept: 'application/json' }
  const token = tokenProvider()
  if (token) headers.Authorization = `Bearer ${token}`
  let response
  try {
    response = await fetch(BASE_URL + path, { method, headers, body: formData })
  } catch {
    throw new ApiError('No se pudo contactar al servidor.', { status: 0, code: 'network_error' })
  }
  const data = (response.headers.get('content-type') ?? '').includes('application/json')
    ? await response.json().catch(() => null)
    : null
  if (!response.ok) {
    const err = data?.error ?? {}
    throw new ApiError(err.message ?? `Error ${response.status}`, {
      status: response.status,
      code: err.code,
      field: err.field,
      data,
    })
  }
  return data
}

export const apiClient = {
  get: (path, opts) => request('GET', path, opts),
  post: (path, body, opts) => request('POST', path, { ...opts, body }),
  put: (path, body, opts) => request('PUT', path, { ...opts, body }),
  patch: (path, body, opts) => request('PATCH', path, { ...opts, body }),
  delete: (path, opts) => request('DELETE', path, opts),
  patchForm: (path, formData) => requestForm('PATCH', path, formData),
  postForm: (path, formData) => requestForm('POST', path, formData),
  baseUrl: BASE_URL,
}
