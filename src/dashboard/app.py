"""
app.py
======
Fase 5 — Dashboard Interactivo (Comunicación)

Dashboard Plotly/Dash para visualizar el análisis de salud y corrupción
en el IGSS de Guatemala. Permite explorar costos unitarios, brechas
financieras y red flags de forma interactiva.

Uso:
    python src/dashboard/app.py
    Luego abrir: http://localhost:8050

Requisitos:
    pip install dash plotly pandas sqlite3
"""

import sqlite3
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import dash
from dash import dcc, html, Input, Output, dash_table
import dash_bootstrap_components as dbc

# ── Configuración ───────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "data" / "warehouse" / "igss_salud_dw.db"

# Colores del tema
COLORS = {
    "primary": "#1A3A5C",    # Azul oscuro institucional
    "danger": "#C0392B",     # Rojo alerta
    "warning": "#E67E22",    # Naranja advertencia
    "success": "#27AE60",    # Verde normal
    "light_bg": "#F8F9FA",
    "card_bg": "#FFFFFF",
    "text": "#2C3E50"
}

NIVEL_COLOR = {
    "NORMAL": COLORS["success"],
    "MODERADO": "#F1C40F",
    "ALTO": COLORS["warning"],
    "CRÍTICO": COLORS["danger"],
}


# ── Carga de datos ───────────────────────────────────────────────────────────
def get_conn():
    return sqlite3.connect(DB_PATH)


def cargar_costos_historicos() -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql_query("""
            SELECT t.anio, fc.costo_unitario_q, fc.z_score,
                   fc.es_outlier, fc.variacion_pct, s.nombre AS servicio
            FROM fact_costos fc
            JOIN dim_tiempo t ON fc.id_tiempo = t.id_tiempo
            JOIN dim_servicio s ON fc.id_servicio = s.id_servicio
            WHERE t.es_anual = 1
            ORDER BY t.anio, s.codigo
        """, conn)


def cargar_ejecucion() -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql_query("""
            SELECT t.anio, d.nombre AS departamento, d.region,
                   fe.egresos_q, fe.ingresos_q, fe.brecha_q,
                   fe.ratio_ei, fe.nivel_riesgo, fe.flag_anomalia
            FROM fact_ejecucion fe
            JOIN dim_tiempo t ON fe.id_tiempo = t.id_tiempo
            JOIN dim_departamento d ON fe.id_departamento = d.id_departamento
            WHERE d.id_departamento != 30
            ORDER BY t.anio, fe.ratio_ei DESC
        """, conn)


def cargar_red_flags() -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql_query("""
            SELECT rf.tipo_flag, rf.descripcion, rf.valor_detectado,
                   rf.umbral, rf.criticidad, rf.fecha_deteccion,
                   d.nombre AS departamento, t.anio
            FROM red_flags_log rf
            LEFT JOIN dim_departamento d ON rf.id_departamento = d.id_departamento
            LEFT JOIN dim_tiempo t ON rf.id_tiempo = t.id_tiempo
            ORDER BY rf.criticidad DESC, t.anio DESC
        """, conn)


# ── Inicializar app ──────────────────────────────────────────────────────────
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.FLATLY],
    title="BI - Justicia en Salud Guatemala (IGSS)",
    suppress_callback_exceptions=True
)

# ── Layout ───────────────────────────────────────────────────────────────────
def build_kpi_card(titulo, valor, subtitulo="", color="primary"):
    return dbc.Card([
        dbc.CardBody([
            html.P(titulo, className="text-muted mb-1", style={"fontSize": "0.85rem"}),
            html.H3(valor, className=f"text-{color} fw-bold mb-0"),
            html.Small(subtitulo, className="text-muted") if subtitulo else html.Span()
        ])
    ], className="shadow-sm h-100")


