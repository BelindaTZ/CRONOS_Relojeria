"""Módulo `mermas` (feature 011): baja de relojes/piezas por daño, pérdida,
robo, defecto o caducidad de insumo, sin venta (Esp. §4.12). Costeo a costo de
adquisición, umbral de autorización de Gerencia General, baja del inventario
activo (003) + asiento de pérdida extraordinaria (010), vínculos a la OT/
técnico (008) y a la transferencia (004).

No expone API pública a otros módulos por ahora — es hoja de la cadena de
dependencias (003, 004, 008, 002, 010 la alimentan; nada consume mermas).
"""
