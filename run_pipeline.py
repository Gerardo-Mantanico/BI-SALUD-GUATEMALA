"""
run_pipeline.py
===============
Pipeline completo de BI — Justicia en Salud Guatemala (IGSS)

Ejecuta todas las fases en secuencia:
  1. Extracción (ingesta/extractor_igss.py)
  2. Transformación (transformacion/limpieza.py)
  3. Carga DW (warehouse/carga_dw.py)
  4. Análisis (analisis/red_flags.py)

Uso:
    python run_pipeline.py
    python run_pipeline.py --solo-analisis   (salta ETL si el DW ya existe)
"""

import sys
import time
import argparse
import subprocess
from pathlib import Path
from loguru import logger

BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
logger.add(LOG_DIR / "pipeline_{time}.log", rotation="1 MB", level="INFO")

PASOS = [
    ("Extracción",     "src/ingesta/extractor_igss.py"),
    ("Transformación", "src/transformacion/limpieza.py"),
    ("Carga DW",       "src/warehouse/carga_dw.py"),
    ("Análisis",       "src/analisis/red_flags.py"),
]


def ejecutar_paso(nombre: str, script: str) -> bool:
    """Ejecuta un script Python y retorna True si tuvo éxito."""
    ruta = BASE_DIR / script
    logger.info(f"\n{'='*50}")
    logger.info(f"▶ Ejecutando: {nombre}")
    logger.info(f"  Script: {script}")
    logger.info(f"{'='*50}")

    inicio = time.time()
    resultado = subprocess.run(
        [sys.executable, str(ruta)],
        capture_output=False
    )
    duracion = round(time.time() - inicio, 1)

    if resultado.returncode == 0:
        logger.success(f"  ✅ {nombre} completado en {duracion}s")
        return True
    else:
        logger.error(f"  ❌ {nombre} falló (código {resultado.returncode})")
        return False


def main():
    parser = argparse.ArgumentParser(description="Pipeline BI - Salud Guatemala")
    parser.add_argument("--solo-analisis", action="store_true",
                        help="Solo ejecutar análisis (el DW ya existe)")
    args = parser.parse_args()

    print("\n" + "="*60)
    print("🏥 PIPELINE BI — JUSTICIA EN SALUD GUATEMALA (IGSS)")
    print("="*60 + "\n")

    inicio_total = time.time()
    pasos = PASOS[3:] if args.solo_analisis else PASOS
    errores = []

    for nombre, script in pasos:
        ok = ejecutar_paso(nombre, script)
        if not ok:
            errores.append(nombre)

    duracion_total = round(time.time() - inicio_total, 1)
    print("\n" + "="*60)

    if not errores:
        print(f"✅ PIPELINE COMPLETADO exitosamente en {duracion_total}s")
        print("\nPróximos pasos:")
        print("  → Dashboard: python src/dashboard/app.py")
        print("  → Abrir:     http://localhost:8050")
    else:
        print(f"⚠️  PIPELINE completado con {len(errores)} errores: {errores}")
        print("\n   Revisa los logs en data/logs/ para más detalles.")
        print("   Asegúrate de haber colocado el Excel en data/raw/")

    print("="*60 + "\n")


if __name__ == "__main__":
    main()