app.layout = dbc.Container([
    # Header
    dbc.Row([
        dbc.Col([
            html.H2("🏥 BI — Justicia en Salud Guatemala (IGSS)",
                    className="text-white fw-bold mb-0"),
            html.P("Análisis de corrupción e ineficiencia | Datos IGSS 2014–2025",
                   className="text-white-50 mb-0")
        ])
    ], className="py-3 mb-3 rounded",
       style={"background": COLORS["primary"]}),

    # Filtros
    dbc.Row([
        dbc.Col([
            html.Label("Año:", className="fw-semibold"),
            dcc.Dropdown(
                id="filtro-anio",
                options=[{"label": str(a), "value": a} for a in range(2014, 2026)],
                value=2025,
                clearable=False,
                style={"minWidth": "120px"}
            )
        ], width=2),
        dbc.Col([
            html.Label("Región:", className="fw-semibold"),
            dcc.Dropdown(
                id="filtro-region",
                options=[{"label": "Todas", "value": "Todas"}] + [
                    {"label": r, "value": r}
                    for r in ["Metropolitana", "Norte", "Nororiente", "Suroccidente",
                              "Suroriente", "Central", "Noroccidente", "Sur", "Petén"]
                ],
                value="Todas",
                clearable=False
            )
        ], width=3),
    ], className="mb-4 p-3 bg-light rounded"),

    # KPI Cards
    dbc.Row([
        dbc.Col(html.Div(id="kpi-costo-hosp"), width=3),
        dbc.Col(html.Div(id="kpi-brecha"), width=3),
        dbc.Col(html.Div(id="kpi-deptos-alerta"), width=3),
        dbc.Col(html.Div(id="kpi-red-flags"), width=3),
    ], className="mb-4 g-3"),

    # Gráficas principales
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("📈 Evolución histórica de costos unitarios (2014–2024)",
                               className="fw-semibold"),
                dbc.CardBody(dcc.Graph(id="grafica-costos-historicos", style={"height": "350px"}))
            ], className="shadow-sm")
        ], width=8),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("🚨 Red Flags detectadas", className="fw-semibold"),
                dbc.CardBody(html.Div(id="tabla-red-flags-resumen"))
            ], className="shadow-sm")
        ], width=4),
    ], className="mb-4"),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("💰 Ratio Egresos/Ingresos por departamento",
                               className="fw-semibold"),
                dbc.CardBody(dcc.Graph(id="grafica-ratio-depto", style={"height": "400px"}))
            ], className="shadow-sm")
        ], width=7),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("🗺️ Brecha financiera — Nivel de riesgo",
                               className="fw-semibold"),
                dbc.CardBody(dcc.Graph(id="grafica-scatter-riesgo", style={"height": "400px"}))
            ], className="shadow-sm")
        ], width=5),
    ], className="mb-4"),

    # Tabla detallada
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("📋 Detalle de ejecución financiera por departamento",
                               className="fw-semibold"),
                dbc.CardBody(html.Div(id="tabla-ejecucion"))
            ], className="shadow-sm")
        ], width=12)
    ], className="mb-4"),

    # Footer
    dbc.Row([
        dbc.Col([
            html.Hr(),
            html.Small(
                "Fuente: IGSS en Cifras 2025 (Departamento Actuarial y Estadístico, IGSS). "
                "Proyecto BI — Análisis de Justicia en Salud Guatemala. "
                "Los hallazgos son de carácter estadístico y descriptivo.",
                className="text-muted"
            )
        ])
    ])

], fluid=True, style={"backgroundColor": COLORS["light_bg"], "minHeight": "100vh"})


# ── Callbacks ────────────────────────────────────────────────────────────────

@app.callback(
    [Output("kpi-costo-hosp", "children"),
     Output("kpi-brecha", "children"),
     Output("kpi-deptos-alerta", "children"),
     Output("kpi-red-flags", "children")],
    [Input("filtro-anio", "value")]
)
def actualizar_kpis(anio):
    df_costos = cargar_costos_historicos()
    df_ejec = cargar_ejecucion()
    df_flags = cargar_red_flags()

    # KPI 1: Costo hospitalización
    hosp = df_costos[(df_costos["anio"] == anio) & (df_costos["servicio"] == "Hospitalización")]
    costo_hosp = f"Q{hosp['costo_unitario_q'].values[0]:,.2f}" if not hosp.empty else "N/A"
    color_hosp = "danger" if not hosp.empty and hosp["es_outlier"].values[0] else "primary"

    # KPI 2: Brecha financiera total
    ejec_anio = df_ejec[df_ejec["anio"] == anio]
    brecha_total = ejec_anio["brecha_q"].sum()
    brecha_str = f"Q{brecha_total/1e9:.2f}M" if brecha_total < 1e9 else f"Q{brecha_total/1e9:.2f}K M"

    # KPI 3: Departamentos en alerta
    n_alerta = len(ejec_anio[ejec_anio["nivel_riesgo"].isin(["CRÍTICO", "ALTO"])])
    color_alerta = "danger" if n_alerta > 5 else "warning" if n_alerta > 2 else "success"

    # KPI 4: Red flags
    n_flags = len(df_flags[df_flags["criticidad"] == "ALTA"])

    return (
        build_kpi_card("Costo Hospitalización", costo_hosp, f"Año {anio}", color_hosp),
        build_kpi_card("Brecha Financiera Total", f"Q{brecha_total:,.0f}", f"Egresos - Ingresos {anio}", "warning"),
        build_kpi_card("Deptos. en Alerta", str(n_alerta), f"Riesgo ALTO o CRÍTICO — {anio}", color_alerta),
        build_kpi_card("Red Flags ALTA", str(n_flags), "Anomalías críticas detectadas", "danger"),
    )


