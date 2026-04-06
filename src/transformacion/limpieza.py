"""
limpieza.py
===========
Fase 2 del pipeline ETL — Transformación y limpieza de datos.

Aplica reglas de calidad, calcula outliers estadísticos (Z-score),
deflacta montos a precios constantes y genera los datasets finales
listos para cargar al Data Warehouse.

Uso:
    python src/transformacion/limpieza.py

Requisitos:
    pip install pandas numpy scipy loguru
"""

import os
from pathlib import Path
import pandas as pd
import numpy as np
from scipy import stats
from loguru import logger

# ── Configuración ───────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parents[2]
PROCESSED_DIR = BASE_DIR / "data" / "processed"
LOG_DIR = BASE_DIR / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger.add(LOG_DIR / "transformacion_{time}.log", rotation="1 MB", level="INFO")

# IPC Guatemala (Base 2014 = 100) — Fuente: BANGUAT
# Permite deflactar valores nominales a quetzales constantes 2014
IPC_GUATEMALA = {
    2014: 100.00, 2015: 102.40, 2016: 104.12, 2017: 107.23,
    2018: 110.85, 2019: 113.42, 2020: 115.18, 2021: 120.34,
    2022: 133.67, 2023: 138.21, 2024: 141.53, 2025: 144.20
}

# Umbrales de red flags
UMBRAL_RATIO_EI_CRITICO = 6.0
UMBRAL_RATIO_EI_ALTO = 4.0
UMBRAL_RATIO_EI_MODERADO = 2.0
UMBRAL_VARIACION_ANUAL = 30.0  # % de variación interanual considerada alta
UMBRAL_ZSCORE = 2.5


def deflactar(monto_nominal: float, anio: int, anio_base: int = 2014) -> float:
    """Convierte un monto nominal a quetzales constantes del año base."""
    ipc_anio = IPC_GUATEMALA.get(anio, None)
    ipc_base = IPC_GUATEMALA.get(anio_base, 100.0)
    if ipc_anio is None:
        return monto_nominal  # Sin deflactar si no hay IPC
    return round(monto_nominal * (ipc_base / ipc_anio), 2)


def calcular_zscore(serie: pd.Series) -> pd.Series:
    """Calcula el Z-score de una serie numérica."""
    return pd.Series(stats.zscore(serie.dropna()), index=serie.dropna().index).reindex(serie.index)


