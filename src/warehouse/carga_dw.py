"""
carga_dw.py
===========
Fase 3 del pipeline ETL — Carga al Data Warehouse.

Crea la base de datos SQLite con el esquema estrella y carga
los datos limpios (data/processed/*_clean.csv) al DW.

Uso:
    python src/warehouse/carga_dw.py

Requisitos:
    pip install pandas sqlalchemy loguru
"""

import sqlite3
from pathlib import Path
import pandas as pd
from loguru import logger

# ── Configuración ───────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parents[2]
PROCESSED_DIR = BASE_DIR / "data" / "processed"
WAREHOUSE_DIR = BASE_DIR / "data" / "warehouse"
SQL_DIR = BASE_DIR / "sql"
LOG_DIR = BASE_DIR / "data" / "logs"

WAREHOUSE_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = WAREHOUSE_DIR / "igss_salud_dw.db"
SCHEMA_SQL = SQL_DIR / "crear_esquema.sql"

logger.add(LOG_DIR / "carga_dw_{time}.log", rotation="1 MB", level="INFO")

# IPC Guatemala para deflactar
IPC_GUATEMALA = {
    2014: 100.00, 2015: 102.40, 2016: 104.12, 2017: 107.23,
    2018: 110.85, 2019: 113.42, 2020: 115.18, 2021: 120.34,
    2022: 133.67, 2023: 138.21, 2024: 141.53, 2025: 144.20
}

ID_SERVICIO_MAP = {
    "HOSP": 1, "CE": 2, "EMERG": 3, "PA": 4, "TOTAL": 5
}

ID_TIEMPO_ANUAL = {anio: int(f"{anio}0") for anio in range(2014, 2026)}


