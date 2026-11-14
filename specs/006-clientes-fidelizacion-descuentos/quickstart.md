# Quickstart: Clientes, Fidelización y Descuentos

**Feature**: `006-clientes-fidelizacion-descuentos` | **Phase**: 1

## Prerrequisitos

- 000, 001 implementadas; migración `0011_clientes` aplicada; parámetros y nivel base sembrados
- Fixtures de transacciones en `backend/tests/fixtures/transacciones_cliente.json` (008/009 pueden no existir aún)

## Escenarios

### V1 — Ficha de cliente (US1)
```bash
curl -XPOST /clientes -d '{"tipo":"natural","identificacion":"1712345678","nombre":"A. Ríos","email":"a@x.com","consentimiento":{"aceptado":true,"version_texto":1}}'
```
- **Esperado**: creado con `numero_afiliado` autogenerado; nivel base; sin `consentimiento.aceptado=true` → 422; identificación duplicada → 409; búsqueda por nombre/cédula/email/afiliado lo encuentra.

### V2 — Configurar niveles (US2)
```bash
curl -XPOST /niveles -d '{"nombre":"Plata","orden":2,"beneficios":{"desc_servicio":0.1},"regla":{"criterio":"monto_acumulado","ventana_meses":12,"umbral_monto":5000}}'
```

### V3 — Recálculo del nivel (US3)
```bash
curl -XPOST /_internal/fidelizacion/recalcular -d '{"cliente_id":1,"hecho":"venta","documento_id":99}'
```
- **Esperado**: con histórico que supera 5000 en 12 meses → sube a Plata; `historial_nivel_cliente` registra el cambio con `hecho_disparador`; si el nivel no cambia, no se crea registro.

### V4 — Recálculo masivo (US3)
```bash
curl -XPUT /niveles/2/regla -d '{"umbral_monto":4000}'
```
- **Esperado**: job diferido reclasifica a todos; historial previo conservado; auditoría.

### V5 — Margen mínimo protegido (US4) 🔒
```bash
curl -XPOST /_internal/descuentos/aplicar -d '{"item_ref":"OMEGA-310","costo":6000,"precio_lista":8000,"descuento":{"tipo":"porcentaje","valor":0.3}}'
```
- **Esperado**: con `margen_minimo` global 15% sobre costo → precio_final 5600, margen −400 < mínimo → `decision: "bloquear"` (o `"requiere_autorizacion"` según política). Con autorización registrada → `permitir` y `autorizacion_margen_minimo` creada.
- Todo cálculo devuelto por el backend; un intento de forzar `margen_resultante` desde el cliente se ignora.

### V6 — Descuento vs. cupón exclusivos (US5)
```bash
curl -XPOST /_internal/descuentos/aplicar -d '{"item_ref":"X","costo":100,"precio_lista":150,"descuento":{...},"cupon":{...}}'   # 422
```
- **Esperado**: pasar descuento **y** cupón → 422 (mutuamente excluyentes).

### V7 — Cupón de uso único (US5)
```bash
curl -XPOST /cupones -d '{"codigo":"CUMPLE-001","cliente_id":1,"tipo":"porcentaje","valor":0.1,"alcance":"tienda","limite_uso":"una_vez","vigencia_fin":"2026-12-31"}'
# consumir 2 veces en paralelo
```
- **Esperado**: solo un consumo pasa; el segundo → 409; estado `usado`; cupón vencido → 409.

### V8 — Reportes (US6)
```bash
curl /reportes/clientes-por-nivel
curl "/reportes/mejores-clientes?top=20"
curl /clientes/1/historial
```
- **Esperado**: distribución por nivel cuadra con niveles vigentes; top por Σ compras+servicios; historial con compras, servicios y citas; exportable.

## Contratos

- [`contracts/clientes.openapi.yaml`](./contracts/clientes.openapi.yaml)
- [`contracts/descuentos.openapi.yaml`](./contracts/descuentos.openapi.yaml)

## Criterio de "listo"

V1–V8 pasan; **pruebas de cálculo de nivel y de margen mínimo protegido verdes (Const. Ppio IX)**.

### V9 — Clientes en riesgo de abandono (ampliación)
```bash
curl /reportes/clientes-en-riesgo
curl -XPOST /cupones/reactivacion -d '{"cliente_id":1,"tipo":"porcentaje","valor":0.15}'
```
- **Esperado**: solo clientes Plata/Oro cuyo silencio supera su cadencia propia × 2 y el piso de 90 días (con ≥ 3 transacciones en la ventana de 24 meses). El cupón se emite como `REACT-<afiliado>`, uso único, vigencia 60 días por defecto.
