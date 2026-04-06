# Fase 1 — Descubrimiento de Datos

**Punteo: 25 pts**  
**Objetivo:** Evaluar la calidad, disponibilidad y relevancia de las fuentes de datos para el análisis de corrupción en salud en Guatemala.

---

## 1.1 Contexto del Problema

El IGSS (Instituto Guatemalteco de Seguridad Social) es la institución pública responsable de brindar servicios de salud y previsión social a los trabajadores formales de Guatemala. Con más de **Q17,000 millones** en presupuesto anual, es una de las instituciones más grandes del Estado y, históricamente, una de las más afectadas por casos de corrupción documentados.

### Pregunta Analítica Central

> ¿Existen patrones estadísticos en los datos oficiales del IGSS que sean consistentes con prácticas de corrupción, malversación o ineficiencia sistémica en la prestación de servicios de salud?

---

## 1.2 Fuentes de Datos Identificadas

### Fuente Principal: IGSS en Cifras 2025

| Atributo | Valor |
|----------|-------|
| Nombre | IGSS en Cifras — Año 2025 (Anual) |
| Formato | Excel con macros (.xlsm) |
| Tamaño | 26.8 MB |
| Hojas | 115 hojas de cálculo |
| Período | 1948 – 2025 |
| Entidad | Departamento Actuarial y Estadístico, IGSS |
| URL | https://www.igssgt.org |
| Elaboración | Edwin García, Sandra Barrientos, Ruby Ramírez |
| Última actualización | 2026 |

#### Hojas Clave para el Proyecto

| Hoja | Contenido | Relevancia |
|------|-----------|------------|
| `H1` | Costo unitario por tipo de servicio (2014–2025) | ⭐⭐⭐ ALTA |
| `Ejec. y Gastos` | Egresos e ingresos por departamento (2024–2025) | ⭐⭐⭐ ALTA |
| `5.1 TD_Costos` | Costos mensuales por departamento (2021–2025) | ⭐⭐⭐ ALTA |
| `5.2 TD_Costos2` | Costos de consulta externa por departamento | ⭐⭐ MEDIA |
| `Costos_fijos` | Costo total y unitario por servicio (2021) | ⭐⭐⭐ ALTA |
| `D3` | Población protegida por tipo de derechohabiente | ⭐⭐ MEDIA |
| `C1` | Histórico de afiliados cotizantes (1948–2025) | ⭐⭐ MEDIA |
| `G1/G2` | Indicadores demográficos de pensionados | ⭐ BAJA |

### Fuentes Complementarias

| Fuente | Tipo | Disponibilidad | Uso en el Proyecto |
|--------|------|---------------|-------------------|
| Contraloría General de Cuentas | PDF/Web | Pública | Auditorías al IGSS |
| GUATECOMPRAS | API REST | Pública | Contratos de medicamentos e insumos |
| Portal Datos Abiertos GT | API CKAN | Pública | Presupuesto ejecutado salud |
| Ministerio de Salud (MSPAS) | Excel/CSV | Pública | Comparación cobertura |
| BANGUAT | API/CSV | Pública | Deflactor de precios (IPC) |

---

## 1.3 Evaluación de Calidad de Datos

### Criterios de Evaluación (Dimensiones de Calidad)

| Dimensión | Descripción | Evaluación IGSS 2025 |
|-----------|-------------|---------------------|
| **Completitud** | ¿Hay datos faltantes? | ✅ Alta — series completas desde 2014 |
| **Consistencia** | ¿Los datos son coherentes entre hojas? | ⚠️ Media — algunas fórmulas dinámicas complejas |
| **Exactitud** | ¿Los datos reflejan la realidad? | ⚠️ Media — datos oficiales pueden subestimar problemas |
| **Actualidad** | ¿Los datos son recientes? | ✅ Alta — año 2025, publicado en 2026 |
| **Accesibilidad** | ¿Son fáciles de obtener? | ✅ Alta — descarga pública en igssgt.org |
| **Trazabilidad** | ¿Hay metadata de origen? | ✅ Alta — cita formal y elaboradores identificados |
| **Granularidad** | ¿El nivel de detalle es suficiente? | ⚠️ Media — a nivel de departamento, no unidad |

### Problemas de Calidad Identificados

1. **Fórmulas dinámicas en lugar de valores:** Varias hojas contienen `=GETPIVOTDATA(...)` y `=IF(...)` en lugar de valores calculados. Esto requiere evaluar las fórmulas o usar las hojas de tabla dinámica como fuente.

2. **Hoja `H1` — Año 2025 incompleto:** Los datos del año 2025 referencian otra hoja (`='H2'!P13`) y no están calculados en el Excel estático, indicando que los datos más recientes son parciales.

3. **Deflación no aplicada:** Los montos están en quetzales nominales. Para comparaciones históricas (2014–2025) es necesario aplicar el IPC del BANGUAT para obtener valores reales.

4. **Datos de nivel departamental, no de unidad ejecutora:** No se puede determinar con los datos disponibles qué hospital o clínica específica presenta las anomalías, solo el departamento.

