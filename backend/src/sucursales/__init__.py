"""Módulo `sucursales` (feature 001): CRUD de sucursales, inactivación con
aviso por correo, y horario de atención por día de semana.

API pública para otros módulos (Principio X):
- `horario_texto(db, sucursal_id)` — línea legible del horario (008/servicio
  técnico la usa en el correo de "listo para retiro").
- `datos_contacto(db, sucursal_id)` — nombre + dirección, para correos y comprobantes.
"""

from sucursales.service import datos_contacto, horario_texto

__all__ = ["datos_contacto", "horario_texto"]