class DataWarehouseLoader:
    """Carga los datos limpios al Data Warehouse SQLite."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = None

    def conectar(self):
        """Abre conexión a SQLite."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        logger.info(f"Conectado a DW: {self.db_path}")

    def cerrar(self):
        if self.conn:
            self.conn.close()
            logger.info("Conexión cerrada.")

    def crear_esquema(self):
        """Ejecuta el script SQL de creación del esquema."""
        logger.info("Creando esquema del Data Warehouse...")
        with open(SCHEMA_SQL, "r", encoding="utf-8") as f:
            sql = f.read()

        # Ejecutar statement por statement (SQLite no admite multi-statement)
        statements = [s.strip() for s in sql.split(";") if s.strip()
                      and not s.strip().startswith("--")]
        cursor = self.conn.cursor()
        errores = 0
        for stmt in statements:
            try:
                cursor.execute(stmt)
            except sqlite3.Error as e:
                # Ignorar errores de SELECT de verificación al final
                if "SELECT" not in stmt.upper():
                    logger.warning(f"Error en SQL: {e}\nStatement: {stmt[:80]}...")
                    errores += 1

        self.conn.commit()
        logger.success(f"Esquema creado ({errores} errores menores ignorados)")

    def cargar_costos_unitarios(self):
        """Carga fact_costos desde costos_unitarios_clean.csv."""
        ruta = PROCESSED_DIR / "costos_unitarios_clean.csv"
        if not ruta.exists():
            logger.warning("costos_unitarios_clean.csv no encontrado, omitiendo.")
            return

        df = pd.read_csv(ruta)
        logger.info(f"Cargando costos unitarios: {len(df)} filas...")

        servicios = [
            ("hospitalizacion_q", "HOSP"),
            ("consulta_externa_q", "CE"),
            ("emergencia_q", "EMERG"),
            ("primeros_auxilios_q", "PA"),
        ]

        cursor = self.conn.cursor()
        registros_insertados = 0

        for _, row in df.iterrows():
            anio = int(row["anio"])
            id_tiempo = ID_TIEMPO_ANUAL.get(anio)
            if id_tiempo is None:
                continue

            for col, codigo in servicios:
                costo = row.get(col)
                if pd.isna(costo):
                    continue

                # Costo real deflactado
                ipc = IPC_GUATEMALA.get(anio, 100.0)
                costo_real = round(costo * (100.0 / ipc), 2)

                # Z-score y outlier
                z_score = row.get("zscore_hosp") if codigo == "HOSP" else None
                es_outlier = bool(row.get("es_outlier_hosp", False)) if codigo == "HOSP" else False
                var_pct = row.get("var_pct_hosp") if codigo == "HOSP" else None
                alerta_var = bool(row.get("alerta_variacion", False)) if codigo == "HOSP" else False

                cursor.execute("""
                    INSERT INTO fact_costos
                    (id_departamento, id_tiempo, id_servicio,
                     costo_unitario_q, costo_unitario_real,
                     es_outlier, z_score, variacion_pct, alerta_variacion)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    1,  # Guatemala (H1 es a nivel nacional, se carga como Guatemala/Nacional)
                    id_tiempo,
                    ID_SERVICIO_MAP[codigo],
                    round(float(costo), 2),
                    costo_real,
                    es_outlier,
                    float(z_score) if z_score is not None and not pd.isna(z_score) else None,
                    float(var_pct) if var_pct is not None and not pd.isna(var_pct) else None,
                    alerta_var
                ))
                registros_insertados += 1

        self.conn.commit()
        logger.success(f"  → {registros_insertados} registros cargados en fact_costos")

    def cargar_ejecucion_gastos(self):
        """Carga fact_ejecucion desde ejecucion_gastos_clean.csv."""
        ruta = PROCESSED_DIR / "ejecucion_gastos_clean.csv"
        if not ruta.exists():
            logger.warning("ejecucion_gastos_clean.csv no encontrado, omitiendo.")
            return

        df = pd.read_csv(ruta)
        logger.info(f"Cargando ejecución y gastos: {len(df)} filas...")

        cursor = self.conn.cursor()
        registros_insertados = 0

        for _, row in df.iterrows():
            anio = int(row["anio"])
            id_depto = int(row["id_departamento"])
            id_tiempo = ID_TIEMPO_ANUAL.get(anio)
            if id_tiempo is None:
                continue

            def safe(col):
                v = row.get(col)
                return float(v) if v is not None and not pd.isna(v) else None

            cursor.execute("""
                INSERT INTO fact_ejecucion
                (id_departamento, id_tiempo,
                 egresos_q, ingresos_q, egresos_real_q, ingresos_real_q,
                 brecha_q, ratio_ei, nivel_riesgo, flag_anomalia, z_score_ratio)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                id_depto, id_tiempo,
                safe("egresos_q"), safe("ingresos_q"),
                safe("egresos_real_q"), safe("ingresos_real_q"),
                safe("brecha_q"), safe("ratio_ei"),
                row.get("nivel_riesgo", "SIN_DATO"),
                bool(row.get("flag_anomalia", False)),
                safe("zscore_ratio")
            ))
            registros_insertados += 1

        self.conn.commit()
        logger.success(f"  → {registros_insertados} registros cargados en fact_ejecucion")

    def registrar_red_flags(self):
        """Detecta y registra automáticamente red flags en el DW."""
        logger.info("Registrando red flags automáticas...")
        cursor = self.conn.cursor()

        # RF-01: Costo de hospitalización outlier
        cursor.execute("""
            INSERT INTO red_flags_log (tipo_flag, descripcion, id_departamento, id_tiempo, valor_detectado, umbral, criticidad)
            SELECT
                'RF-01',
                'Costo unitario de hospitalización estadísticamente atípico (Z-score > 2.5)',
                id_departamento,
                id_tiempo,
                costo_unitario_q,
                2.5,
                CASE WHEN z_score > 3.5 THEN 'ALTA' ELSE 'MEDIA' END
            FROM fact_costos
            WHERE es_outlier = TRUE AND id_servicio = 1
        """)

        # RF-02: Ratio egresos/ingresos crítico (> 6)
        cursor.execute("""
            INSERT INTO red_flags_log (tipo_flag, descripcion, id_departamento, id_tiempo, valor_detectado, umbral, criticidad)
            SELECT
                'RF-02',
                'Ratio egresos/ingresos en nivel CRÍTICO (> 6.0)',
                id_departamento,
                id_tiempo,
                ratio_ei,
                6.0,
                'ALTA'
            FROM fact_ejecucion
            WHERE nivel_riesgo = 'CRÍTICO'
        """)

        # RF-03: Ratio egresos/ingresos alto (4 a 6)
        cursor.execute("""
            INSERT INTO red_flags_log (tipo_flag, descripcion, id_departamento, id_tiempo, valor_detectado, umbral, criticidad)
            SELECT
                'RF-03',
                'Ratio egresos/ingresos en nivel ALTO (4.0 a 6.0)',
                id_departamento,
                id_tiempo,
                ratio_ei,
                4.0,
                'MEDIA'
            FROM fact_ejecucion
            WHERE nivel_riesgo = 'ALTO'
        """)

        # RF-04: Variación interanual de costos > 30%
        cursor.execute("""
            INSERT INTO red_flags_log (tipo_flag, descripcion, id_departamento, id_tiempo, valor_detectado, umbral, criticidad)
            SELECT
                'RF-04',
                'Variación interanual de costo > 30%',
                id_departamento,
                id_tiempo,
                variacion_pct,
                30.0,
                CASE WHEN variacion_pct > 50 THEN 'ALTA' ELSE 'MEDIA' END
            FROM fact_costos
            WHERE alerta_variacion = TRUE
        """)

        self.conn.commit()

        n_flags = cursor.execute("SELECT COUNT(*) FROM red_flags_log").fetchone()[0]
        logger.success(f"  → {n_flags} red flags registradas en red_flags_log")

    def verificar_carga(self):
        """Verifica los conteos finales del DW."""
        cursor = self.conn.cursor()
        tablas = ["dim_tiempo", "dim_departamento", "dim_servicio",
                  "fact_costos", "fact_ejecucion", "red_flags_log"]
        logger.info("── Verificación del Data Warehouse ─────────────────────")
        for tabla in tablas:
            count = cursor.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
            logger.info(f"  {tabla:<25} {count:>6} registros")

        # Resumen de alertas
        criticas = cursor.execute(
            "SELECT COUNT(*) FROM red_flags_log WHERE criticidad='ALTA'"
        ).fetchone()[0]
        logger.warning(f"  Red flags ALTA criticidad: {criticas}")


def main():
    logger.info("=" * 60)
    logger.info("IGSS BI — Fase 3: Carga al Data Warehouse")
    logger.info("=" * 60)

    loader = DataWarehouseLoader(DB_PATH)
    try:
        loader.conectar()
        loader.crear_esquema()
        loader.cargar_costos_unitarios()
        loader.cargar_ejecucion_gastos()
        loader.registrar_red_flags()
        loader.verificar_carga()
        logger.success("✅ Data Warehouse cargado exitosamente")
        logger.info(f"   Base de datos: {DB_PATH}")
    finally:
        loader.cerrar()


if __name__ == "__main__":
    main()
