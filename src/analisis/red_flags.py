"""
red_flags.py
============
Fase 4 — Análisis estadístico y detección de anomalías.

Aplica indicadores BI y análisis estadístico sobre el Data Warehouse
para detectar patrones consistentes con corrupción o ineficiencia
en el sistema de salud del IGSS.

Uso:
    python src/analisis/red_flags.py

Genera:
    exports/hallazgos_red_flags.csv
    exports/resumen_ejecutivo.txt
"""

import sqlite3
from pathlib import Path
import pandas as pd
import numpy as np
from scipy import stats
from datetime import datetime
from loguru import logger

# ── Configuración ───────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "data" / "warehouse" / "igss_salud_dw.db"
EXPORTS_DIR = BASE_DIR / "exports"
LOG_DIR = BASE_DIR / "data" / "logs"
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger.add(LOG_DIR / "analisis_{time}.log", rotation="1 MB", level="INFO")


class AnalizadorRedFlags:
    """Motor de análisis estadístico para detección de anomalías en datos del IGSS."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.hallazgos = []

    def cerrar(self):
        self.conn.close()

    def _query(self, sql: str, params=()) -> pd.DataFrame:
        return pd.read_sql_query(sql, self.conn, params=params)

    # ─────────────────────────────────────────────────────────────
    # Análisis 1: Evolución histórica de costos unitarios
    # ─────────────────────────────────────────────────────────────
    def analizar_costos_historicos(self) -> dict:
        """
        Analiza la evolución histórica de costos unitarios de hospitalización.
        Detecta inflexiones y cambios estructurales (breakpoints).
        """
        logger.info("Analizando costos históricos (H1)...")

        df = self._query("""
            SELECT t.anio, fc.costo_unitario_q, fc.es_outlier, fc.z_score,
                   fc.variacion_pct, fc.alerta_variacion, s.codigo
            FROM fact_costos fc
            JOIN dim_tiempo t ON fc.id_tiempo = t.id_tiempo
            JOIN dim_servicio s ON fc.id_servicio = s.id_servicio
            WHERE t.es_anual = 1 AND s.codigo = 'HOSP'
            ORDER BY t.anio
        """)

        if df.empty:
            logger.warning("No hay datos de costos históricos en el DW.")
            return {}

        # Estadísticas descriptivas
        stats_desc = {
            "media": round(df["costo_unitario_q"].mean(), 2),
            "mediana": round(df["costo_unitario_q"].median(), 2),
            "desv_std": round(df["costo_unitario_q"].std(), 2),
            "min": round(df["costo_unitario_q"].min(), 2),
            "max": round(df["costo_unitario_q"].max(), 2),
            "anio_min": int(df.loc[df["costo_unitario_q"].idxmin(), "anio"]),
            "anio_max": int(df.loc[df["costo_unitario_q"].idxmax(), "anio"]),
        }

        # Detectar punto de inflexión (cambio más abrupto)
        df["variacion_abs"] = df["variacion_pct"].abs()
        idx_max_var = df["variacion_abs"].idxmax()
        inflexion = {
            "anio": int(df.loc[idx_max_var, "anio"]),
            "variacion_pct": round(float(df.loc[idx_max_var, "variacion_pct"]), 1),
            "costo_q": round(float(df.loc[idx_max_var, "costo_unitario_q"]), 2)
        }

        # Outliers
        outliers = df[df["es_outlier"] == True][["anio", "costo_unitario_q", "z_score"]]

        resultado = {
            "tipo": "COSTOS_HISTORICOS_HOSP",
            "estadisticas": stats_desc,
            "punto_inflexion": inflexion,
            "n_outliers": len(outliers),
            "anios_outlier": outliers["anio"].tolist()
        }

        # Generar hallazgo si hay anomalía
        if len(outliers) > 0:
            self.hallazgos.append({
                "codigo": "RF-A1",
                "tipo": "Costo hospitalización atípico",
                "descripcion": (
                    f"El costo de hospitalización presenta {len(outliers)} años atípicos "
                    f"(Z-score > 2.5): {outliers['anio'].tolist()}. "
                    f"El incremento máximo fue de {inflexion['variacion_pct']}% en {inflexion['anio']}. "
                    f"Rango de costos: Q{stats_desc['min']:,.2f} a Q{stats_desc['max']:,.2f}."
                ),
                "criticidad": "ALTA" if len(outliers) >= 3 else "MEDIA",
                "departamento": "Nacional",
                "anio": inflexion["anio"]
            })

        logger.success(
            f"  Inflexión máxima: {inflexion['variacion_pct']}% en {inflexion['anio']} | "
            f"Outliers: {len(outliers)} años"
        )
        return resultado

    # ─────────────────────────────────────────────────────────────
    # Análisis 2: Brecha financiera por departamento
    # ─────────────────────────────────────────────────────────────
    def analizar_brechas_financieras(self) -> pd.DataFrame:
        """
        Analiza la brecha egresos-ingresos por departamento y año.
        Clasifica por nivel de riesgo y detecta outliers.
        """
        logger.info("Analizando brechas financieras por departamento...")

        df = self._query("""
            SELECT t.anio, d.nombre AS departamento, d.region,
                   fe.egresos_q, fe.ingresos_q, fe.brecha_q,
                   fe.ratio_ei, fe.nivel_riesgo, fe.flag_anomalia
            FROM fact_ejecucion fe
            JOIN dim_tiempo t ON fe.id_tiempo = t.id_tiempo
            JOIN dim_departamento d ON fe.id_departamento = d.id_departamento
            WHERE d.id_departamento != 30
            ORDER BY t.anio, fe.ratio_ei DESC
        """)

        if df.empty:
            logger.warning("No hay datos de ejecución financiera en el DW.")
            return df

        # Top departamentos con mayor brecha por año
        for anio in df["anio"].unique():
            subset = df[df["anio"] == anio].head(5)
            criticos = subset[subset["nivel_riesgo"].isin(["CRÍTICO", "ALTO"])]

            if not criticos.empty:
                for _, row in criticos.iterrows():
                    self.hallazgos.append({
                        "codigo": "RF-A2",
                        "tipo": "Brecha financiera crítica",
                        "descripcion": (
                            f"[{anio}] {row['departamento']}: ratio egresos/ingresos = "
                            f"{row['ratio_ei']:.2f}x (nivel {row['nivel_riesgo']}). "
                            f"Brecha de Q{row['brecha_q']:,.0f}. "
                            f"Por cada Q1 recaudado se gastan Q{row['ratio_ei']:.2f}."
                        ),
                        "criticidad": "ALTA" if row["nivel_riesgo"] == "CRÍTICO" else "MEDIA",
                        "departamento": row["departamento"],
                        "anio": anio
                    })

        n_criticos = len(df[df["nivel_riesgo"] == "CRÍTICO"])
        n_altos = len(df[df["nivel_riesgo"] == "ALTO"])
        logger.success(f"  Departamentos en nivel CRÍTICO: {n_criticos} | ALTO: {n_altos}")
        return df

    # ─────────────────────────────────────────────────────────────
    # Análisis 3: Índice HHI de concentración de gasto
    # ─────────────────────────────────────────────────────────────
    def calcular_hhi_gasto(self) -> dict:
        """
        Calcula el Índice Herfindahl-Hirschman (HHI) de concentración
        del gasto en salud por departamento.
        Un HHI > 2500 indica alta concentración (posible inequidad sistémica).
        """
        logger.info("Calculando HHI de concentración de gasto...")

        df = self._query("""
            SELECT t.anio, d.nombre AS departamento, fe.egresos_q
            FROM fact_ejecucion fe
            JOIN dim_tiempo t ON fe.id_tiempo = t.id_tiempo
            JOIN dim_departamento d ON fe.id_departamento = d.id_departamento
            WHERE d.id_departamento != 30
        """)

        resultados = {}
        for anio in df["anio"].unique():
            subset = df[df["anio"] == anio].copy()
            total = subset["egresos_q"].sum()
            if total == 0:
                continue
            subset["share"] = subset["egresos_q"] / total * 100
            hhi = round((subset["share"] ** 2).sum(), 2)
            resultados[int(anio)] = {
                "hhi": hhi,
                "concentracion": "ALTA" if hhi > 2500 else "MODERADA" if hhi > 1500 else "BAJA",
                "top1_depto": subset.loc[subset["share"].idxmax(), "departamento"],
                "top1_pct": round(subset["share"].max(), 1)
            }
            logger.info(f"  HHI {anio}: {hhi:.0f} ({resultados[int(anio)]['concentracion']}) "
                        f"— Top: {resultados[int(anio)]['top1_depto']} "
                        f"({resultados[int(anio)]['top1_pct']}%)")

        return resultados

    # ─────────────────────────────────────────────────────────────
    # Análisis 4: Regresión lineal de tendencia de costos
    # ─────────────────────────────────────────────────────────────
    def proyectar_tendencia_costos(self) -> dict:
        """
        Proyecta la tendencia futura de costos de hospitalización
        usando regresión lineal. Permite estimar cuándo los costos
        serán insostenibles para el IGSS.
        """
        logger.info("Proyectando tendencia de costos (regresión lineal)...")

        df = self._query("""
            SELECT t.anio, fc.costo_unitario_q
            FROM fact_costos fc
            JOIN dim_tiempo t ON fc.id_tiempo = t.id_tiempo
            JOIN dim_servicio s ON fc.id_servicio = s.id_servicio
            WHERE s.codigo = 'HOSP' AND t.es_anual = 1
            ORDER BY t.anio
        """)

        if len(df) < 4:
            return {}

        x = df["anio"].values
        y = df["costo_unitario_q"].values

        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

        # Proyecciones
        proyecciones = {}
        for anio_futuro in [2026, 2027, 2028, 2030]:
            proyecciones[anio_futuro] = round(slope * anio_futuro + intercept, 2)

        resultado = {
            "pendiente": round(slope, 2),
            "r_cuadrado": round(r_value ** 2, 4),
            "p_value": round(p_value, 6),
            "es_significativa": p_value < 0.05,
            "interpretacion": (
                f"El costo de hospitalización aumenta en promedio Q{slope:.2f} por año. "
                f"R² = {r_value**2:.4f} — la tendencia explica el {r_value**2*100:.1f}% "
                f"de la variación histórica."
            ),
            "proyecciones": proyecciones
        }

        logger.success(
            f"  Tendencia: +Q{slope:.2f}/año | R²={r_value**2:.4f} | "
            f"Proyección 2028: Q{proyecciones.get(2028, 'N/A'):,.2f}"
        )
        return resultado

    # ─────────────────────────────────────────────────────────────
    # Exportar hallazgos
    # ─────────────────────────────────────────────────────────────
    def exportar_hallazgos(self):
        """Exporta todos los hallazgos a CSV y genera resumen ejecutivo."""
        if self.hallazgos:
            df_flags = pd.DataFrame(self.hallazgos)
            out_csv = EXPORTS_DIR / "hallazgos_red_flags.csv"
            df_flags.to_csv(out_csv, index=False, encoding="utf-8")
            logger.success(f"Red flags exportadas: {out_csv}")

        # Resumen ejecutivo en texto
        resumen = [
            "=" * 65,
            "RESUMEN EJECUTIVO — BI JUSTICIA EN SALUD GUATEMALA (IGSS)",
            f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 65,
            "",
            "HALLAZGOS IDENTIFICADOS:",
            f"Total de red flags: {len(self.hallazgos)}",
            f"Criticidad ALTA: {sum(1 for h in self.hallazgos if h['criticidad']=='ALTA')}",
            f"Criticidad MEDIA: {sum(1 for h in self.hallazgos if h['criticidad']=='MEDIA')}",
            "",
            "DETALLE DE HALLAZGOS:",
        ]

        for i, h in enumerate(self.hallazgos, 1):
            resumen.extend([
                f"\n[{i}] {h['codigo']} — {h['tipo']} ({h['criticidad']})",
                f"    Departamento: {h['departamento']} | Año: {h['anio']}",
                f"    {h['descripcion']}"
            ])

        resumen.extend([
            "",
            "=" * 65,
            "RECOMENDACIÓN: Estos hallazgos deben ser contrastados con",
            "datos de GUATECOMPRAS y auditorías de la Contraloría antes",
            "de emitir conclusiones definitivas.",
            "=" * 65
        ])

        out_txt = EXPORTS_DIR / "resumen_ejecutivo.txt"
        with open(out_txt, "w", encoding="utf-8") as f:
            f.write("\n".join(resumen))
        logger.success(f"Resumen ejecutivo: {out_txt}")

        # Imprimir resumen en consola
        print("\n".join(resumen))


def main():
    logger.info("=" * 60)
    logger.info("IGSS BI — Fase 4: Análisis de Red Flags")
    logger.info("=" * 60)

    if not DB_PATH.exists():
        logger.error(f"No se encontró el DW: {DB_PATH}")
        logger.error("Ejecuta primero: python src/warehouse/carga_dw.py")
        return

    analizador = AnalizadorRedFlags(DB_PATH)
    try:
        analizador.analizar_costos_historicos()
        analizador.analizar_brechas_financieras()
        analizador.calcular_hhi_gasto()
        analizador.proyectar_tendencia_costos()
        analizador.exportar_hallazgos()
        logger.success("✅ Análisis de red flags completado")
    finally:
        analizador.cerrar()


if __name__ == "__main__":
    main()
