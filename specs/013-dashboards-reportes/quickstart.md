# Quickstart: Dashboards y Reportes

**Feature**: `013-dashboards-reportes` | **Phase**: 1

## Prerrequisitos

- 000–012 implementadas; warehouse de 012 poblado (corrida ELT ejecutada); datos operativos o fixtures
- Usuarios: "Gerencia General", "Gerente de Sucursal", un vendedor

## Escenarios

### V1 — Panel principal (US1)
```bash
curl "/panel?periodo=2026-09" -H "Authorization: Bearer <gerencia>"
```
- **Esperado**: 6 KPIs (margen, rentabilidad por sucursal, CxC vencidas, rotación de stock, productividad de técnicos, clientes por nivel), cada uno con valor, tendencia y `drill_down`; el frontend los carga de forma asíncrona (skeletons); ≤ 8–10 KPIs.

### V2 — Reporte analítico con filtros (US2)
```bash
curl "/reportes/margen-por-marca?periodo=2026-09&sucursal_id=1" -H "Authorization: Bearer <admin>"
```
- **Esperado**: `tipo_grafico: barras`; cambiar `periodo` o `sucursal_id` actualiza sin botón "Buscar"; una distribución (`clientes-por-nivel`) devuelve `tipo_grafico: pastel`; una tendencia (`rotacion-stock`) devuelve `lineas`.

### V3 — Tipos de gráfico (US3)
- Verificar en el frontend que cada reporte usa `vue-echarts` con el tipo correcto y que no se carga ninguna otra librería de gráficos.

### V4 — Degradación (US3)
```bash
docker compose stop clickhouse
curl "/reportes/margen-por-marca?periodo=2026-09"
curl "/panel?periodo=2026-09"
curl /relojes   # operativo intacto
```
- **Esperado**: `{disponible: false, motivo, frescura}` sin stack trace; el frontend muestra "Datos analíticos no disponibles — última actualización: …"; la navegación operativa sigue funcionando.

### V5 — Sello de frescura y "actualizar ahora" (US1)
```bash
curl /reportes/estado-frescura
curl -XPOST /reportes/actualizar-ahora -H "Authorization: Bearer <admin>"
```
- **Esperado**: "actualizado a HH:MM" por dominio; el botón dispara una corrida real del DAG (012).

### V6 — Índice de reportes simples (US4)
```bash
curl /reportes/indice -H "Authorization: Bearer <vendedor>"
curl /reportes/indice -H "Authorization: Bearer <admin>"
```
- **Esperado**: el vendedor ve solo reportes operativos permitidos (agenda, inventario, historial de cliente/reloj) y no los complejos; el admin ve todo, incluido el informe de servicios de 008.

### V7 — Drill-down (US1)
- En el panel, pulsar el KPI "CxC vencidas".
- **Esperado**: navega a `/contabilidad/cxc?estado=vencida` (flujo real de 010), no un mensaje.

### V8 — Exportación (US6)
```bash
curl "/reportes/margen-por-marca/exportar?formato=xlsx&periodo=2026-09" -o margen.xlsx
curl "/reportes/aging-cxc/exportar?formato=pdf" -o aging.pdf
```
- **Esperado**: CSV/Excel/PDF disponibles; un reporte con > 5 000 filas solo ofrece CSV.

### V9 — Scope por sucursal (US)
```bash
curl "/reportes/rentabilidad-neta-sucursal?periodo=2026-09" -H "Authorization: Bearer <gerente_A>"
```
- **Esperado**: el gerente de A solo ve A; Gerencia General ve consolidado o filtra.

## Contratos

- [`contracts/dashboards.openapi.yaml`](./contracts/dashboards.openapi.yaml)

## Criterio de "listo"

V1–V9 pasan; los 18 reportes de §4.11.2 accesibles con su gráfico; panel asíncrono; degradación limpia; drill-downs abren flujos reales.