5. **Ausencia de datos de proveedores:** El Excel no incluye información sobre los proveedores de insumos médicos, lo cual es clave para el análisis de corrupción en compras.

---

## 1.4 Perfilado de Datos (Data Profiling)

### Costos Unitarios Históricos (Hoja H1)

| Año | Hospitalización (Q) | Consulta Externa (Q) | Emergencia (Q) | Variación Hosp. |
|-----|--------------------|--------------------|----------------|-----------------|
| 2014 | 5,736.88 | 604.75 | 225.10 | — |
| 2015 | 5,979.26 | 636.32 | 228.80 | +4.2% |
| 2016 | 5,482.91 | 620.41 | 238.07 | -8.3% |
| 2017 | 5,655.90 | 625.88 | 248.70 | +3.2% |
| 2018 | 6,424.16 | 611.34 | 248.55 | +13.6% |
| 2019 | 6,029.50 | 537.73 | 210.26 | -6.1% |
| 2020 | 10,703.21 | 826.25 | 373.59 | **+77.5%** ⚠️ |
| 2021 | 14,470.93 | 763.37 | 371.90 | **+35.2%** ⚠️ |
| 2022 | 10,683.55 | 689.28 | 260.53 | -26.2% |
| 2023 | 11,284.65 | 742.27 | 369.55 | +5.6% |
| 2024 | 12,570.93 | 764.09 | 343.05 | +11.4% |

**Hallazgo crítico:** El costo de hospitalización aumentó 140% entre 2019 y 2021, pasando de Q6,029 a Q14,470. Aunque la pandemia de COVID-19 puede explicar parte del incremento, la magnitud es inusualmente alta y merece investigación.

### Ejecución Financiera 2025 por Departamento

| Departamento | Egresos 2025 (Q) | Ingresos 2025 (Q) | Brecha (Q) | Ratio E/I |
|-------------|-----------------|------------------|-----------|-----------|
| Guatemala | 9,037,870,146 | 6,895,525,299 | 2,142,344,847 | 1.31 |
| Quetzaltenango | 778,963,467 | 132,915,633 | 646,047,834 | **5.86** ⚠️ |
| Escuintla | 590,327,749 | 328,653,691 | 261,674,058 | 1.80 |
| Suchitepéquez | 353,088,100 | 57,203,343 | 295,884,757 | **6.17** ⚠️ |
| Izabal | 294,984,610 | 63,869,344 | 231,115,266 | **4.62** ⚠️ |
| Retalhuleu | 156,105,855 | 50,600,381 | 105,505,474 | 3.08 |
| San Marcos | 222,226,886 | 53,832,672 | 168,394,214 | 4.13 |

**Hallazgo crítico:** Quetzaltenango y Suchitepéquez tienen ratios egresos/ingresos de 5.86 y 6.17 respectivamente. Esto significa que por cada Q1 que recaudan, gastan más de Q5. Esta brecha debe ser financiada con transferencias del nivel central, lo cual representa un vector de riesgo de corrupción.

---

## 1.5 Hipótesis Específicas a Validar

Con base en el perfilado inicial, se plantean las siguientes hipótesis analíticas:

**H1:** El incremento de costos de hospitalización en 2020–2021 supera lo que puede explicarse por la pandemia de COVID-19, sugiriendo sobreprecios en compras de insumos.

**H2:** Existe una correlación negativa entre la brecha ingresos-egresos de un departamento y la cobertura efectiva de servicios de salud a la población afiliada.

**H3:** Los departamentos con mayor brecha financiera muestran menor eficiencia operativa (mayor costo por atención) que los departamentos con balance equilibrado.

**H4:** Los costos unitarios presentan variaciones estadísticamente significativas entre departamentos con condiciones demográficas similares, lo cual no puede explicarse únicamente por factores geográficos.

---

## 1.6 Plan de Adquisición de Datos

| Actividad | Herramienta | Responsable | Estado |
|-----------|------------|-------------|--------|
| Descarga IGSS Excel 2025 | Descarga manual | Estudiante | ✅ Completado |
| Extracción hojas clave | Python openpyxl | `src/ingesta/extractor_igss.py` | ✅ Completado |
| Descarga IPC BANGUAT | Web scraping / CSV | Pendiente | 🔄 En proceso |
| Búsqueda en GUATECOMPRAS | API REST | Pendiente | 🔄 En proceso |
| Reportes Contraloría IGSS | Descarga PDF | Pendiente | 🔄 En proceso |

---

## 1.7 Consideraciones Éticas y Legales

- Todos los datos utilizados son públicos y de acceso libre, conforme al **Decreto 57-2008 Ley de Acceso a la Información Pública** de Guatemala.
- El análisis no busca señalar personas individuales, sino identificar patrones institucionales.
- Los hallazgos son de carácter estadístico y descriptivo; no constituyen prueba legal de corrupción.
- Se recomienda que cualquier hallazgo relevante sea reportado a la Contraloría General de Cuentas o al Ministerio Público.
