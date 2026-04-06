# 🏥 BI - Justicia en Salud Guatemala (IGSS)

**Proyecto de Business Intelligence — Ciclo de Vida del Dato**  
Curso: Inteligencia de Negocios · Universidad · 2026  
Enfoque: Análisis de corrupción y eficiencia en el sistema de salud del IGSS

---

## 📌 Descripción

Este proyecto implementa un sistema completo de Business Intelligence para analizar el estado de la justicia en salud en Guatemala, con foco en el **Instituto Guatemalteco de Seguridad Social (IGSS)**. Se aplica el ciclo de vida del dato completo: desde la ingesta de datos oficiales hasta dashboards interactivos que permiten detectar anomalías, brechas financieras y posibles indicadores de corrupción en el sector salud.

### Hipótesis Central

> "Existe evidencia estadística de anomalías en la ejecución presupuestaria, los costos unitarios de servicios médicos y la brecha ingresos-egresos del IGSS que sugieren irregularidades en la gestión de los recursos destinados a la salud pública en Guatemala."

---

## 🗂️ Estructura del Repositorio

```
bi-salud-guatemala/
│
├── README.md                        ← Este archivo
├── requirements.txt                 ← Dependencias Python
├── .gitignore                       ← Archivos ignorados por git
│
├── docs/                            ← Documentación del proyecto
│   ├── 01_fase_descubrimiento.md    ← Calidad y fuentes de datos
│   ├── 02_fase_preparacion.md       ← Limpieza y transformación
│   ├── 03_fase_planeacion.md        ← Modelo dimensional
│   ├── 04_fase_construccion.md      ← Data Warehouse
│   ├── 05_fase_comunicacion.md      ← Dashboard y reportes
│   ├── 06_fase_operacionalizacion.md← Automatización
│   └── consideraciones.md           ← Supuestos y decisiones técnicas
│
├── data/
│   ├── raw/                         ← Datos originales sin modificar
│   │   └── IGSS_en_Cifras_2025.xlsm ← Fuente IGSS oficial
│   ├── processed/                   ← Datos limpios en CSV
│   │   ├── costos_unitarios.csv
│   │   ├── ejecucion_gastos.csv
│   │   └── poblacion_protegida.csv
│   └── warehouse/                   ← Base de datos SQLite del DW
│       └── igss_salud_dw.db
│
├── src/
│   ├── ingesta/
│   │   └── extractor_igss.py        ← Extrae datos del Excel IGSS
│   ├── transformacion/
│   │   └── limpieza.py              ← Limpieza y normalización
│   ├── warehouse/
│   │   └── carga_dw.py              ← Carga al Data Warehouse
│   ├── analisis/
│   │   └── red_flags.py             ← Detección de anomalías
│   └── dashboard/
│       └── app.py                   ← Dashboard Dash/Plotly
│
├── sql/
│   ├── crear_esquema.sql            ← DDL del Data Warehouse
│   └── consultas_analiticas.sql     ← Queries BI
│
├── notebooks/
│   └── analisis_exploratorio.ipynb  ← EDA inicial
│
└── exports/
    └── reporte_hallazgos.pdf        ← Reporte final de hallazgos
```

---

## 🔄 Ciclo de Vida del Dato

```
[IGSS Excel Oficial] → [Extracción] → [Limpieza] → [Data Warehouse]
                                                          ↓
                                               [Análisis Estadístico]
                                                          ↓
                                               [Dashboard Interactivo]
                                                          ↓
                                               [Reporte de Hallazgos]
```

### Fases Implementadas

| Fase | Descripción | Punteo | Archivo |
|------|-------------|--------|---------|
| 1. Descubrimiento | Calidad y evaluación de fuentes | 25 pts | `docs/01_fase_descubrimiento.md` |
| 2. Preparación | ETL y limpieza de datos | 10 pts | `docs/02_fase_preparacion.md` |
| 3. Planeación | Modelo dimensional (esquema estrella) | 10 pts | `docs/03_fase_planeacion.md` |
| 4. Construcción | Data Warehouse SQLite | 10 pts | `docs/04_fase_construccion.md` |
| 5. Comunicación | Dashboard Plotly/Dash | 15 pts | `docs/05_fase_comunicacion.md` |
| 6. Operacionalización | Automatización y actualización | 7 pts | `docs/06_fase_operacionalizacion.md` |

---

## 🚀 Cómo Ejecutar

### 1. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 2. Colocar el archivo fuente
```bash
# Copiar el Excel del IGSS a la carpeta de datos crudos
cp IGSS_en_Cifras_2025.xlsm data/raw/
```

### 3. Ejecutar el pipeline completo
```bash
# Fase 1: Extracción
python src/ingesta/extractor_igss.py

# Fase 2: Transformación y limpieza
python src/transformacion/limpieza.py

# Fase 3: Carga al Data Warehouse
python src/warehouse/carga_dw.py

# Fase 4: Análisis de red flags
python src/analisis/red_flags.py

# Fase 5: Dashboard
python src/dashboard/app.py
# Abrir: http://localhost:8050
```

### Pipeline completo en un solo comando
```bash
python run_pipeline.py
```

---

## 📊 Principales Hallazgos

### 🔴 Red Flag 1 — Incremento Explosivo de Costos (2019–2021)
El costo de hospitalización pasó de **Q6,029** (2019) a **Q14,470** (2021), un aumento del **140% en 2 años**. La pandemia explica parte del incremento, pero no justifica la magnitud.

### 🔴 Red Flag 2 — Brecha Ingresos-Egresos por Departamento
Quetzaltenango registró Q778M en egresos vs. Q132M en ingresos en 2025 (**brecha de Q646M**). Esta brecha sistémica requiere investigación sobre su origen y destino.

### 🔴 Red Flag 3 — Variación Inexplicable Entre Departamentos
Departamentos con población y servicios similares presentan costos unitarios radicalmente diferentes, sugiriendo posibles irregularidades en la asignación de recursos.

---

## 🗃️ Fuentes de Datos

| Fuente | Tipo | Período | Hojas Clave |
|--------|------|---------|-------------|
| IGSS en Cifras 2025 (oficial) | Excel .xlsm | 1948–2025 | H1, Ejec. y Gastos, 5.1 TD_Costos |
| Contraloría General de Cuentas | PDF reportes | 2015–2024 | Auditorías IGSS |
| GUATECOMPRAS | API REST | 2015–2024 | Contratos médicos |
| Portal Datos Abiertos GT | CKAN API | 2018–2024 | Presupuesto salud |

---

## 👤 Autor

Estudiante de Ingeniería en Sistemas / Ciencias de la Computación  
Curso: Business Intelligence · 2026  
Institución: Universidad de San Carlos de Guatemala (u otra)

---

## 📄 Licencia

Este proyecto es de uso académico. Los datos utilizados son públicos y provienen de fuentes oficiales del gobierno de Guatemala.
