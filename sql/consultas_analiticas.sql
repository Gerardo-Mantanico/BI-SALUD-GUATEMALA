-- ============================================================
-- consultas_analiticas.sql
-- Catálogo de consultas BI para análisis de salud y corrupción
-- Data Warehouse: igss_salud_dw.db
-- ============================================================

-- ────────────────────────────────────────────────────────────
-- BLOQUE A: Análisis de Costos Unitarios
-- ────────────────────────────────────────────────────────────

-- A-01: Evolución histórica de costos por tipo de servicio
SELECT
    t.anio,
    s.nombre          AS servicio,
    fc.costo_unitario_q,
    fc.costo_unitario_real,
    fc.variacion_pct,
    fc.z_score,
    CASE WHEN fc.es_outlier THEN '⚠️ ATÍPICO' ELSE 'Normal' END AS estado
FROM fact_costos fc
JOIN dim_tiempo t   ON fc.id_tiempo = t.id_tiempo
JOIN dim_servicio s ON fc.id_servicio = s.id_servicio
WHERE t.es_anual = 1
ORDER BY s.codigo, t.anio;

-- A-02: Años con incremento mayor al 30% en hospitalización
SELECT
    t.anio,
    fc.costo_unitario_q                    AS costo_Q,
    ROUND(fc.variacion_pct, 1)            AS variacion_pct,
    ROUND(fc.z_score, 2)                  AS z_score
FROM fact_costos fc
JOIN dim_tiempo t   ON fc.id_tiempo = t.id_tiempo
JOIN dim_servicio s ON fc.id_servicio = s.id_servicio
WHERE s.codigo = 'HOSP'
  AND fc.alerta_variacion = TRUE
ORDER BY fc.variacion_pct DESC;

-- A-03: Comparación 2019 vs 2021 (antes/durante crisis de costos)
SELECT
    s.nombre     AS servicio,
    MAX(CASE WHEN t.anio = 2019 THEN fc.costo_unitario_q END) AS costo_2019,
    MAX(CASE WHEN t.anio = 2021 THEN fc.costo_unitario_q END) AS costo_2021,
    ROUND(
        (MAX(CASE WHEN t.anio = 2021 THEN fc.costo_unitario_q END) -
         MAX(CASE WHEN t.anio = 2019 THEN fc.costo_unitario_q END))
        / MAX(CASE WHEN t.anio = 2019 THEN fc.costo_unitario_q END) * 100, 1
    )            AS incremento_pct_2019_2021
FROM fact_costos fc
JOIN dim_tiempo t   ON fc.id_tiempo = t.id_tiempo
JOIN dim_servicio s ON fc.id_servicio = s.id_servicio
WHERE t.anio IN (2019, 2021) AND t.es_anual = 1
GROUP BY s.nombre
ORDER BY incremento_pct_2019_2021 DESC;

-- A-04: Proyección de costos 2026-2030 (regresión lineal simplificada)
-- Usando pendiente histórica: ~Q600/año en hospitalización
WITH base AS (
    SELECT t.anio, fc.costo_unitario_q
    FROM fact_costos fc
    JOIN dim_tiempo t   ON fc.id_tiempo = t.id_tiempo
    JOIN dim_servicio s ON fc.id_servicio = s.id_servicio
    WHERE s.codigo = 'HOSP' AND t.es_anual = 1
),
params AS (
    SELECT
        AVG(anio)             AS media_x,
        AVG(costo_unitario_q) AS media_y,
        SUM((anio - AVG(anio) OVER()) * (costo_unitario_q - AVG(costo_unitario_q) OVER()))
            / SUM((anio - AVG(anio) OVER()) * (anio - AVG(anio) OVER())) AS pendiente
    FROM base
)
SELECT
    proyeccion.anio_futuro                                       AS anio,
    ROUND(p.media_y + p.pendiente * (proyeccion.anio_futuro - p.media_x), 2) AS costo_proyectado_Q,
    'PROYECCIÓN'                                                 AS tipo
FROM (VALUES (2026), (2027), (2028), (2029), (2030)) AS proyeccion(anio_futuro)
CROSS JOIN params p;


-- ────────────────────────────────────────────────────────────
-- BLOQUE B: Análisis de Ejecución Financiera
-- ────────────────────────────────────────────────────────────

-- B-01: Top 10 departamentos con mayor brecha en 2025
SELECT
    d.nombre          AS departamento,
    d.region,
    ROUND(fe.egresos_q / 1e6, 2)   AS egresos_millones_Q,
    ROUND(fe.ingresos_q / 1e6, 2)  AS ingresos_millones_Q,
    ROUND(fe.brecha_q / 1e6, 2)    AS brecha_millones_Q,
    ROUND(fe.ratio_ei, 2)           AS ratio_egresos_ingresos,
    fe.nivel_riesgo
