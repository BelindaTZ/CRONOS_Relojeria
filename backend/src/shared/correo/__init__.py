"""Capacidad compartida de correo con plantillas (Principio XI).

API pública: `enviar(plantilla, a, contexto)`. En 001 los envíos son directos;
014 añade cola, reintentos, panel de entregas y opt-out.
"""

from shared.correo.service import enviar

__all__ = ["enviar"]
