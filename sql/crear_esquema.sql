-- ============================================================
-- crear_esquema.sql
-- Data Warehouse — BI Justicia en Salud Guatemala (IGSS)
-- Modelo Dimensional: Esquema Estrella
-- Motor: SQLite 3.x (compatible con PostgreSQL con mínimos cambios)
-- ============================================================

-- ── Limpieza previa (en orden inverso de FK) ──────────────────
DROP VIEW IF EXISTS dm_ejecucion;
DROP VIEW IF EXISTS dm_costos;
DROP VIEW IF EXISTS strategic_mart_kpis;
DROP TABLE IF EXISTS fact_ejecucion;
DROP TABLE IF EXISTS fact_costos;
DROP TABLE IF EXISTS dim_servicio;
DROP TABLE IF EXISTS dim_departamento;
DROP TABLE IF EXISTS dim_tiempo;
DROP TABLE IF EXISTS red_flags_log;

-- ============================================================
-- TABLAS DE DIMENSIONES
-- ============================================================

-- dim_tiempo: Dimensión de tiempo (año / mes)
CREATE TABLE dim_tiempo (
    id_tiempo       INTEGER PRIMARY KEY,
    anio            INTEGER NOT NULL,
    mes             INTEGER,              -- NULL para datos anuales
    nombre_mes      VARCHAR(20),
    trimestre       INTEGER,
    es_anual        BOOLEAN DEFAULT FALSE,
    UNIQUE(anio, mes)
);

-- dim_departamento: Los 22 departamentos de Guatemala + Multiregional
CREATE TABLE dim_departamento (
    id_departamento INTEGER PRIMARY KEY,  -- Código oficial MINFIN
    nombre          VARCHAR(60) NOT NULL,
    region          VARCHAR(40),
    poblacion_est   INTEGER,              -- Estimación más reciente
    latitud         DECIMAL(8,6),
    longitud        DECIMAL(9,6)
);

-- dim_servicio: Tipos de servicio médico del IGSS
CREATE TABLE dim_servicio (
    id_servicio     INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo          VARCHAR(10) NOT NULL UNIQUE,
    nombre          VARCHAR(60) NOT NULL,
    descripcion     TEXT
);

-- ============================================================
-- TABLAS DE HECHOS
-- ============================================================

-- fact_costos: Costos de atención médica por departamento, año y servicio
CREATE TABLE fact_costos (
    id_hecho            INTEGER PRIMARY KEY AUTOINCREMENT,
    id_departamento     INTEGER NOT NULL REFERENCES dim_departamento(id_departamento),
    id_tiempo           INTEGER NOT NULL REFERENCES dim_tiempo(id_tiempo),
    id_servicio         INTEGER NOT NULL REFERENCES dim_servicio(id_servicio),
    costo_total_q       DECIMAL(15,2),   -- Quetzales nominales
    costo_unitario_q    DECIMAL(10,2),   -- Costo por atención (nominales)
    costo_unitario_real DECIMAL(10,2),   -- Deflactado a Q2014
    cantidad_atenciones INTEGER,
    es_outlier          BOOLEAN DEFAULT FALSE,
    z_score             DECIMAL(8,4),
    variacion_pct       DECIMAL(8,2),    -- Variación respecto al año anterior
    alerta_variacion    BOOLEAN DEFAULT FALSE,
    fuente_dato         VARCHAR(20) DEFAULT 'IGSS_2025'
);

-- fact_ejecucion: Ejecución presupuestaria por departamento y año
CREATE TABLE fact_ejecucion (
    id_hecho            INTEGER PRIMARY KEY AUTOINCREMENT,
    id_departamento     INTEGER NOT NULL REFERENCES dim_departamento(id_departamento),
    id_tiempo           INTEGER NOT NULL REFERENCES dim_tiempo(id_tiempo),
    egresos_q           DECIMAL(15,2),   -- Gastos ejecutados (nominales)
    ingresos_q          DECIMAL(15,2),   -- Recaudación (nominales)
    egresos_real_q      DECIMAL(15,2),   -- Deflactado Q2014
    ingresos_real_q     DECIMAL(15,2),   -- Deflactado Q2014
    brecha_q            DECIMAL(15,2),   -- Egresos - Ingresos
    ratio_ei            DECIMAL(8,4),    -- Egresos / Ingresos
    nivel_riesgo        VARCHAR(15),     -- NORMAL / MODERADO / ALTO / CRÍTICO
    flag_anomalia       BOOLEAN DEFAULT FALSE,
    z_score_ratio       DECIMAL(8,4),
    fuente_dato         VARCHAR(20) DEFAULT 'IGSS_2025'
);

