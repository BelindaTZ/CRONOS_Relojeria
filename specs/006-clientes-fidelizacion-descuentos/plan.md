# Implementation Plan: Clientes, Fidelización y Descuentos

**Branch**: `006-clientes-fidelizacion-descuentos` | **Date**: 2026-09-10 | **Spec**: [spec.md](./spec.md)

## Summary

CRM básico de clientes (§4.8) con identificación (cédula/RUC), **número de afiliado** único autogenerado, **casilla de consentimiento LOPDP**, y edición de identificación solo con rol elevado. **Programa de fidelización**: niveles configurables (nombre, criterio monto/frecuencia/combinación, umbrales, beneficios), **motor de recálculo** del nivel al registrarse una compra o servicio, historial de cambios de nivel, recálculo en cascada al cambiar umbrales. **Descuentos generales y cupones** (§4.8.2), **mutuamente excluyentes** en una misma operación. **Servicio compartido de margen mínimo protegido**: dado un ítem y su costo, calcula el precio final y el margen resultante y **bloquea o exige autorización de Gerencia General** si cae bajo el mínimo configurable — siempre en backend (Const. Ppio V). Reportes operativos: clientes por nivel, mejores clientes, historial de cliente.

## Technical Context

**Language/Version**: Python 3.12 / FastAPI, Vue 3

**Primary Dependencies**: SQLAlchemy 2.x, Alembic; `shared/guard`, `shared/auditoria`, `shared/parametros` (niveles, márgenes mínimos); expone `shared/descuentos` (servicio consumido por 008 y 009)

**Storage**: PostgreSQL

**Testing**: `pytest` — **cobertura obligatoria (Const. Ppio IX)**: cálculo de nivel de fidelización, margen mínimo protegido tras descuentos/cupones

**Project Type**: Web — módulo `clientes` (+ `shared/descuentos`)

**Performance Goals**: alta de cliente < 2 min; recálculo de nivel < 300 ms; validación de margen mínimo < 100 ms

**Constraints**: descuento + cupón nunca juntos; margen mínimo siempre validado en backend; identificación única; consentimiento obligatorio al alta

**Scale/Scope**: cientos de clientes, decenas de descuentos/cupones activos

## Constitution Check

| Principio | Cumplimiento |
|---|---|
| I | FR citan §4.8, §4.8.1, §4.8.2, §9.1, §9.4, §7. ✅ |
| II | Clientes, niveles, descuentos, aplicaciones y autorizaciones son registros reales. ✅ |
| III | PostgreSQL OLTP. ✅ |
| IV | Módulo `clientes_fidelizacion`; autorización de margen mínimo por Gerencia General, auditada. ✅ |
| V | Nivel y margen mínimo **siempre en backend**. ✅ |
| VI | Referencia 001, 008, 009; no los redefine. ✅ |
| VII | Motor de nivel/descuentos como parámetros tipados; sin motor de reglas externo. ✅ |
| VIII | De corrido tras aprobación. ✅ |
| IX | **Cobertura obligatoria** de nivel y margen mínimo. ✅ |
| X | `clientes/` con capas; `shared/descuentos` reutilizable. ✅ |
| XI | Búsqueda multi-criterio; selectores sin texto libre; exportación; consentimiento como casilla. ✅ |
| XII | Pantallas con `ui-ux-pro-max`. ✅ |

**Resultado**: PASS.

## Project Structure

```text
backend/src/
├── clientes/
│   ├── router.py     # /clientes, /clientes/{id}/historial, /niveles, /descuentos, /cupones
│   ├── service.py    # CRM, motor de nivel, historial de nivel, reportes operativos
│   ├── nivel.py      # cálculo puro del nivel a partir del histórico
│   ├── repository.py
│   └── schemas.py
└── shared/descuentos/
    ├── aplicar.py    # aplicar_descuento(item, costo, descuento|cupon) -> {precio_final, margen, decision}
    └── margen_minimo.py  # valida contra parámetro; devuelve permitir|bloquear|requiere_autorizacion

frontend/src/clientes/
├── components/ (ListaClientes, FichaCliente, HistorialCliente, ConfigNiveles, PanelDescuentos, PanelCupones)
├── composables/ stores/ services/
```

**Structure Decision**: Módulo `clientes` + utilidad `shared/descuentos` (el servicio de margen mínimo y aplicación de descuento lo consumen 008 y 009). El motor de nivel es una función pura en `nivel.py` para poder testearlo con fixtures antes de que existan 008/009.

## Complexity Tracking

| Elemento | Por qué | Alternativa más simple rechazada porque |
|---|---|---|
| Motor de nivel + recálculo en cascada | §4.8.1 (recálculo automático) + decisión del negocio | Nivel fijo o manual: viola §4.8.1 |
| `shared/descuentos` con estados (permitir/bloquear/autorizar) | §4.8.2 (margen mínimo protegido con bloqueo o autorización) | Solo bloquear: el negocio quiere permitir con autorización explícita |
