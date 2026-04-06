# Consideraciones del Proyecto

**BI — Justicia en Salud Guatemala (IGSS)**  
Documento de supuestos, decisiones técnicas y limitaciones.

---

## Consideraciones Técnicas

### 1. Tecnología de Base de Datos

**Decisión:** Se usa SQLite en lugar de PostgreSQL o MySQL.

**Justificación:** El volumen de datos del proyecto es de miles de registros (no millones). SQLite es suficiente, no requiere servidor, es completamente portable y facilita la entrega y revisión académica del proyecto. Para un entorno de producción real, se recomendaría PostgreSQL con esquema de particionamiento por año.

### 2. Formato del Excel Fuente

**Situación:** El archivo `.xlsm` contiene fórmulas dinámicas (`GETPIVOTDATA`, `IF`, `VLOOKUP`) que no se calculan al leerlo con `openpyxl` en modo `data_only=True`.

**Solución adoptada:** Se usa `data_only=True` para capturar los valores calculados en el último guardado del archivo. Las fórmulas que quedaron sin calcular (principalmente datos de 2025 más recientes) se excluyen del análisis de costos unitarios y se documenta esta limitación.

### 3. Deflactación de Precios

**Decisión:** Se aplica deflactación usando el IPC de Guatemala (BANGUAT) con base en 2014=100.

**Supuesto:** Los valores del IPC usados son aproximaciones basadas en datos históricos conocidos. Para producción real, deberían extraerse directamente desde la API del BANGUAT.

### 4. Datos de Año 2025 Incompletos

**Situación:** La hoja H1 del Excel muestra que los costos unitarios de 2025 referencian otra hoja y no tienen valores calculados en el archivo estático.

**Decisión:** Los costos unitarios de 2025 se excluyen del análisis histórico. La ejecución financiera 2025 (Ejec. y Gastos) sí tiene valores y se incluye.

### 5. Nivel de Granularidad

**Limitación:** Los datos disponibles son a nivel de **departamento**, no de **unidad de salud** (hospital, clínica). Esto significa que no podemos identificar cuál hospital específico presenta las anomalías, solo el departamento.

**Recomendación:** Para un análisis más profundo, se debería solicitar a través de la Ley de Acceso a la Información Pública los datos a nivel de unidad ejecutora.

---

## Consideraciones Éticas

### 6. Naturaleza del Análisis

**Aclaración importante:** Los hallazgos de este proyecto son de carácter **estadístico y descriptivo**. Un patrón estadístico anómalo (outlier) NO es equivalente a prueba legal de corrupción. El análisis identifica áreas que merecen investigación adicional, no establece culpabilidad de personas o instituciones.

### 7. Fuentes de Datos

**Compromiso:** Todos los datos usados son de acceso público, conforme al Decreto 57-2008 "Ley de Acceso a la Información Pública" de Guatemala. No se han usado datos confidenciales, privados o obtenidos de forma ilegal.

### 8. Privacidad

**Decisión:** El análisis es estrictamente institucional. No se nombran ni identifican personas individuales. El foco es en patrones institucionales del IGSS como entidad pública.

---

## Limitaciones del Proyecto

| Limitación | Impacto | Mitigación |
|-----------|---------|-----------|
| Sin datos de proveedores (GUATECOMPRAS) | No se puede cruzar costo con contratos | Dejar documentado para fase futura |
| Datos a nivel departamental, no de unidad | No se puede identificar hospital específico | Usar LAIP para datos más granulares |
| IPC aproximado | Deflactación no exacta | Documentar supuesto, usar fuente BANGUAT |
| Excel con fórmulas dinámicas | Algunos datos de 2025 sin calcular | Excluir y documentar |
| Sin datos de Contraloría integrados | No se puede cruzar con auditorías | Futura fuente de enriquecimiento |

---

## Parte del Gobierno de Datos

Como parte del gobierno de datos, este proyecto establece:

- **Catálogos de referencia:** `dim_departamento` y `dim_servicio` son los catálogos maestros del dominio.
- **Trazabilidad:** Cada registro en las tablas de hechos incluye la columna `fuente_dato` indicando su origen.
- **Auditoría:** La tabla `red_flags_log` registra automáticamente todas las anomalías detectadas con timestamp.
- **Versionamiento:** El repositorio en Git sirve como sistema de control de versiones del código y la documentación.
- **Diccionario de datos:** Cada tabla está documentada en `docs/03_fase_planeacion.md` con descripción de cada campo.
