# Fase 5 — Comunicación (Dashboard)

**Punteo: 15 pts**  
**Objetivo:** Comunicar los hallazgos de forma visual e interactiva mediante un dashboard construido con Plotly/Dash.

---

## 5.1 Arquitectura del Dashboard

El dashboard está construido con **Dash** (Python) y **Plotly** para las gráficas interactivas. Se accede desde cualquier navegador en `http://localhost:8050`.

### Componentes del Dashboard

| Sección | Tipo | Propósito |
|---------|------|-----------|
| KPI Cards (4) | Métricas numéricas | Vista ejecutiva rápida |
| Filtros | Dropdowns | Filtrar por año y región |
| Gráfica de costos históricos | Línea + barras | Evolución y outliers 2014–2024 |
| Gráfica de ratio E/I | Barras horizontales | Comparación por departamento |
| Scatter de riesgo | Dispersión | Egresos vs. ingresos con nivel de riesgo |
| Tabla de red flags | Tabla resumida | Alertas críticas detectadas |
| Tabla de ejecución | DataTable | Detalle completo por departamento |

---

## 5.2 KPIs del Dashboard

| KPI | Descripción | Umbral de Alerta |
|-----|-------------|-----------------|
| Costo Hospitalización | Costo unitario del año seleccionado | > Q10,000 → rojo |
| Brecha Financiera Total | Suma de brechas por año | > Q2,000M → alerta |
| Departamentos en Alerta | Cuenta de niveles ALTO+CRÍTICO | > 5 → rojo |
| Red Flags ALTA | Total de alertas de alta criticidad | > 0 → visible |

---

## 5.3 Narrativa Visual

El dashboard cuenta una historia en 3 capas:

**Capa 1 — ¿Qué pasó con los costos?**  
La gráfica histórica muestra el incremento dramático del costo de hospitalización en 2020–2021. Los marcadores en forma de estrella indican los años estadísticamente atípicos.

**Capa 2 — ¿Dónde está el riesgo financiero?**  
El gráfico de barras horizontales muestra el ratio egresos/ingresos por departamento, con líneas de umbral en 4x (ALTO) y 6x (CRÍTICO).

**Capa 3 — ¿Quiénes son los outliers?**  
El scatter plot posiciona cada departamento según sus ingresos y egresos. Los puntos por encima de la línea diagonal gastan más de lo que recaudan; el color indica el nivel de riesgo.

---

## 5.4 Ejecución del Dashboard

```bash
# Asegurarse de tener el DW construido
python run_pipeline.py

# Lanzar el dashboard
python src/dashboard/app.py

# Abrir en el navegador:
# http://localhost:8050
```
