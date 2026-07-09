"""
Dashboard interactivo de Churn — PlayOn+
Genera un único archivo HTML (dashboard.html) con:
  - KPIs superiores
  - Evolución de churn mensual + churn por segmento (RFM)
  - Correlación: soporte técnico vs. % de baja, y método de pago vs. % de baja
"""

import sqlite3
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio

conn = sqlite3.connect("../data/churn_streaming.db")
clientes = pd.read_sql_query("SELECT * FROM Clientes", conn)
actividad = pd.read_sql_query("SELECT * FROM Actividad", conn, parse_dates=["Fecha_Mes"])

PRECIO_MENSUAL = 4500  # ARS supuesto

# ---------------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------------
ultimo_mes = actividad["Fecha_Mes"].max()
df_ultimo_mes = actividad[actividad["Fecha_Mes"] == ultimo_mes]

clientes_activos = int(df_ultimo_mes["Suscripcion_Activa"].sum())
bajas_ultimo_mes = int((df_ultimo_mes["Suscripcion_Activa"] == 0).sum())
tasa_churn_actual = round(100 * bajas_ultimo_mes / len(df_ultimo_mes), 1)
mrr_perdido = bajas_ultimo_mes * PRECIO_MENSUAL

MESES_ES = ["enero","febrero","marzo","abril","mayo","junio","julio",
            "agosto","septiembre","octubre","noviembre","diciembre"]
mes_referencia = f"{MESES_ES[ultimo_mes.month - 1]} {ultimo_mes.year}"

# ---------------------------------------------------------------------------
# Query 1: churn mensual
# ---------------------------------------------------------------------------
q_churn_mensual = """
WITH activos_inicio_mes AS (
    SELECT Fecha_Mes, COUNT(*) AS total_activos FROM Actividad GROUP BY Fecha_Mes
),
bajas_mes AS (
    SELECT Fecha_Mes, SUM(CASE WHEN Suscripcion_Activa = 0 THEN 1 ELSE 0 END) AS bajas
    FROM Actividad GROUP BY Fecha_Mes
)
SELECT a.Fecha_Mes, a.total_activos, b.bajas,
       ROUND(100.0 * b.bajas / a.total_activos, 2) AS tasa_churn_pct
FROM activos_inicio_mes a JOIN bajas_mes b ON a.Fecha_Mes = b.Fecha_Mes
ORDER BY a.Fecha_Mes;
"""
churn_mensual = pd.read_sql_query(q_churn_mensual, conn, parse_dates=["Fecha_Mes"])

# ---------------------------------------------------------------------------
# Query 2: segmentación RFM
# ---------------------------------------------------------------------------
q_rfm = """
WITH metricas_cliente AS (
    SELECT ac.ID_Cliente, COUNT(*) AS meses_activos,
        ROUND(AVG(ac.Uso_Del_Servicio), 1) AS uso_promedio,
        MIN(ac.Suscripcion_Activa) AS tuvo_baja
    FROM Actividad ac GROUP BY ac.ID_Cliente
)
SELECT ID_Cliente,
    CASE
        WHEN tuvo_baja = 0 THEN 'Perdido'
        WHEN uso_promedio >= 15 AND meses_activos >= 3 THEN 'Campeón'
        WHEN uso_promedio < 10 OR meses_activos <= 2 THEN 'En riesgo'
        ELSE 'Regular'
    END AS segmento_rfm
FROM metricas_cliente;
"""
rfm = pd.read_sql_query(q_rfm, conn)
segmentos = rfm["segmento_rfm"].value_counts().reindex(
    ["Campeón", "Regular", "En riesgo", "Perdido"]
)

# ---------------------------------------------------------------------------
# Query 3: soporte técnico vs. churn
# ---------------------------------------------------------------------------
q_soporte = """
WITH soporte_acumulado AS (
    SELECT ID_Cliente, SUM(Interacciones_Soporte) AS total_soporte, MIN(Suscripcion_Activa) AS tuvo_baja
    FROM Actividad GROUP BY ID_Cliente
)
SELECT
    CASE WHEN total_soporte = 0 THEN '0 llamados'
         WHEN total_soporte <= 2 THEN '1-2 llamados'
         ELSE 'Más de 2 llamados' END AS rango_soporte,
    ROUND(100.0 * SUM(CASE WHEN tuvo_baja = 0 THEN 1 ELSE 0 END) / COUNT(*), 2) AS tasa_baja_pct
FROM soporte_acumulado GROUP BY rango_soporte;
"""
soporte = pd.read_sql_query(q_soporte, conn)
orden_soporte = ["0 llamados", "1-2 llamados", "Más de 2 llamados"]
soporte = soporte.set_index("rango_soporte").reindex(orden_soporte).reset_index()

