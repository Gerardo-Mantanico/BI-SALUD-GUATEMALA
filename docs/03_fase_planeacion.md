# Fase 3 — Planeación (Modelo Dimensional)

**Punteo: 10 pts**  
**Objetivo:** Diseñar el modelo dimensional (esquema estrella) del Data Warehouse para el análisis de salud y corrupción en el IGSS.

---

## 3.1 Decisiones de Arquitectura

### Tipo de Modelo: Esquema Estrella

Se elige el **esquema estrella** sobre el copo de nieve por las siguientes razones:
- Los datos del IGSS son relativamente simples y no requieren normalización adicional en las dimensiones.
- El esquema estrella es más eficiente para consultas analíticas con GROUP BY y agregaciones.
- Facilita la creación de cubos OLAP sin complejidad adicional.
- El volumen de datos (miles, no millones de registros) no justifica la complejidad del copo de nieve.

### Capas del Data Warehouse

```
ODS (Operational Data Store)     → Datos limpios, estructura fuente
Data Warehouse (DW)              → Modelo estrella, histórico
Data Mart (DM) - Costos          → Análisis de costos y anomalías  
Data Mart (DM) - Ejecución       → Análisis financiero por departamento
Strategic Mart                   → KPIs ejecutivos consolidados
```

---

## 3.2 Modelo Dimensional — Esquema Estrella

### Diagrama del Modelo

```
                    dim_tiempo
                    ─────────
                    id_tiempo (PK)
                    anio
                    mes
                    trimestre
                         │
                         │
dim_departamento         │              dim_servicio
────────────────    ─────┼─────    ────────────────
id_departamento (PK)─────┤         id_servicio (PK)
nombre_departamento      │         nombre_servicio
region                   │         descripcion
poblacion_estimada        │
                    ──────────────────────────────
                         FACT_COSTOS
                    ──────────────────────────────
                    id_hecho (PK)
                    id_departamento (FK)
                    id_tiempo (FK)
                    id_servicio (FK)
                    costo_total_q
                    costo_unitario_q
                    cantidad_atenciones
                    es_outlier
                    z_score
                    ──────────────────────────────
                    
                    
dim_departamento         
────────────────    ──────────────────────────────
id_departamento (PK)     FACT_EJECUCION
                    ──────────────────────────────
                    id_hecho (PK)
                    id_departamento (FK)
                    id_tiempo (FK)
                    egresos_q
                    ingresos_q
                    brecha_q
                    ratio_ei
                    flag_anomalia
                    ──────────────────────────────
```

---

## 3.3 Definición de Tablas de Hechos

### FACT_COSTOS — Costos de Atención Médica

**Granularidad:** Un registro por departamento, año, mes y tipo de servicio.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| id_hecho | INTEGER PK | Llave primaria surrogada |
| id_departamento | INTEGER FK | Referencia a dim_departamento |
| id_tiempo | INTEGER FK | Referencia a dim_tiempo |
| id_servicio | INTEGER FK | Referencia a dim_servicio |
| costo_total_q | DECIMAL(15,2) | Costo total del período en Quetzales |
| costo_unitario_q | DECIMAL(10,2) | Costo por atención en Quetzales |
| cantidad_atenciones | INTEGER | Número de atenciones prestadas |
| es_outlier | BOOLEAN | True si Z-score > 2.5 |
| z_score | DECIMAL(6,4) | Puntuación Z del costo unitario |

### FACT_EJECUCION — Ejecución Presupuestaria

**Granularidad:** Un registro por departamento y año.

| Columna | Tipo | Descripción |
|---------|------|-------------|
| id_hecho | INTEGER PK | Llave primaria surrogada |
| id_departamento | INTEGER FK | Referencia a dim_departamento |
| id_tiempo | INTEGER FK | Referencia a dim_tiempo |
| egresos_q | DECIMAL(15,2) | Gastos ejecutados en Quetzales |
| ingresos_q | DECIMAL(15,2) | Recaudación en Quetzales |
| brecha_q | DECIMAL(15,2) | Diferencia egresos - ingresos |
| ratio_ei | DECIMAL(6,4) | Egresos / Ingresos |
| flag_anomalia | BOOLEAN | True si ratio > 4.0 |

---

## 3.4 Definición de Tablas de Dimensiones

### dim_tiempo

| Columna | Tipo | Descripción |
|---------|------|-------------|
| id_tiempo | INTEGER PK | Llave primaria surrogada |
| anio | INTEGER | Año (2014–2025) |
| mes | INTEGER | Mes (1–12), NULL para datos anuales |
| nombre_mes | VARCHAR(20) | Nombre del mes en español |
| trimestre | INTEGER | Trimestre (1–4) |
| es_anual | BOOLEAN | True si el registro es anual |

### dim_departamento

