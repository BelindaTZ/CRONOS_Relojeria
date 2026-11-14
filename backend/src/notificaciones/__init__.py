"""API pública del módulo `notificaciones` (feature 014).

Las features de origen (001, 006, 007, 008) llaman `encolar()` directo en
Python — mismo patrón que el resto de integraciones entre módulos de este
backend (`clientes.cliente_mini`, `tecnicos.datos_para_correo`, etc., Ppio X) —
en vez de un viaje HTTP a `/_internal/notificaciones/encolar` (que también
existe, para pruebas/uso operativo manual).
"""

from notificaciones.service import cancelar_pendiente, encolar, puede_enviar

__all__ = ["encolar", "cancelar_pendiente", "puede_enviar"]