@app.callback(
    Output("grafica-costos-historicos", "figure"),
    [Input("filtro-anio", "value")]
)
def grafica_costos_historicos(anio_sel):
    df = cargar_costos_historicos()
    df_hosp = df[df["servicio"] == "Hospitalización"].copy()

    if df_hosp.empty:
        return go.Figure().add_annotation(text="Sin datos", showarrow=False)

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Línea principal de costos
    fig.add_trace(go.Scatter(
        x=df_hosp["anio"], y=df_hosp["costo_unitario_q"],
        mode="lines+markers",
        name="Hospitalización (Q)",
        line=dict(color=COLORS["primary"], width=2.5),
        marker=dict(
            size=[12 if o else 8 for o in df_hosp["es_outlier"]],
            color=[COLORS["danger"] if o else COLORS["primary"] for o in df_hosp["es_outlier"]],
            symbol=["star" if o else "circle" for o in df_hosp["es_outlier"]]
        ),
        hovertemplate="<b>Año %{x}</b><br>Costo: Q%{y:,.2f}<extra></extra>"
    ), secondary_y=False)

    # Línea de variación porcentual
    fig.add_trace(go.Bar(
        x=df_hosp["anio"], y=df_hosp["variacion_pct"],
        name="Variación anual %",
        marker_color=[COLORS["danger"] if abs(v or 0) > 30 else COLORS["success"]
                      for v in df_hosp["variacion_pct"]],
        opacity=0.4,
        hovertemplate="<b>Año %{x}</b><br>Variación: %{y:.1f}%<extra></extra>"
    ), secondary_y=True)

    # Línea de umbral de alerta
    fig.add_hline(y=10000, line_dash="dash", line_color=COLORS["warning"],
                  annotation_text="Umbral alerta Q10,000", secondary_y=False)

    # Marcar año seleccionado
    fig.add_vline(x=anio_sel, line_dash="dot", line_color="gray", opacity=0.5)

    fig.update_layout(
        margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(orientation="h", y=-0.15),
        plot_bgcolor="white",
        paper_bgcolor="white",
        hovermode="x unified"
    )
    fig.update_yaxes(title_text="Costo unitario (Q)", secondary_y=False,
                     tickformat="Q,.0f", gridcolor="#f0f0f0")
    fig.update_yaxes(title_text="Variación anual (%)", secondary_y=True)
    return fig


@app.callback(
    Output("grafica-ratio-depto", "figure"),
    [Input("filtro-anio", "value"), Input("filtro-region", "value")]
)
def grafica_ratio_departamento(anio, region):
    df = cargar_ejecucion()
    df = df[df["anio"] == anio]
    if region != "Todas":
        df = df[df["region"] == region]

    df = df.sort_values("ratio_ei", ascending=True)

    fig = go.Figure(go.Bar(
        x=df["ratio_ei"],
        y=df["departamento"],
        orientation="h",
        marker_color=[NIVEL_COLOR.get(n, "#95A5A6") for n in df["nivel_riesgo"]],
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Ratio E/I: %{x:.2f}<br>"
            "<extra></extra>"
        )
    ))

    fig.add_vline(x=1, line_dash="solid", line_color="gray",
                  annotation_text="Punto de equilibrio")
    fig.add_vline(x=4, line_dash="dash", line_color=COLORS["warning"],
                  annotation_text="Umbral ALTO")
    fig.add_vline(x=6, line_dash="dash", line_color=COLORS["danger"],
                  annotation_text="Umbral CRÍTICO")

    fig.update_layout(
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis_title="Ratio Egresos / Ingresos",
        yaxis_title="",
        plot_bgcolor="white",
        paper_bgcolor="white",
        showlegend=False
    )
    return fig


