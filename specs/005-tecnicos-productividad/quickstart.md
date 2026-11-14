# Quickstart: Técnicos y Productividad

**Feature**: `005-tecnicos-productividad` | **Phase**: 1

## Prerrequisitos

- 000, 001, 004 implementadas; migración `0010_tecnicos` aplicada; parámetro `horas_productivas_estandar_mes` sembrado
- Usuario con permiso administrativo en `tecnicos`; fixtures de OT (008 puede no existir aún → usar `backend/tests/fixtures/ordenes_trabajo.json`)

## Escenarios

### V1 — Ficha de técnico y costo (US1)
```bash
curl -XPOST /tecnicos -d '{"nombre":"J. Pérez","especialidades":["Rolex","Omega"],"sucursales":[1],"usuario_id":12}'
curl -XPOST /tecnicos/1/costo -d '{"sueldo_mensual":1600,"vigente_desde":"2026-09-01"}'
curl /tecnicos/1 -H "Authorization: Bearer <no_admin>"   # sin sueldo_mensual
```
- **Esperado**: creado; `tarifa_hora = 1600/160 = 10`; el costo interno no es visible para roles no administrativos.

### V2 — Definir esquema de bono (US2)
```bash
curl -XPOST /reglas-bono -d '{"nombre":"Bono 2026","periodicidad":"mensual","componentes":[
  {"tipo":"monto_por_meta","indicador":"ot_completadas","umbral":20,"valor":200},
  {"tipo":"porcentaje_margen","indicador":"margen_generado","umbral":0,"valor":0.05}]}'
```
- **Esperado**: regla vigente y auditada.

### V3 — Cálculo del bono (US3)
```bash
curl -XPOST /periodos-liquidacion -d '{"fecha_inicio":"2026-09-01","fecha_fin":"2026-09-30"}'
curl -XPOST /bonos/calcular -d '{"periodo_id":1,"tecnico_id":1}'    # usa fixtures de OT
curl /bonos?periodo_id=1&tecnico_id=1
```
- **Esperado**: con 22 OT completadas y margen X, `valor_total = 200 + 0.05·X`; `desglose` por indicador; `estado=preliminar`; `bono_ot` prorrateado por `costo_mo_ot`. Técnico sin OT → `valor_total = 0`.

### V4 — Recálculo por parámetro (US3)
```bash
curl -XPUT /parametros/horas_productivas_estandar_mes -d '{"valor":170,"ambito_tipo":"global"}'
```
- **Esperado**: `bono_acumulado` de periodos **abiertos** se recalcula (tarifa horaria cambió); un periodo **cerrado** no se toca; cambio auditado.

### V5 — Costo de MO por OT (contrato para 008)
```bash
curl -XPOST /_internal/costeo/costo-mo-ot -d '{"tecnico_id":1,"horas":3,"tipo_reparacion":"servicio_completo"}'
```
- **Esperado**: `10 × 3 = 30`; sin `horas` → `10 × tiempo_estimado(servicio_completo)`.

### V6 — Productividad operativa (US5)
```bash
curl "/productividad?periodo_id=1"
```
- **Esperado**: por técnico: OT completadas, tiempo promedio, margen generado, bono alcanzado; exportable CSV/Excel/PDF.

### V7 — Restricciones del técnico
```bash
curl -XPATCH /tecnicos/1 -H "Authorization: Bearer <el_propio_tecnico>" -d '{"sueldo_mensual":2000}'   # 403
curl -XPATCH /tecnicos/1/estado -H "Authorization: Bearer <el_propio_tecnico>" -d '{"estado":"inactivo"}' # 403
```

## Contratos

- [`contracts/tecnicos.openapi.yaml`](./contracts/tecnicos.openapi.yaml)

## Criterio de "listo"

V1–V7 pasan; **pruebas del cálculo de bono, tarifa horaria y prorrateo verdes (Const. Ppio IX)**.
