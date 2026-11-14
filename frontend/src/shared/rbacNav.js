/**
 * Predicado único de "¿puede este usuario entrar a una ruta?" — usado tanto por
 * el guard de navegación (`router/index.js`) como por el nav (`AppShell.vue`),
 * para que el menú nunca ofrezca un enlace que el guard vaya a rechazar (o
 * viceversa). La verdad sigue siendo el backend (Principio IV); esto solo
 * refleja `session.perfil.permisos` (= `shared.guard.permisos_efectivos`).
 *
 * `meta` acepta las mismas 3 llaves que ya usan los `routes.js`:
 *  - `soloGerencia: true`      → solo el rol "Gerencia General".
 *  - `modulo` (+ `operacion`)  → acceso RBAC real al módulo (y, si se indica,
 *                                a esa operación dentro de él).
 *  - `roles: [...]`            → conjunto de rol explícito (pantallas de
 *                                costos/política que no mapean 1:1 a RBAC).
 * Sin ninguna de las 3, la ruta es visible para cualquier usuario autenticado.
 */
export function puedeEntrar(session, meta = {}) {
  if (meta.soloGerencia && !session.esGerencia) return false
  if (meta.modulo && !session.esGerencia && !session.puede(meta.modulo, meta.operacion)) return false
  if (meta.roles && !meta.roles.some((r) => session.roles.includes(r))) return false
  return true
}

/**
 * Igual que `puedeEntrar`, pero además oculta del NAV (no de la ruta — sigue
 * accesible por URL directa, Const. §3 "Gerencia General: acceso total") las
 * pantallas de captura operativa que no corresponden a su portal (`meta.ocultoPortalGerencia`
 * — feedback del usuario 2026-09-10: "el gerente no es vendedor ni técnico,
 * ¿por qué su portal tiene 'nueva venta'/'registrar OT'?"). Úsalo solo en
 * `AppShell.vue`; el guard de navegación sigue usando `puedeEntrar`.
 */
export function visibleEnPortal(session, meta = {}) {
  if (meta.ocultoPortalGerencia && session.esGerencia) return false
  return puedeEntrar(session, meta)
}