@app.callback(
    Output("grafica-scatter-riesgo", "figure"),
    [Input("filtro-anio", "value")]
)
def grafica_scatter_riesgo(anio):
    df = cargar_ejecucion()
    df = df[df["anio"] == anio]

    fig = px.scatter(
        df,
        x="ingresos_q",
        y="egresos_q",
        color="nivel_riesgo",
        color_discrete_map=NIVEL_COLOR,
        size="brecha_q",
        size_max=30,
        hover_name="departamento",
        hover_data={"ingresos_q": ":,.0f", "egresos_q": ":,.0f", "ratio_ei": ":.2f"},
        labels={
            "ingresos_q": "Ingresos (Q)",
            "egresos_q": "Egresos (Q)",
            "nivel_riesgo": "Nivel de Riesgo"
        }
    )

    # Línea de equilibrio (egresos = ingresos)
    max_val = max(df["egresos_q"].max(), df["ingresos_q"].max())
    fig.add_trace(go.Scatter(
        x=[0, max_val], y=[0, max_val],
        mode="lines",
        line=dict(dash="dash", color="gray"),
        name="Equilibrio",
        hoverinfo="skip"
    ))

    fig.update_layout(
        margin=dict(l=0, r=0, t=10, b=0),
        plot_bgcolor="white",
        paper_bgcolor="white",
        legend=dict(orientation="h", y=-0.2, font=dict(size=10))
    )
    return fig


@app.callback(
    Output("tabla-red-flags-resumen", "children"),
    [Input("filtro-anio", "value")]
)
def tabla_red_flags(anio):
    df = cargar_red_flags()
    if df.empty:
        return html.P("No hay red flags registradas.", className="text-muted")

    resumen = df.groupby(["criticidad", "tipo_flag"]).size().reset_index(name="count")
    resumen = resumen.sort_values(["criticidad", "count"], ascending=[True, False])

    rows = []
    for _, row in resumen.iterrows():
        badge_color = "danger" if row["criticidad"] == "ALTA" else "warning"
        rows.append(html.Tr([
            html.Td(dbc.Badge(row["criticidad"], color=badge_color, className="me-1")),
            html.Td(row["tipo_flag"], style={"fontSize": "0.8rem"}),
            html.Td(dbc.Badge(str(row["count"]), color="secondary", pill=True))
        ]))

    return html.Table([
        html.Thead(html.Tr([
            html.Th("Nivel", style={"fontSize": "0.8rem"}),
            html.Th("Tipo", style={"fontSize": "0.8rem"}),
            html.Th("N°", style={"fontSize": "0.8rem"})
        ])),
        html.Tbody(rows)
    ], className="table table-sm table-hover")


@app.callback(
    Output("tabla-ejecucion", "children"),
    [Input("filtro-anio", "value"), Input("filtro-region", "value")]
)
def tabla_ejecucion(anio, region):
    df = cargar_ejecucion()
    df = df[df["anio"] == anio]
    if region != "Todas":
        df = df[df["region"] == region]

    df = df.sort_values("ratio_ei", ascending=False)

    columnas = [
        {"name": "Departamento", "id": "departamento"},
        {"name": "Región", "id": "region"},
        {"name": "Egresos (Q)", "id": "egresos_q", "type": "numeric",
         "format": {"specifier": ",.0f"}},
        {"name": "Ingresos (Q)", "id": "ingresos_q", "type": "numeric",
         "format": {"specifier": ",.0f"}},
        {"name": "Brecha (Q)", "id": "brecha_q", "type": "numeric",
         "format": {"specifier": ",.0f"}},
        {"name": "Ratio E/I", "id": "ratio_ei", "type": "numeric",
         "format": {"specifier": ".2f"}},
        {"name": "Nivel de Riesgo", "id": "nivel_riesgo"},
    ]

    return dash_table.DataTable(
        data=df.to_dict("records"),
        columns=columnas,
        style_table={"overflowX": "auto"},
        style_header={"backgroundColor": COLORS["primary"], "color": "white", "fontWeight": "bold"},
        style_cell={"fontSize": "13px", "padding": "8px"},
        style_data_conditional=[
            {"if": {"filter_query": '{nivel_riesgo} = "CRÍTICO"'},
             "backgroundColor": "#fde8e8", "color": COLORS["danger"]},
            {"if": {"filter_query": '{nivel_riesgo} = "ALTO"'},
             "backgroundColor": "#fef3e0", "color": COLORS["warning"]},
            {"if": {"filter_query": '{nivel_riesgo} = "NORMAL"'},
             "backgroundColor": "#e8f8f0"},
        ],
        page_size=22,
        sort_action="native"
    )


# ── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if not DB_PATH.exists():
        print(f"\n❌ No se encontró el Data Warehouse: {DB_PATH}")
        print("   Ejecuta primero el pipeline completo: python run_pipeline.py\n")
    else:
        print("\n🏥 Dashboard BI - Justicia en Salud Guatemala (IGSS)")
        print("   Abre tu navegador en: http://localhost:8050\n")
        app.run(debug=True, port=8050)
