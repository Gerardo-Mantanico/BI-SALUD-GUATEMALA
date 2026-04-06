# Fase 6 — Operacionalización

**Punteo: 7 pts**  
**Objetivo:** Automatizar la actualización del sistema cuando el IGSS publique nuevas versiones del Excel anual.

---

## 6.1 Estrategia de Actualización

El IGSS publica el informe "IGSS en Cifras" una vez al año (generalmente en enero/febrero del siguiente año). La operacionalización consiste en detectar, descargar y procesar automáticamente el nuevo archivo.

### Flujo de Actualización Automática

```
[Scheduler mensual (cron/Task Scheduler)]
         ↓
[check_update.py — Verifica si hay nueva versión]
         ↓ (si hay nueva versión)
[Descarga nuevo Excel desde igssgt.org]
         ↓
[run_pipeline.py — Ejecuta ETL completo]
         ↓
[Actualización incremental del DW]
         ↓  
[Regeneración de vistas y KPIs]
         ↓
[Dashboard actualizado automáticamente]
         ↓
[Envío de reporte de cambios por email]
```

---

## 6.2 Script de Verificación de Actualización

```python
# src/operacionalizacion/check_update.py

import hashlib
import requests
from pathlib import Path

URL_IGSS = "https://www.igssgt.org/informes-y-estadisticas/"
HASH_FILE = Path("data/raw/.last_hash")

def verificar_nueva_version() -> bool:
    """Compara el hash del archivo actual vs. el disponible en igssgt.org."""
    # Hash del archivo local
    local_path = Path("data/raw/IGSS_en_Cifras_2025.xlsm")
    if not local_path.exists():
        return True  # No hay archivo, descargar
    
    with open(local_path, "rb") as f:
        hash_local = hashlib.md5(f.read()).hexdigest()
    
    # Comparar con hash guardado
    if HASH_FILE.exists():
        hash_previo = HASH_FILE.read_text().strip()
        if hash_local == hash_previo:
            print("No hay nueva versión disponible.")
            return False
    
    HASH_FILE.write_text(hash_local)
    return True
```

---

## 6.3 Configuración de Scheduler

### Linux/Mac (cron)
```bash
# Verificar actualizaciones el 1ro de cada mes a las 6am
0 6 1 * * cd /ruta/bi-salud-gt && python src/operacionalizacion/check_update.py >> data/logs/cron.log 2>&1
```

### Windows (Task Scheduler)
```powershell
schtasks /create /tn "IGSS_BI_Update" /tr "python C:\bi-salud-gt\src\operacionalizacion\check_update.py" /sc monthly /d 1 /st 06:00
```

---

## 6.4 Actualización Incremental del DW

Para no recrear todo el DW cada año, se implementa carga incremental:

```sql
-- Insertar solo registros nuevos (evitar duplicados)
INSERT OR IGNORE INTO fact_ejecucion 
    (id_departamento, id_tiempo, egresos_q, ...)
SELECT ... FROM staging_ejecucion
WHERE NOT EXISTS (
    SELECT 1 FROM fact_ejecucion fe2
    WHERE fe2.id_departamento = staging_ejecucion.id_departamento
    AND fe2.id_tiempo = staging_ejecucion.id_tiempo
);
```

---

## 6.5 Nuevo DataMart — Tendencias Multianuales

Con cada actualización se puede añadir un nuevo DataMart de tendencias:

```sql
CREATE VIEW dm_tendencias AS
SELECT 
    s.nombre AS servicio,
    MIN(t.anio) AS anio_inicio,
    MAX(t.anio) AS anio_fin,
    MIN(fc.costo_unitario_q) AS costo_minimo,
    MAX(fc.costo_unitario_q) AS costo_maximo,
    AVG(fc.costo_unitario_q) AS costo_promedio,
    -- Tasa de crecimiento anual compuesta (CAGR)
    ROUND(
        (POWER(MAX(fc.costo_unitario_q) / MIN(fc.costo_unitario_q), 
               1.0 / (MAX(t.anio) - MIN(t.anio))) - 1) * 100, 2
    ) AS cagr_pct
FROM fact_costos fc
JOIN dim_tiempo t ON fc.id_tiempo = t.id_tiempo
JOIN dim_servicio s ON fc.id_servicio = s.id_servicio
WHERE t.es_anual = 1
GROUP BY s.nombre;
```