-- ============================================================
-- TABLA DE AUDITORÍA
-- ============================================================

-- red_flags_log: Registro de alertas detectadas
CREATE TABLE red_flags_log (
    id_flag         INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha_deteccion DATETIME DEFAULT CURRENT_TIMESTAMP,
    tipo_flag       VARCHAR(30) NOT NULL,  -- RF-01 a RF-08
    descripcion     TEXT,
    id_departamento INTEGER REFERENCES dim_departamento(id_departamento),
    id_tiempo       INTEGER REFERENCES dim_tiempo(id_tiempo),
    valor_detectado DECIMAL(15,4),
    umbral          DECIMAL(15,4),
    criticidad      VARCHAR(10)  -- ALTA / MEDIA / BAJA
);

-- ============================================================
-- DATOS DE CATÁLOGOS (Dimensiones estáticas)
-- ============================================================

-- Poblar dim_tiempo (años 2014–2025)
INSERT INTO dim_tiempo (id_tiempo, anio, mes, nombre_mes, trimestre, es_anual) VALUES
(20140, 2014, NULL, NULL, NULL, TRUE),
(20150, 2015, NULL, NULL, NULL, TRUE),
(20160, 2016, NULL, NULL, NULL, TRUE),
(20170, 2017, NULL, NULL, NULL, TRUE),
(20180, 2018, NULL, NULL, NULL, TRUE),
(20190, 2019, NULL, NULL, NULL, TRUE),
(20200, 2020, NULL, NULL, NULL, TRUE),
(20210, 2021, NULL, NULL, NULL, TRUE),
(20220, 2022, NULL, NULL, NULL, TRUE),
(20230, 2023, NULL, NULL, NULL, TRUE),
(20240, 2024, NULL, NULL, NULL, TRUE),
(20250, 2025, NULL, NULL, NULL, TRUE),
-- Meses 2021
(202101, 2021, 1, 'Enero', 1, FALSE),
(202102, 2021, 2, 'Febrero', 1, FALSE),
(202103, 2021, 3, 'Marzo', 1, FALSE),
(202104, 2021, 4, 'Abril', 2, FALSE),
(202105, 2021, 5, 'Mayo', 2, FALSE),
(202106, 2021, 6, 'Junio', 2, FALSE),
(202107, 2021, 7, 'Julio', 3, FALSE),
(202108, 2021, 8, 'Agosto', 3, FALSE),
(202109, 2021, 9, 'Septiembre', 3, FALSE),
(202110, 2021, 10, 'Octubre', 4, FALSE),
(202111, 2021, 11, 'Noviembre', 4, FALSE),
(202112, 2021, 12, 'Diciembre', 4, FALSE),
-- Meses 2022
(202201, 2022, 1, 'Enero', 1, FALSE),
(202202, 2022, 2, 'Febrero', 1, FALSE),
(202203, 2022, 3, 'Marzo', 1, FALSE),
(202204, 2022, 4, 'Abril', 2, FALSE),
(202205, 2022, 5, 'Mayo', 2, FALSE),
(202206, 2022, 6, 'Junio', 2, FALSE),
(202207, 2022, 7, 'Julio', 3, FALSE),
(202208, 2022, 8, 'Agosto', 3, FALSE),
(202209, 2022, 9, 'Septiembre', 3, FALSE),
(202210, 2022, 10, 'Octubre', 4, FALSE),
(202211, 2022, 11, 'Noviembre', 4, FALSE),
(202212, 2022, 12, 'Diciembre', 4, FALSE);

