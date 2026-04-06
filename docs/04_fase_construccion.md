# Fase 4 — Construcción del Data Warehouse

**Punteo: 10 pts**  
**Objetivo:** Implementar el Data Warehouse usando SQLite con el esquema estrella diseñado en la Fase 3.

---

## 4.1 Tecnología Seleccionada

| Componente | Tecnología | Justificación |
|------------|-----------|---------------|
| Motor de BD | SQLite 3.x | Cero configuración, portable, suficiente para el volumen de datos |
| ORM | Python sqlite3 nativo | Sin dependencias adicionales |
| Lenguaje ETL | Python 3.11 | Ecosistema maduro para análisis de datos |
| Almacenamiento | Archivo `.db` local | Facilita portabilidad del proyecto |

---

## 4.2 Estructura del Data Warehouse

```
igss_salud_dw.db
│
├── DIMENSIONES
│   ├── dim_tiempo          (12 años + 24 registros mensuales)
│   ├── dim_departamento    (23 departamentos de Guatemala)
│   └── dim_servicio        (5 tipos de servicio médico)
│
├── HECHOS
│   ├── fact_costos         (Costos unitarios por servicio y año)
│   └── fact_ejecucion      (Egresos/ingresos por departamento y año)
│
├── AUDITORÍA
│   └── red_flags_log       (Alertas automáticas detectadas)
│
└── VISTAS (DATA MARTS)
    ├── dm_costos           (Análisis de anomalías en costos)
    ├── dm_ejecucion        (Análisis financiero con niveles de riesgo)
    └── strategic_mart_kpis (KPIs ejecutivos nacionales)
```

---

## 4.3 Proceso de Construcción

### Paso 1: Creación del esquema
```bash
python src/warehouse/carga_dw.py
```
Ejecuta `sql/crear_esquema.sql` que crea todas las tablas, índices y vistas.

### Paso 2: Verificación del DW
```sql
-- Verificar conteos
SELECT 'dim_tiempo'        AS tabla, COUNT(*) AS registros FROM dim_tiempo
UNION ALL
SELECT 'dim_departamento', COUNT(*) FROM dim_departamento
UNION ALL
SELECT 'fact_costos',      COUNT(*) FROM fact_costos
UNION ALL
SELECT 'fact_ejecucion',   COUNT(*) FROM fact_ejecucion;
```

---

## 4.4 Validaciones de Integridad

| Validación | Query | Resultado Esperado |
|-----------|-------|-------------------|
| Sin huérfanos en fact_costos | `SELECT COUNT(*) FROM fact_costos WHERE id_departamento NOT IN (SELECT id_departamento FROM dim_departamento)` | 0 |
| Sin huérfanos en fact_ejecucion | `SELECT COUNT(*) FROM fact_ejecucion WHERE id_tiempo NOT IN (SELECT id_tiempo FROM dim_tiempo)` | 0 |
| Montos positivos | `SELECT COUNT(*) FROM fact_ejecucion WHERE egresos_q < 0` | 0 |
| Ratios válidos | `SELECT COUNT(*) FROM fact_ejecucion WHERE ratio_ei < 0` | 0 |

---

## 4.5 Consultas Analíticas Clave

Ver archivo `sql/consultas_analiticas.sql` para el catálogo completo.

### Top 5 departamentos con mayor brecha en 2025
```sql
SELECT d.nombre, fe.egresos_q, fe.ingresos_q, fe.brecha_q, fe.nivel_riesgo
FROM fact_ejecucion fe
JOIN dim_departamento d ON fe.id_departamento = d.id_departamento
JOIN dim_tiempo t ON fe.id_tiempo = t.id_tiempo
WHERE t.anio = 2025 AND d.id_departamento != 30
ORDER BY fe.brecha_q DESC
LIMIT 5;
```

### Años con costos de hospitalización atípicos
```sql
SELECT t.anio, fc.costo_unitario_q, fc.z_score
FROM fact_costos fc
JOIN dim_tiempo t ON fc.id_tiempo = t.id_tiempo
JOIN dim_servicio s ON fc.id_servicio = s.id_servicio
WHERE s.codigo = 'HOSP' AND fc.es_outlier = TRUE
ORDER BY fc.z_score DESC;
```
