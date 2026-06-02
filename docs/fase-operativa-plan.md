# AppMedica — Fase operativa: plan de implementación

**Dirección de producto:** tablero administrativo y económico del consultorio (no EMR hospitalario).

**Criterio:** velocidad, claridad, pocos clics, reemplazar Excel. Sin IA, móvil ni automatizaciones complejas en esta fase.

---

## Estado actual (base sólida)

| Capa | Qué existe |
|------|------------|
| Datos | `Payment`, `InsuranceClaim`, `Appointment` con cierre administrativo |
| Deuda particular | Suma de `Payment.status = pending` |
| Deuda OS | Suma de claims `pending` + `invoiced` |
| Cobro parcial | Múltiples `Payment` por turno; `add_payment` reduce pending |
| UI | Agenda cierra/cobra; OS tiene reclamos+ranking; **no hay `/payments`** |
| Seguridad | JWT + tenant; **sin RBAC** |
| Calidad | `test_core_flow.py` manual; **sin pytest/CI** |

## Deuda técnica detectada

1. No hay capa unificada “cobros/deuda” (lógica repartida en dashboard, agenda, OS).
2. Menú `/payments` y `/reports` visibles pero vacíos.
3. Errores 401 y empty states inconsistentes en frontend.
4. Roles en BD sin enforcement.
5. Sin export → usuarios mantienen Excel para contador/listas.
6. `AppointmentClosureService` monolítico (refactor posterior, no bloqueante).

## Riesgos

| Riesgo | Mitigación |
|--------|------------|
| Duplicar lógica de deuda | Un `CollectionsService` como única fuente para `/payments` |
| Romper cierre en agenda | Reutilizar `add_payment_to_appointment`; no duplicar reglas |
| RBAC incompleto frustra equipos | 3 roles, ~6 reglas; documentar en UI |
| Scope creep | Bloques con criterio de “done” cada uno |
| Ranking OS sin datos | Cobros enlaza a reclamos; no mezclar flujos |

## Bloques de implementación

### Bloque 1 — Cobros (`/payments`) ✅

- API `GET /payments/summary`, `GET /payments/items?tab=`
- Pantalla: resumen, tabs (particulares | OS | recientes | pendientes), tabla, acciones rápidas
- Reutilizar cobro desde agenda (`POST .../payments`)

**Done cuando:** consultorio ve deuda y cobra sin ir turno por turno en agenda.

### Bloque 2 — Exportación ✅

- `GET /exports/{resource}?format=xlsx|csv`
- Botones en Pacientes y Cobros

### Bloque 3 — RBAC mínimo ✅ (parcial)

- `require_role`, filtros professional en agenda/cobros
- staff: no DELETE pacientes
- owner: todo

### Bloque 4 — Tests + CI ✅ (inicial)

- pytest: `tests/test_collections_service.py`
- GitHub Actions: `.github/workflows/ci.yml`

### Bloque 5 — UX + alertas dashboard

- 401 global, empty/loading unificados
- Cards alerta: sin cerrar, reclamos viejos

### Bloque 6 — Reportes básicos (opcional post-validación)

- Resumen mensual texto + export

---

## Orden acordado

1. Cobros → 2. Export → 3. RBAC → 4. Tests/CI → 5. UX → 6. Reportes