class TransformadorDatos:
    """Aplica transformaciones y reglas de calidad a los datasets del IGSS."""

    def transformar_costos_unitarios(self) -> pd.DataFrame:
        """Limpia y enriquece el dataset de costos unitarios (H1)."""
        logger.info("Transformando costos unitarios...")
        ruta = PROCESSED_DIR / "costos_unitarios.csv"
        df = pd.read_csv(ruta)

        # T-01: Verificar tipos
        df["anio"] = df["anio"].astype(int)
        for col in ["hospitalizacion_q", "consulta_externa_q", "emergencia_q", "primeros_auxilios_q"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        # T-04: Deflactar a quetzales constantes 2014
        df["hospitalizacion_real_q"] = df.apply(
            lambda r: deflactar(r["hospitalizacion_q"], r["anio"]), axis=1
        )
        df["consulta_externa_real_q"] = df.apply(
            lambda r: deflactar(r["consulta_externa_q"], r["anio"]), axis=1
        )

        # T-07: Calcular Z-scores para hospitalización
        df["zscore_hosp"] = calcular_zscore(df["hospitalizacion_q"]).round(4)
        df["es_outlier_hosp"] = df["zscore_hosp"].abs() > UMBRAL_ZSCORE

        # Calcular variación interanual
        df = df.sort_values("anio").reset_index(drop=True)
        df["var_pct_hosp"] = df["hospitalizacion_q"].pct_change() * 100
        df["var_pct_ce"] = df["consulta_externa_q"].pct_change() * 100
        df["alerta_variacion"] = df["var_pct_hosp"].abs() > UMBRAL_VARIACION_ANUAL

        # Conteo de red flags
        n_outliers = df["es_outlier_hosp"].sum()
        n_alertas = df["alerta_variacion"].sum()
        logger.info(f"  Outliers detectados en hospitalización: {n_outliers}")
        logger.info(f"  Alertas por variación > {UMBRAL_VARIACION_ANUAL}%: {n_alertas}")

        out = PROCESSED_DIR / "costos_unitarios_clean.csv"
        df.to_csv(out, index=False, encoding="utf-8")
        logger.success(f"  → Guardado: {out} ({len(df)} registros)")
        return df

    def transformar_ejecucion_gastos(self) -> pd.DataFrame:
        """Limpia y enriquece el dataset de ejecución financiera."""
        logger.info("Transformando ejecución y gastos...")
        ruta = PROCESSED_DIR / "ejecucion_gastos.csv"
        df = pd.read_csv(ruta)

        # T-02: Normalizar tipos
        df["anio"] = df["anio"].astype(int)
        df["id_departamento"] = df["id_departamento"].astype(int)
        for col in ["egresos_q", "ingresos_q", "brecha_q", "ratio_ei"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        # T-04: Deflactar montos
        df["egresos_real_q"] = df.apply(
            lambda r: deflactar(r["egresos_q"], r["anio"]), axis=1
        )
        df["ingresos_real_q"] = df.apply(
            lambda r: deflactar(r["ingresos_q"], r["anio"]), axis=1
        )

        # Clasificación por nivel de riesgo financiero
        def clasificar_riesgo(ratio):
            if pd.isna(ratio):
                return "SIN_DATO"
            if ratio > UMBRAL_RATIO_EI_CRITICO:
                return "CRÍTICO"
            if ratio > UMBRAL_RATIO_EI_ALTO:
                return "ALTO"
            if ratio > UMBRAL_RATIO_EI_MODERADO:
                return "MODERADO"
            return "NORMAL"

        df["nivel_riesgo"] = df["ratio_ei"].apply(clasificar_riesgo)

        # Z-score del ratio por año
        for anio in df["anio"].unique():
            mask = df["anio"] == anio
            df.loc[mask, "zscore_ratio"] = calcular_zscore(df.loc[mask, "ratio_ei"]).round(4)

        df["es_outlier_ratio"] = df["zscore_ratio"].abs() > UMBRAL_ZSCORE

        # Reporte de hallazgos
        for nivel in ["CRÍTICO", "ALTO"]:
            subset = df[df["nivel_riesgo"] == nivel]
            if not subset.empty:
                logger.warning(f"  Departamentos con riesgo {nivel}:")
                for _, row in subset.iterrows():
                    logger.warning(
                        f"    [{row['anio']}] {row['departamento']}: "
                        f"ratio={row['ratio_ei']:.2f}, brecha=Q{row['brecha_q']:,.0f}"
                    )

        out = PROCESSED_DIR / "ejecucion_gastos_clean.csv"
        df.to_csv(out, index=False, encoding="utf-8")
        logger.success(f"  → Guardado: {out} ({len(df)} registros)")
        return df

    def transformar_costos_departamento(self) -> pd.DataFrame:
        """Limpia y enriquece el dataset de costos por departamento."""
        logger.info("Transformando costos por departamento...")
        ruta = PROCESSED_DIR / "costos_departamento.csv"
        df = pd.read_csv(ruta)

        # Verificar si existe el archivo
        if not ruta.exists():
            logger.warning("Archivo costos_departamento.csv no encontrado, omitiendo.")
            return pd.DataFrame()

        df["anio"] = df["anio"].astype(int)
        df["mes"] = df["mes"].astype(int)
        df["costo_total_q"] = pd.to_numeric(df["costo_total_q"], errors="coerce")

        # T-09: Validar rangos (rechazar negativos)
        df = df[df["costo_total_q"] > 0].copy()

        # T-04: Deflactar
        df["costo_real_q"] = df.apply(
            lambda r: deflactar(r["costo_total_q"], r["anio"]), axis=1
        )

        # Calcular promedio trimestral
        df["trimestre"] = df["mes"].apply(lambda m: (m - 1) // 3 + 1)

        # Z-score por departamento y año
        df["zscore_costo"] = df.groupby(["id_departamento", "anio"])["costo_total_q"].transform(
            lambda x: stats.zscore(x) if len(x) > 2 else np.nan
        ).round(4)

        out = PROCESSED_DIR / "costos_departamento_clean.csv"
        df.to_csv(out, index=False, encoding="utf-8")
        logger.success(f"  → Guardado: {out} ({len(df)} registros)")
        return df

    def generar_reporte_calidad(self, dfs: dict) -> dict:
        """Genera un reporte de calidad de datos."""
        reporte = {}
        for nombre, df in dfs.items():
            if df.empty:
                continue
            reporte[nombre] = {
                "total_registros": len(df),
                "columnas": list(df.columns),
                "nulos_por_columna": df.isnull().sum().to_dict(),
                "tipos_de_dato": df.dtypes.astype(str).to_dict(),
            }
            if "es_outlier_hosp" in df.columns:
                reporte[nombre]["outliers_hospitalizacion"] = int(df["es_outlier_hosp"].sum())
            if "nivel_riesgo" in df.columns:
                reporte[nombre]["distribucion_riesgo"] = df["nivel_riesgo"].value_counts().to_dict()

        return reporte


def main():
    logger.info("=" * 60)
    logger.info("IGSS BI — Fase 2: Transformación y Limpieza")
    logger.info("=" * 60)

    transformador = TransformadorDatos()
    dfs = {}

    try:
        df_costos = transformador.transformar_costos_unitarios()
        dfs["costos_unitarios"] = df_costos
    except FileNotFoundError:
        logger.error("No se encontró costos_unitarios.csv. Ejecuta primero extractor_igss.py")

    try:
        df_ejec = transformador.transformar_ejecucion_gastos()
        dfs["ejecucion_gastos"] = df_ejec
    except FileNotFoundError:
        logger.error("No se encontró ejecucion_gastos.csv. Ejecuta primero extractor_igss.py")

    try:
        ruta_deptos = PROCESSED_DIR / "costos_departamento.csv"
        if ruta_deptos.exists():
            df_deptos = transformador.transformar_costos_departamento()
            dfs["costos_departamento"] = df_deptos
    except Exception as e:
        logger.warning(f"No se pudo transformar costos_departamento: {e}")

    # Reporte de calidad
    reporte = transformador.generar_reporte_calidad(dfs)
    logger.info("\n── REPORTE DE CALIDAD ──────────────────────────────────")
    for dataset, info in reporte.items():
        logger.info(f"Dataset: {dataset}")
        logger.info(f"  Registros: {info['total_registros']}")
        total_nulos = sum(info['nulos_por_columna'].values())
        logger.info(f"  Total nulos: {total_nulos}")
        if "outliers_hospitalizacion" in info:
            logger.info(f"  Outliers hospitalización: {info['outliers_hospitalizacion']}")
        if "distribucion_riesgo" in info:
            logger.info(f"  Distribución riesgo: {info['distribucion_riesgo']}")

    logger.info("=" * 60)
    logger.success("✅ Transformación completada exitosamente")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
