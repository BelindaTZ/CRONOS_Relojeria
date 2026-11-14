# Data Model: Dashboards y Reportes

**Feature**: `013-dashboards-reportes` | **Phase**: 1 | **Date**: 2026-09-10

Esta feature **no crea entidades OLTP**. Toda la lectura es sobre el warehouse de ClickHouse (012). Se documentan las estructuras de configuración y los contratos de respuesta.

## Configuración (código, no tablas)

### Catálogo de reportes (`warehouse.py`)
| Campo | Descripción |
|---|---|
| `slug` | identificador estable del reporte (ej. `margen-por-marca`) |
| `titulo` | nombre visible |
| `modelo_ch` | tabla/vista de ClickHouse que lo alimenta |
| `filtros_soportados` | subconjunto de {periodo, sucursal, marca, tecnico} |
| `tipo_grafico` | `barras` \| `pastel` \| `lineas` \| `kpi` \| `tabla` |
| `permiso` | (módulo `reportes`, operación `consultar`) + audiencia (gerencia/admin) |

Los 18 `slug` cubren §4.11.2 (ver `research.md` D3 y `data-model.md` de 012).

### Definición del panel (`service.py`)
Lista fija de 6 KPIs (§4.11.3), cada uno: `{clave, titulo, modelo_ch, formato, drill_down}`.

### Índice de reportes simples (`service.py`)
Lista de §4.11.1 con `{titulo, modulo, ruta, permiso}` — enlaces, no reimplementación.

## Contratos de respuesta

### KPI del panel
```
{ clave, titulo, valor, unidad, tendencia: {valor, direccion}, drill_down: {tipo, ruta, filtros} }
```

### Reporte analítico
```
{ slug, titulo, tipo_grafico, filtros_aplicados,
  series: [...], categorias: [...], filas: [...],   // según tipo
  total_filas, frescura: {dominio, ultima_carga_ts},
  disponible: bool }
```

### Estado degradado
```
{ disponible: false, motivo, frescura: {ultima_carga_ts} }
```

## Reglas (backend, fachada)

1. El backend operativo NO agrega datos; `warehouse.py` es la única puerta a ClickHouse (solo lectura).
2. `scope_sucursal` aplicado a todo `slug` con filtro de sucursal.
3. Si ClickHouse/Airflow no responden ⇒ respuesta `disponible: false` (nunca 500 con stack trace).
4. Panel ≤ 8–10 KPIs (fijado en 6).
5. Exportación: > 5 000 filas ⇒ solo CSV.
6. Todo `drill_down` apunta a un flujo o pantalla real con contexto.

## Nota

`GET /reportes/estado-frescura` y `POST /reportes/actualizar-ahora` son de 012; 013 los consume.