-- Poblar dim_departamento
INSERT INTO dim_departamento (id_departamento, nombre, region, poblacion_est, latitud, longitud) VALUES
(1,  'Guatemala',      'Metropolitana',  3257616, 14.6349, -90.5069),
(2,  'El Progreso',    'Nororiente',      161584, 14.9333, -90.0667),
(3,  'Sacatepéquez',   'Central',         318695, 14.5586, -90.7346),
(4,  'Chimaltenango',  'Central',         728953, 14.6610, -90.8190),
(5,  'Escuintla',      'Sur',             744264, 14.3047, -90.7851),
(6,  'Santa Rosa',     'Suroriente',      390359, 14.2189, -90.2971),
(7,  'Sololá',         'Suroccidente',    478328, 14.7744, -91.1823),
(8,  'Totonicapán',    'Suroccidente',    508409, 14.9131, -91.3614),
(9,  'Quetzaltenango', 'Suroccidente',    836543, 14.8434, -91.5180),
(10, 'Suchitepéquez',  'Suroccidente',    571499, 14.5318, -91.5187),
(11, 'Retalhuleu',     'Suroccidente',    341566, 14.5289, -91.6761),
(12, 'San Marcos',     'Suroccidente',   1109507, 14.9655, -91.7963),
(13, 'Huehuetenango',  'Noroccidente',  1283054, 15.3197, -91.4713),
(14, 'Quiché',         'Noroccidente',   1053696, 15.0337, -91.1545),
(15, 'Baja Verapaz',   'Norte',           323468, 15.1222, -90.3675),
(16, 'Alta Verapaz',   'Norte',          1275430, 15.4746, -90.3724),
(17, 'Petén',          'Petén',           706094, 16.9138, -89.8934),
(18, 'Izabal',         'Nororiente',      481470, 15.4742, -89.1444),
(19, 'Zacapa',         'Nororiente',      248949, 14.9693, -89.5296),
(20, 'Chiquimula',     'Nororiente',      406111, 14.7995, -89.5455),
(21, 'Jalapa',         'Suroriente',      357247, 14.6321, -89.9885),
(22, 'Jutiapa',        'Suroriente',      512115, 14.2909, -89.8920),
(30, 'Multiregional',  'Multiregional',        0, NULL,    NULL);

-- Poblar dim_servicio
INSERT INTO dim_servicio (codigo, nombre, descripcion) VALUES
('HOSP', 'Hospitalización',
    'Servicio de hospitalización — atención en cama a pacientes que requieren internamiento'),
('CE', 'Consulta Externa',
    'Consultas médicas ambulatorias en clínicas y centros del IGSS'),
('EMERG', 'Emergencia',
    'Atención de urgencias y emergencias médicas'),
('PA', 'Primeros Auxilios',
    'Atención inmediata de lesiones menores y primeros auxilios'),
('TOTAL', 'Total Servicios',
    'Agregado de todos los tipos de servicio');

-- ============================================================
-- DATA MARTS (Vistas analíticas)
-- ============================================================

-- DataMart 1: Análisis de costos con detección de anomalías
CREATE VIEW dm_costos AS
SELECT
    t.anio,
    t.mes,
    t.nombre_mes,
    t.trimestre,
    d.nombre        AS departamento,
    d.region,
    s.nombre        AS servicio,
    s.codigo        AS codigo_servicio,
    fc.costo_total_q,
    fc.costo_unitario_q,
    fc.costo_unitario_real,
    fc.es_outlier,
    fc.z_score,
    fc.variacion_pct,
    fc.alerta_variacion,
    CASE
        WHEN fc.z_score > 3.5  THEN 'EXTREMO'
        WHEN fc.z_score > 2.5  THEN 'ALTO'
        WHEN fc.z_score > 1.5  THEN 'MODERADO'
        ELSE 'NORMAL'
    END             AS nivel_alerta_costo
FROM fact_costos fc
JOIN dim_tiempo t        ON fc.id_tiempo = t.id_tiempo
JOIN dim_departamento d  ON fc.id_departamento = d.id_departamento
JOIN dim_servicio s      ON fc.id_servicio = s.id_servicio;