# ---------------------------------------------------------------------------
# Query 4: churn por método de pago
# ---------------------------------------------------------------------------
q_pago = """
WITH estado_final AS (
    SELECT ID_Cliente, MIN(Suscripcion_Activa) AS tuvo_baja FROM Actividad GROUP BY ID_Cliente
)
SELECT c.Metodo_Pago,
    ROUND(100.0 * SUM(CASE WHEN e.tuvo_baja = 0 THEN 1 ELSE 0 END) / COUNT(*), 2) AS tasa_churn_pct
FROM Clientes c JOIN estado_final e ON e.ID_Cliente = c.ID_Cliente
GROUP BY c.Metodo_Pago ORDER BY tasa_churn_pct DESC;
"""
pago = pd.read_sql_query(q_pago, conn)

conn.close()

# ---------------------------------------------------------------------------
# Paleta
# ---------------------------------------------------------------------------
COLOR_ROJO = "#E63946"
COLOR_AZUL = "#457B9D"
COLOR_AZUL_OSCURO = "#1D3557"
COLOR_VERDE = "#2A9D8F"
COLOR_NARANJA = "#F4A261"
COLOR_GRIS = "#8D99AE"

COLORES_SEGMENTO = {"Campeón": COLOR_VERDE, "Regular": COLOR_AZUL,
                     "En riesgo": COLOR_NARANJA, "Perdido": COLOR_ROJO}

# ---------------------------------------------------------------------------
# Gráfico 1: evolución del churn mensual (línea)
# ---------------------------------------------------------------------------
fig_evolucion = go.Figure()
fig_evolucion.add_trace(go.Scatter(
    x=churn_mensual["Fecha_Mes"], y=churn_mensual["tasa_churn_pct"],
    mode="lines+markers", line=dict(color=COLOR_ROJO, width=3),
    marker=dict(size=7),
    hovertemplate="%{x|%b %Y}<br>Churn: %{y}%<extra></extra>",
))
fig_evolucion.add_hline(
    y=churn_mensual["tasa_churn_pct"].mean(), line_dash="dash", line_color=COLOR_GRIS,
    annotation_text=f"Promedio {churn_mensual['tasa_churn_pct'].mean():.1f}%",
    annotation_position="top left",
)
fig_evolucion.update_layout(
    title="Evolución de la Tasa de Churn Mensual",
    yaxis_title="Tasa de Churn (%)", xaxis_title=None,
    margin=dict(t=50, l=40, r=20, b=30), height=340,
)

# ---------------------------------------------------------------------------
# Gráfico 2: segmentación RFM (barras)
# ---------------------------------------------------------------------------
fig_segmentos = go.Figure(go.Bar(
    x=segmentos.index, y=segmentos.values,
    marker_color=[COLORES_SEGMENTO[s] for s in segmentos.index],
    text=segmentos.values, textposition="outside",
    hovertemplate="%{x}: %{y} clientes<extra></extra>",
))
fig_segmentos.update_layout(
    title="Segmentación de Clientes (RFM)",
    yaxis_title="Cantidad de clientes",
    margin=dict(t=50, l=40, r=20, b=30), height=340,
)

# ---------------------------------------------------------------------------
# Gráfico 3: soporte técnico vs. % de baja
# ---------------------------------------------------------------------------
fig_soporte = go.Figure(go.Bar(
    x=soporte["rango_soporte"], y=soporte["tasa_baja_pct"],
    marker_color=COLOR_NARANJA,
    text=[f"{v}%" for v in soporte["tasa_baja_pct"]], textposition="outside",
    hovertemplate="%{x}<br>%{y}%% de baja<extra></extra>",
))
fig_soporte.update_layout(
    title="Tasa de Baja según Llamados a Soporte",
    yaxis_title="Tasa de Baja (%)",
    margin=dict(t=50, l=40, r=20, b=30), height=320,
)