FROM fact_ejecucion fe
JOIN dim_departamento d ON fe.id_departamento = d.id_departamento
JOIN dim_tiempo t        ON fe.id_tiempo = t.id_tiempo
WHERE t.anio = 2025
  AND d.id_departamento != 30
ORDER BY fe.brecha_q DESC
LIMIT 10;

-- B-02: Departamentos con nivel de riesgo CRÍTICO o ALTO (ambos años)
SELECT
    d.nombre          AS departamento,
    t.anio,
    ROUND(fe.ratio_ei, 2)   AS ratio_ei,
    fe.nivel_riesgo,
    ROUND(fe.brecha_q / 1e6, 2) AS brecha_millones_Q
FROM fact_ejecucion fe
JOIN dim_departamento d ON fe.id_departamento = d.id_departamento
JOIN dim_tiempo t        ON fe.id_tiempo = t.id_tiempo
WHERE fe.nivel_riesgo IN ('CRÍTICO', 'ALTO')
ORDER BY t.anio, fe.ratio_ei DESC;

-- B-03: Variación de brecha 2024 → 2025 por departamento
SELECT
    d.nombre AS departamento,
    d.region,
    ROUND(MAX(CASE WHEN t.anio=2024 THEN fe.brecha_q END)/1e6, 2) AS brecha_2024_M,
    ROUND(MAX(CASE WHEN t.anio=2025 THEN fe.brecha_q END)/1e6, 2) AS brecha_2025_M,
    ROUND(
        (MAX(CASE WHEN t.anio=2025 THEN fe.brecha_q END) -
         MAX(CASE WHEN t.anio=2024 THEN fe.brecha_q END))
        / NULLIF(ABS(MAX(CASE WHEN t.anio=2024 THEN fe.brecha_q END)), 0) * 100, 1
    ) AS variacion_pct
FROM fact_ejecucion fe
JOIN dim_departamento d ON fe.id_departamento = d.id_departamento
JOIN dim_tiempo t        ON fe.id_tiempo = t.id_tiempo
WHERE d.id_departamento != 30
GROUP BY d.nombre, d.region
HAVING brecha_2024_M IS NOT NULL AND brecha_2025_M IS NOT NULL
ORDER BY variacion_pct DESC;

-- B-04: Resumen nacional por año
SELECT
    t.anio,
    ROUND(SUM(fe.egresos_q)/1e9, 3)   AS total_egresos_miles_M,
    ROUND(SUM(fe.ingresos_q)/1e9, 3)  AS total_ingresos_miles_M,
    ROUND(SUM(fe.brecha_q)/1e9, 3)    AS brecha_nacional_miles_M,
    COUNT(CASE WHEN fe.nivel_riesgo = 'CRÍTICO' THEN 1 END) AS deptos_criticos,
    COUNT(CASE WHEN fe.nivel_riesgo = 'ALTO'    THEN 1 END) AS deptos_alto,
    COUNT(CASE WHEN fe.nivel_riesgo = 'NORMAL'  THEN 1 END) AS deptos_normales
FROM fact_ejecucion fe
JOIN dim_tiempo t ON fe.id_tiempo = t.id_tiempo
WHERE fe.id_departamento != 30
GROUP BY t.anio
ORDER BY t.anio;

-- B-05: Concentración de gasto (índice HHI simplificado)
SELECT
    t.anio,
    d.nombre   AS departamento,
    ROUND(fe.egresos_q / SUM(fe.egresos_q) OVER (PARTITION BY t.anio) * 100, 2) AS share_pct,
    ROUND(
        POWER(fe.egresos_q / SUM(fe.egresos_q) OVER (PARTITION BY t.anio) * 100, 2), 2
    ) AS hhi_componente
FROM fact_ejecucion fe
JOIN dim_departamento d ON fe.id_departamento = d.id_departamento
JOIN dim_tiempo t        ON fe.id_tiempo = t.id_tiempo
WHERE d.id_departamento != 30
ORDER BY t.anio, share_pct DESC;


-- ────────────────────────────────────────────────────────────
-- BLOQUE C: Red Flags y Alertas
-- ────────────────────────────────────────────────────────────

-- C-01: Resumen de red flags por tipo y criticidad
SELECT
    tipo_flag,
    criticidad,
    COUNT(*)                        AS total,
    MIN(anio)                       AS anio_mas_antiguo,
    MAX(anio)                       AS anio_mas_reciente
FROM red_flags_log rf
LEFT JOIN dim_tiempo t ON rf.id_tiempo = t.id_tiempo
GROUP BY tipo_flag, criticidad
ORDER BY criticidad DESC, total DESC;

-- C-02: Red flags por departamento (¿cuáles acumulan más alertas?)
SELECT
    d.nombre        AS departamento,
    COUNT(*)        AS total_flags,
    SUM(CASE WHEN rf.criticidad = 'ALTA'  THEN 1 ELSE 0 END) AS flags_alta,
    SUM(CASE WHEN rf.criticidad = 'MEDIA' THEN 1 ELSE 0 END) AS flags_media