-- DataMart 2: Análisis de ejecución financiera
CREATE VIEW dm_ejecucion AS
SELECT
    t.anio,
    d.nombre        AS departamento,
    d.region,
    fe.egresos_q,
    fe.ingresos_q,
    fe.egresos_real_q,
    fe.ingresos_real_q,
    fe.brecha_q,
    fe.ratio_ei,
    fe.nivel_riesgo,
    fe.flag_anomalia,
    fe.z_score_ratio,
    -- Porcentaje de la brecha respecto al total nacional del año
    ROUND(fe.brecha_q / SUM(fe.brecha_q) OVER (PARTITION BY t.anio) * 100, 2)
        AS pct_brecha_nacional
FROM fact_ejecucion fe
JOIN dim_tiempo t        ON fe.id_tiempo = t.id_tiempo
JOIN dim_departamento d  ON fe.id_departamento = d.id_departamento
WHERE d.id_departamento != 30;  -- Excluir Multiregional de análisis por depto

-- Strategic Mart: KPIs ejecutivos nacionales
CREATE VIEW strategic_mart_kpis AS
SELECT
    t.anio,
    -- KPIs de costos
    ROUND(AVG(CASE WHEN s.codigo='HOSP' THEN fc.costo_unitario_q END), 2)
        AS costo_medio_hospitalizacion,
    ROUND(AVG(CASE WHEN s.codigo='CE'   THEN fc.costo_unitario_q END), 2)
        AS costo_medio_consulta_externa,
    ROUND(AVG(CASE WHEN s.codigo='EMERG' THEN fc.costo_unitario_q END), 2)
        AS costo_medio_emergencia,
    COUNT(CASE WHEN fc.es_outlier = TRUE THEN 1 END)
        AS total_outliers_costo,
    -- KPIs financieros
    ROUND(SUM(fe.egresos_q) / 1e9, 3)    AS total_egresos_miles_millones,
    ROUND(SUM(fe.ingresos_q) / 1e9, 3)   AS total_ingresos_miles_millones,
    ROUND(SUM(fe.brecha_q) / 1e9, 3)     AS brecha_nacional_miles_millones,
    COUNT(CASE WHEN fe.flag_anomalia = TRUE THEN 1 END)
        AS departamentos_en_alerta,
    -- Índice de riesgo agregado
    ROUND(
        CAST(COUNT(CASE WHEN fe.nivel_riesgo IN ('CRÍTICO','ALTO') THEN 1 END) AS FLOAT)
        / COUNT(DISTINCT fe.id_departamento) * 100, 1
    )   AS pct_deptos_riesgo_alto
FROM dim_tiempo t
LEFT JOIN fact_costos fc    ON fc.id_tiempo = t.id_tiempo
LEFT JOIN dim_servicio s    ON fc.id_servicio = s.id_servicio
LEFT JOIN fact_ejecucion fe ON fe.id_tiempo = t.id_tiempo
WHERE t.es_anual = TRUE
GROUP BY t.anio
ORDER BY t.anio;

-- ============================================================
-- ÍNDICES para rendimiento analítico
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_fc_depto_tiempo  ON fact_costos(id_departamento, id_tiempo);
CREATE INDEX IF NOT EXISTS idx_fc_servicio       ON fact_costos(id_servicio);
CREATE INDEX IF NOT EXISTS idx_fc_outlier        ON fact_costos(es_outlier);
CREATE INDEX IF NOT EXISTS idx_fe_depto_tiempo   ON fact_ejecucion(id_departamento, id_tiempo);
CREATE INDEX IF NOT EXISTS idx_fe_flag           ON fact_ejecucion(flag_anomalia);
CREATE INDEX IF NOT EXISTS idx_fe_riesgo         ON fact_ejecucion(nivel_riesgo);
CREATE INDEX IF NOT EXISTS idx_rf_tipo           ON red_flags_log(tipo_flag);
CREATE INDEX IF NOT EXISTS idx_rf_criticidad     ON red_flags_log(criticidad);

-- ============================================================
-- Verificación del esquema
-- ============================================================
SELECT 'dim_tiempo'        AS tabla, COUNT(*) AS registros FROM dim_tiempo
UNION ALL
SELECT 'dim_departamento', COUNT(*) FROM dim_departamento
UNION ALL
SELECT 'dim_servicio',     COUNT(*) FROM dim_servicio
UNION ALL
SELECT 'fact_costos',      COUNT(*) FROM fact_costos
UNION ALL
SELECT 'fact_ejecucion',   COUNT(*) FROM fact_ejecucion;
