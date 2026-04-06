# Fase 2 — Preparación de Datos

**Punteo: 10 pts**  
**Objetivo:** Limpiar, transformar y estandarizar los datos extraídos del Excel del IGSS para que puedan ser cargados al Data Warehouse.

---

## 2.1 Proceso ETL (Extract, Transform, Load)

El proceso ETL para este proyecto sigue tres etapas bien definidas:

```
[Excel IGSS .xlsm]
       ↓ EXTRACT
[Python openpyxl → CSV en data/raw/]
       ↓ TRANSFORM  
[Limpieza, normalización, validación → data/processed/]
       ↓ LOAD
[SQLite Data Warehouse → data/warehouse/igss_salud_dw.db]
```

---

## 2.2 Extracción (Extract)

### Fuente: IGSS_en_Cifras_2025.xlsm

Se extraen 3 conjuntos de datos principales de las hojas del Excel:

#### Conjunto 1: Costos Unitarios (Hoja H1)
- **Columnas:** Año, Hospitalización, Consulta_Externa, Emergencia, Primeros_Auxilios
- **Filas:** 11 registros (2014–2024)
- **Formato destino:** `data/processed/costos_unitarios.csv`

#### Conjunto 2: Ejecución y Gastos por Departamento (Hoja Ejec. y Gastos)
- **Columnas:** ID_Departamento, Departamento, Egresos, Ingresos, Año
- **Filas:** 23 departamentos × 2 años = 46 registros
- **Formato destino:** `data/processed/ejecucion_gastos.csv`

#### Conjunto 3: Costos Totales por Departamento (Hoja 5.1 TD_Costos)
- **Columnas:** ID_Dpto, Departamento, Mes, Año, Costo_Total
- **Filas:** 22 departamentos × 12 meses × 5 años ≈ 1,320 registros
- **Formato destino:** `data/processed/costos_departamento.csv`

---

## 2.3 Transformación (Transform)

### Reglas de Limpieza Aplicadas

| Regla | Descripción | Implementación |
|-------|-------------|----------------|
| **T-01** | Eliminar filas con fórmulas no calculadas | Filtrar `isinstance(val, str) and val.startswith('=')` |
| **T-02** | Normalizar nombres de departamentos | Diccionario de mapeo estandarizado |
| **T-03** | Convertir montos a tipo float | `pd.to_numeric(col, errors='coerce')` |
| **T-04** | Aplicar deflactor IPC para valores reales | Cruzar con índice BANGUAT (base 2014=100) |
| **T-05** | Calcular brecha financiera | `brecha = egresos - ingresos` |
| **T-06** | Calcular ratio egresos/ingresos | `ratio = egresos / ingresos` |
| **T-07** | Marcar outliers estadísticos | Z-score > 2.5 = anomalía |
| **T-08** | Eliminar registros duplicados | `df.drop_duplicates()` |
| **T-09** | Validar rangos de montos | Rechazar negativos o > Q50,000M |
| **T-10** | Estandarizar IDs de departamento | Código numérico 1–22 + 30 (Multiregional) |

### Diccionario de Normalización de Departamentos

```python
DEPTO_MAP = {
    "Guatemala": 1,
    "El Progreso": 2,
    "Sacatepéquez": 3,
    "Chimaltenango": 4,
    "Escuintla": 5,
    "Santa Rosa": 6,
    "Sololá": 7,
    "Totonicapán": 8,
    "Quetzaltenango": 9,
    "Suchitepéquez": 10,
    "Retalhuleu": 11,
    "San Marcos": 12,
    "Huehuetenango": 13,
    "Quiché": 14,
    "Baja Verapaz": 15,
    "Alta Verapaz": 16,
    "Petén": 17,
    "Izabal": 18,
    "Zacapa": 19,
    "Chiquimula": 20,
    "Jalapa": 21,
    "Jutiapa": 22
}
```

---

## 2.4 Resultado de la Limpieza

### Dataset: costos_unitarios.csv

| Campo | Tipo | Nulos antes | Nulos después | Transformación |
|-------|------|------------|--------------|----------------|
| Año | integer | 0 | 0 | Ninguna |
| Hospitalizacion_Q | float | 1 (2025) | 1 (excluido) | Excluir 2025 incompleto |
| Consulta_Externa_Q | float | 1 (2025) | 1 (excluido) | Excluir 2025 incompleto |
| Emergencia_Q | float | 1 (2025) | 1 (excluido) | Excluir 2025 incompleto |
| Primeros_Auxilios_Q | float | 1 (2025) | 1 (excluido) | Excluir 2025 incompleto |

**Registros:** 11 (2014–2024) | **Completitud:** 100% en período analizado

### Dataset: ejecucion_gastos.csv

| Campo | Tipo | Nulos | Transformación |
|-------|------|-------|----------------|
| ID_Departamento | integer | 0 | Mapeo estándar |
| Departamento | string | 0 | Normalización de nombres |
| Egresos_Q | float | 0 | Conversión numérica |
| Ingresos_Q | float | 0 | Conversión numérica |
| Anio | integer | 0 | Añadida columna |
| Brecha_Q | float | 0 | Calculada: Egresos - Ingresos |
| Ratio_EI | float | 0 | Calculada: Egresos / Ingresos |

**Registros:** 46 | **Completitud:** 100%

---

## 2.5 Análisis de Calidad Post-Transformación

### Detección de Outliers — Costos Unitarios

Aplicando Z-score sobre la serie de costo de hospitalización:

| Año | Costo Q | Z-Score | ¿Outlier? |
|-----|---------|---------|-----------|
| 2019 | 6,029.50 | -0.32 | No |
| 2020 | 10,703.21 | **2.89** | ⚠️ SÍ |
| 2021 | 14,470.93 | **3.78** | ⚠️ SÍ |
| 2022 | 10,683.55 | **2.88** | ⚠️ SÍ |

Los años 2020, 2021 y 2022 son estadísticamente atípicos. Se marcan con flag `es_outlier = True` pero NO se eliminan — son el núcleo del análisis.

### Detección de Outliers — Ratio Egresos/Ingresos 2025

| Departamento | Ratio | ¿Outlier? |
|-------------|-------|-----------|
| Suchitepéquez | 6.17 | ⚠️ SÍ |
| Quetzaltenango | 5.86 | ⚠️ SÍ |
| Izabal | 4.62 | ⚠️ SÍ |
| San Marcos | 4.13 | ⚠️ SÍ |
| Guatemala | 1.31 | No |

---

## 2.6 Estructura de Archivos CSV Generados

### costos_unitarios.csv
```
anio,hospitalizacion_q,consulta_externa_q,emergencia_q,primeros_auxilios_q,es_outlier_hosp
2014,5736.88,604.75,225.10,130.42,False
2015,5979.26,636.32,228.80,130.71,False
...
2021,14470.93,763.37,371.90,166.81,True
```

### ejecucion_gastos.csv
```
id_departamento,departamento,anio,egresos_q,ingresos_q,brecha_q,ratio_ei,flag_anomalia
1,Guatemala,2024,15403042880.19,13458687505.72,1944355374.47,1.14,False
9,Quetzaltenango,2025,778963466.52,132915632.81,646047833.71,5.86,True
...
```

### costos_departamento.csv
```
id_departamento,departamento,anio,mes,costo_total_q
1,Guatemala,2021,Enero,277536908.10
1,Guatemala,2021,Febrero,380641306.77
...
```