FROM red_flags_log rf
JOIN dim_departamento d ON rf.id_departamento = d.id_departamento
GROUP BY d.nombre
ORDER BY flags_alta DESC, total_flags DESC;

-- C-03: Detalle completo de alertas de alta criticidad
SELECT
    rf.tipo_flag,
    rf.descripcion,
    ROUND(rf.valor_detectado, 2) AS valor,
    rf.umbral,
    rf.criticidad,
    d.nombre AS departamento,
    t.anio
FROM red_flags_log rf
LEFT JOIN dim_departamento d ON rf.id_departamento = d.id_departamento
LEFT JOIN dim_tiempo t        ON rf.id_tiempo = t.id_tiempo
WHERE rf.criticidad = 'ALTA'
ORDER BY t.anio DESC, rf.tipo_flag;


-- ────────────────────────────────────────────────────────────
-- BLOQUE D: KPIs Ejecutivos (Strategic Mart)
-- ────────────────────────────────────────────────────────────

-- D-01: Vista del Strategic Mart
SELECT * FROM strategic_mart_kpis;

-- D-02: Índice compuesto de riesgo por departamento (2025)
SELECT
    d.nombre                    AS departamento,
    d.region,
    fe.ratio_ei,
    fe.nivel_riesgo,
    fe.flag_anomalia,
    fe.z_score_ratio,
    -- Puntaje de riesgo compuesto (0-100)
    ROUND(
        CASE fe.nivel_riesgo
            WHEN 'CRÍTICO'  THEN 80 + LEAST(fe.ratio_ei * 2, 20)
            WHEN 'ALTO'     THEN 50 + (fe.ratio_ei - 4) * 10
            WHEN 'MODERADO' THEN 20 + (fe.ratio_ei - 2) * 15
            ELSE                 fe.ratio_ei * 5
        END, 1
    )                           AS indice_riesgo_compuesto
FROM fact_ejecucion fe
JOIN dim_departamento d ON fe.id_departamento = d.id_departamento
JOIN dim_tiempo t        ON fe.id_tiempo = t.id_tiempo
WHERE t.anio = 2025
  AND d.id_departamento != 30
ORDER BY indice_riesgo_compuesto DESC;


-- ────────────────────────────────────────────────────────────
-- BLOQUE E: Análisis para el Cubo OLAP
-- ────────────────────────────────────────────────────────────

-- E-01: Cubo de costos — Pivot por servicio y año
SELECT
    t.anio,
    ROUND(MAX(CASE WHEN s.codigo='HOSP'  THEN fc.costo_unitario_q END), 2) AS hosp_Q,
    ROUND(MAX(CASE WHEN s.codigo='CE'    THEN fc.costo_unitario_q END), 2) AS consulta_Q,
    ROUND(MAX(CASE WHEN s.codigo='EMERG' THEN fc.costo_unitario_q END), 2) AS emergencia_Q,
    ROUND(MAX(CASE WHEN s.codigo='PA'    THEN fc.costo_unitario_q END), 2) AS prim_aux_Q
FROM fact_costos fc
JOIN dim_tiempo t   ON fc.id_tiempo = t.id_tiempo
JOIN dim_servicio s ON fc.id_servicio = s.id_servicio
WHERE t.es_anual = 1
GROUP BY t.anio
ORDER BY t.anio;

-- E-02: Cubo de ejecución — Roll-up por región
SELECT
    t.anio,
    d.region,
    ROUND(SUM(fe.egresos_q)/1e6, 2)  AS egresos_M,
    ROUND(SUM(fe.ingresos_q)/1e6, 2) AS ingresos_M,
    ROUND(SUM(fe.brecha_q)/1e6, 2)   AS brecha_M,
    ROUND(AVG(fe.ratio_ei), 2)        AS ratio_promedio,
    COUNT(CASE WHEN fe.flag_anomalia THEN 1 END) AS deptos_en_alerta
FROM fact_ejecucion fe
JOIN dim_departamento d ON fe.id_departamento = d.id_departamento
JOIN dim_tiempo t        ON fe.id_tiempo = t.id_tiempo
WHERE d.id_departamento != 30
GROUP BY t.anio, d.region
ORDER BY t.anio, brecha_M DESC;

-- E-03: Drill-down Suroccidente 2025 (región con más alertas)
SELECT
    d.nombre   AS departamento,
    ROUND(fe.egresos_q/1e6, 2)  AS egresos_M,
    ROUND(fe.ingresos_q/1e6, 2) AS ingresos_M,
    ROUND(fe.brecha_q/1e6, 2)   AS brecha_M,
    fe.ratio_ei,
    fe.nivel_riesgo
FROM fact_ejecucion fe
JOIN dim_departamento d ON fe.id_departamento = d.id_departamento
JOIN dim_tiempo t        ON fe.id_tiempo = t.id_tiempo
WHERE t.anio = 2025
  AND d.region = 'Suroccidente'
ORDER BY fe.ratio_ei DESC;