# ---------------------------------------------------------------------------
# Gráfico 4: churn por método de pago
# ---------------------------------------------------------------------------
fig_pago = go.Figure(go.Bar(
    x=pago["tasa_churn_pct"], y=pago["Metodo_Pago"], orientation="h",
    marker_color=COLOR_AZUL_OSCURO,
    text=[f"{v}%" for v in pago["tasa_churn_pct"]], textposition="outside",
    hovertemplate="%{y}<br>%{x}%% de churn<extra></extra>",
))
fig_pago.update_layout(
    title="Tasa de Churn según Método de Pago",
    xaxis_title="Tasa de Churn (%)",
    margin=dict(t=50, l=40, r=20, b=30), height=320,
)

# ---------------------------------------------------------------------------
# Ensamblado del HTML
# ---------------------------------------------------------------------------
config = {"displayModeBar": False, "responsive": True}

html_evolucion = pio.to_html(fig_evolucion, include_plotlyjs="cdn", full_html=False, config=config)
html_segmentos = pio.to_html(fig_segmentos, include_plotlyjs=False, full_html=False, config=config)
html_soporte = pio.to_html(fig_soporte, include_plotlyjs=False, full_html=False, config=config)
html_pago = pio.to_html(fig_pago, include_plotlyjs=False, full_html=False, config=config)

html = f"""
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Dashboard de Churn — PlayOn+</title>
<style>
  body {{
    font-family: 'Segoe UI', Arial, sans-serif;
    background: #F1FAEE;
    margin: 0;
    padding: 24px 40px 60px 40px;
    color: {COLOR_AZUL_OSCURO};
  }}
  h1 {{
    font-size: 26px;
    margin-bottom: 4px;
  }}
  .subtitulo {{
    color: {COLOR_GRIS};
    margin-bottom: 24px;
    font-size: 14px;
  }}
  .kpis {{
    display: flex;
    gap: 20px;
    margin-bottom: 28px;
    flex-wrap: wrap;
  }}
  .kpi-card {{
    background: white;
    border-radius: 12px;
    padding: 18px 26px;
    box-shadow: 0 2px 8px rgba(29,53,87,0.08);
    flex: 1;
    min-width: 200px;
    border-left: 5px solid {COLOR_ROJO};
  }}
  .kpi-card:nth-child(2) {{ border-left-color: {COLOR_AZUL}; }}
  .kpi-card:nth-child(3) {{ border-left-color: {COLOR_NARANJA}; }}
  .kpi-label {{
    font-size: 13px;
    color: {COLOR_GRIS};
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }}
  .kpi-value {{
    font-size: 30px;
    font-weight: 700;
    margin-top: 4px;
  }}
  .grid-central {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    margin-bottom: 20px;
  }}
  .grid-inferior {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
  }}
  .chart-card {{
    background: white;
    border-radius: 12px;
    padding: 10px 16px;
    box-shadow: 0 2px 8px rgba(29,53,87,0.08);
  }}
  @media (max-width: 900px) {{
    .grid-central, .grid-inferior {{ grid-template-columns: 1fr; }}
  }}
</style>
</head>
<body>

  <h1>📉 Dashboard de Retención — PlayOn+</h1>
  <div class="subtitulo">Datos al cierre de {mes_referencia} · Fuente: churn_streaming.db</div>

  <div class="kpis">
    <div class="kpi-card">
      <div class="kpi-label">Tasa de Churn Actual</div>
      <div class="kpi-value">{tasa_churn_actual}%</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Clientes Activos</div>
      <div class="kpi-value">{clientes_activos:,}</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">MRR Perdido (último mes)</div>
      <div class="kpi-value">${mrr_perdido:,.0f}</div>
    </div>
  </div>

  <div class="grid-central">
    <div class="chart-card">{html_evolucion}</div>
    <div class="chart-card">{html_segmentos}</div>
  </div>

  <div class="grid-inferior">
    <div class="chart-card">{html_soporte}</div>
    <div class="chart-card">{html_pago}</div>
  </div>

</body>
</html>
"""

with open("dashboard.html", "w", encoding="utf-8") as f:
    f.write(html)

print("Dashboard generado: dashboard.html")
print(f"KPIs -> Churn actual: {tasa_churn_actual}% | Activos: {clientes_activos} | MRR perdido: ${mrr_perdido:,.0f}")