| Columna | Tipo | Descripción |
|---------|------|-------------|
| id_departamento | INTEGER PK | Código oficial del departamento (1–22) |
| nombre | VARCHAR(50) | Nombre del departamento |
| region | VARCHAR(30) | Región (Metropolitana, Norte, etc.) |
| poblacion_2025 | INTEGER | Estimación de población |
| latitud | DECIMAL(8,6) | Coordenada para mapas |
| longitud | DECIMAL(9,6) | Coordenada para mapas |

### dim_servicio

| Columna | Tipo | Descripción |
|---------|------|-------------|
| id_servicio | INTEGER PK | Llave primaria surrogada |
| codigo | VARCHAR(10) | Código del servicio (HOSP, CE, EMERG, PA) |
| nombre | VARCHAR(50) | Hospitalización, Consulta Externa, etc. |
| descripcion | TEXT | Descripción del servicio |

---

## 3.5 Data Marts

### DataMart 1: Análisis de Costos (dm_costos)

**Propósito:** Detectar anomalías en los costos de atención médica.

**Vista principal:**
```sql
CREATE VIEW dm_costos AS
SELECT 
    t.anio,
    d.nombre AS departamento,
    s.nombre AS servicio,
    f.costo_unitario_q,
    f.z_score,
    f.es_outlier,
    LAG(f.costo_unitario_q) OVER (
        PARTITION BY f.id_departamento, f.id_servicio 
        ORDER BY t.anio
    ) AS costo_anio_anterior,
    ROUND(
        (f.costo_unitario_q - LAG(f.costo_unitario_q) OVER (
            PARTITION BY f.id_departamento, f.id_servicio 
            ORDER BY t.anio
        )) / LAG(f.costo_unitario_q) OVER (
            PARTITION BY f.id_departamento, f.id_servicio 
            ORDER BY t.anio
        ) * 100, 2
    ) AS variacion_pct
FROM fact_costos f
JOIN dim_tiempo t ON f.id_tiempo = t.id_tiempo
JOIN dim_departamento d ON f.id_departamento = d.id_departamento
JOIN dim_servicio s ON f.id_servicio = s.id_servicio;
```

### DataMart 2: Análisis Financiero (dm_ejecucion)

**Propósito:** Monitorear la brecha ingresos-egresos y flags de alerta financiera.

```sql
CREATE VIEW dm_ejecucion AS
SELECT 
    t.anio,
    d.nombre AS departamento,
    d.region,
    e.egresos_q,
    e.ingresos_q,
    e.brecha_q,
    e.ratio_ei,
    e.flag_anomalia,
    CASE 
        WHEN e.ratio_ei > 6 THEN 'CRÍTICO'
        WHEN e.ratio_ei > 4 THEN 'ALTO'
        WHEN e.ratio_ei > 2 THEN 'MODERADO'
        ELSE 'NORMAL'
    END AS nivel_riesgo
FROM fact_ejecucion e
JOIN dim_tiempo t ON e.id_tiempo = t.id_tiempo
JOIN dim_departamento d ON e.id_departamento = d.id_departamento;
```

### Strategic Mart: KPIs Ejecutivos

| KPI | Fórmula | Umbral Alerta |
|-----|---------|---------------|
| Costo medio hospitalización | AVG(costo_unitario) WHERE servicio='HOSP' | > Q10,000 |
| Variación interanual de costos | (costo_t - costo_t-1) / costo_t-1 | > 30% |
| Brecha financiera promedio nacional | AVG(brecha_q) | > Q200M |
| % departamentos en alerta | COUNT(flag=TRUE) / COUNT(*) | > 25% |
| Índice de concentración de gasto | HHI de costos por depto | > 2,500 |

---

## 3.6 Flujo de Actualización de Datos

```
[IGSS publica nuevo Excel anual]
            ↓
[Script de detección de cambios]
  ↓ Nuevo archivo detectado
[Pipeline ETL automático]
  ↓ Extracción → Limpieza → Validación
[Actualización incremental del DW]
  ↓ INSERT nuevos registros
[Recálculo de Z-scores y flags]
  ↓
[Actualización automática del dashboard]
  ↓
[Generación de reporte de cambios]
```

---

## 3.7 Supuestos de Diseño

1. **Granularidad anual para costos unitarios:** Los datos de H1 son anuales, por lo que fact_costos tiene granularidad anual cuando la fuente es esta hoja.

2. **Granularidad mensual para costos totales:** Los datos de 5.1 TD_Costos están disponibles mensualmente por departamento.

3. **Datos de 2025 excluidos parcialmente:** El año 2025 tiene datos incompletos en costos unitarios; se incluye solo para ejecución financiera donde los datos son anuales.

4. **Quetzales nominales:** El análisis primario usa valores nominales. El ajuste por IPC se aplica como campo calculado adicional en las vistas del Data Mart.

5. **Región Multiregional (ID 30):** Se registra pero se excluye de análisis comparativos por departamento.
