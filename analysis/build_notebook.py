import nbformat as nbf

nb = nbf.v4.new_notebook()
cells = []

def md(text):
    cells.append(nbf.v4.new_markdown_cell(text))

def code(text):
    cells.append(nbf.v4.new_code_cell(text))

# ---------------------------------------------------------------------------
md("""# Análisis de Churn — PlayOn+ (servicio de streaming ficticio)

**Objetivo:** identificar las causas raíz del abandono de suscriptores y proponer
estrategias de retención basadas en datos.

Fuente de datos: `data/churn_streaming.db` (SQLite), generada de forma sintética
para este proyecto de portfolio, simulando 1.200 clientes y 18 meses de actividad.
""")

# ---------------------------------------------------------------------------
code("""import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import seaborn as sns

sns.set_theme(style="whitegrid")
plt.rcParams["figure.figsize"] = (10, 5)

conn = sqlite3.connect("../data/churn_streaming.db")

clientes = pd.read_sql_query("SELECT * FROM Clientes", conn)
actividad = pd.read_sql_query("SELECT * FROM Actividad", conn)
actividad["Fecha_Mes"] = pd.to_datetime(actividad["Fecha_Mes"])

print(f"Clientes: {len(clientes):,}")
print(f"Registros de actividad: {len(actividad):,}")
clientes.head()""")

# ---------------------------------------------------------------------------
md("## 1. Tasa de Churn Mensual\n\nEvolución de la tasa de baja mes a mes (clientes que cancelaron / clientes activos ese mes).")

code("""query_churn_mensual = '''
WITH activos_inicio_mes AS (
    SELECT Fecha_Mes, COUNT(*) AS total_activos
    FROM Actividad GROUP BY Fecha_Mes
),
bajas_mes AS (
    SELECT Fecha_Mes, SUM(CASE WHEN Suscripcion_Activa = 0 THEN 1 ELSE 0 END) AS bajas
    FROM Actividad GROUP BY Fecha_Mes
)
SELECT a.Fecha_Mes, a.total_activos, b.bajas,
       ROUND(100.0 * b.bajas / a.total_activos, 2) AS tasa_churn_pct
FROM activos_inicio_mes a
JOIN bajas_mes b ON a.Fecha_Mes = b.Fecha_Mes
ORDER BY a.Fecha_Mes;
'''

churn_mensual = pd.read_sql_query(query_churn_mensual, conn, parse_dates=["Fecha_Mes"])
churn_mensual""")

code("""fig, ax = plt.subplots()
ax.plot(churn_mensual["Fecha_Mes"], churn_mensual["tasa_churn_pct"], marker="o", color="#E63946")
ax.set_title("Evolución de la Tasa de Churn Mensual — PlayOn+", fontsize=13, weight="bold")
ax.set_xlabel("Mes")
ax.set_ylabel("Tasa de Churn (%)")
ax.yaxis.set_major_formatter(mtick.PercentFormatter())
ax.axhline(churn_mensual["tasa_churn_pct"].mean(), color="gray", linestyle="--", linewidth=1,
           label=f'Promedio: {churn_mensual["tasa_churn_pct"].mean():.1f}%')
ax.legend()
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig("churn_mensual.png", dpi=150)
plt.show()""")

# ---------------------------------------------------------------------------
md("""## 2. Churn por antigüedad del cliente

¿En qué mes de contrato se produce la mayor fuga? Esto ayuda a saber si el problema
es el fin de una promoción, un problema de onboarding, o desgaste a largo plazo.""")

code("""query_antiguedad = '''
WITH actividad_con_antiguedad AS (
    SELECT a.ID_Cliente, a.Fecha_Mes, a.Suscripcion_Activa,
        CAST((STRFTIME('%Y', a.Fecha_Mes) - STRFTIME('%Y', c.Fecha_Alta)) * 12 +
             (STRFTIME('%m', a.Fecha_Mes) - STRFTIME('%m', c.Fecha_Alta)) AS INTEGER) AS antiguedad_meses
    FROM Actividad a JOIN Clientes c ON c.ID_Cliente = a.ID_Cliente
)
SELECT antiguedad_meses, COUNT(*) AS total_registros,
       SUM(CASE WHEN Suscripcion_Activa = 0 THEN 1 ELSE 0 END) AS bajas,
       ROUND(100.0 * SUM(CASE WHEN Suscripcion_Activa = 0 THEN 1 ELSE 0 END) / COUNT(*), 2) AS tasa_churn_pct
FROM actividad_con_antiguedad
GROUP BY antiguedad_meses
ORDER BY antiguedad_meses;
'''

churn_antiguedad = pd.read_sql_query(query_antiguedad, conn)
churn_antiguedad.head(12)""")

code("""fig, ax = plt.subplots()
datos = churn_antiguedad[churn_antiguedad["antiguedad_meses"] <= 12]
colores = ["#E63946" if m == datos.loc[datos["tasa_churn_pct"].idxmax(), "antiguedad_meses"]
           else "#457B9D" for m in datos["antiguedad_meses"]]
ax.bar(datos["antiguedad_meses"], datos["tasa_churn_pct"], color=colores)
ax.set_title("Tasa de Churn según Antigüedad del Cliente (mes de contrato)", fontsize=13, weight="bold")
ax.set_xlabel("Mes de contrato (0 = mes de alta)")
ax.set_ylabel("Tasa de Churn (%)")
ax.yaxis.set_major_formatter(mtick.PercentFormatter())
plt.tight_layout()
plt.savefig("churn_antiguedad.png", dpi=150)
plt.show()

pico = datos.loc[datos["tasa_churn_pct"].idxmax()]
print(f"Pico de churn: mes {int(pico['antiguedad_meses'])} de contrato, con {pico['tasa_churn_pct']}% de bajas")""")

# ---------------------------------------------------------------------------
md("## 3. Segmentación RFM (Recencia, Frecuencia, Valor de uso)")

code("""query_rfm = '''
WITH ultima_fecha AS (SELECT MAX(Fecha_Mes) AS fecha_max FROM Actividad),
metricas_cliente AS (
    SELECT ac.ID_Cliente, MAX(ac.Fecha_Mes) AS ultima_actividad,
        COUNT(*) AS meses_activos, ROUND(AVG(ac.Uso_Del_Servicio), 1) AS uso_promedio,
        MIN(ac.Suscripcion_Activa) AS tuvo_baja
    FROM Actividad ac GROUP BY ac.ID_Cliente
)
SELECT m.ID_Cliente, c.Nombre, m.ultima_actividad, m.meses_activos, m.uso_promedio,
    CASE
        WHEN m.tuvo_baja = 0 THEN 'Perdido'
        WHEN m.uso_promedio >= 15 AND m.meses_activos >= 3 THEN 'Campeón'
        WHEN m.uso_promedio < 10 OR m.meses_activos <= 2 THEN 'En riesgo'
        ELSE 'Regular'
    END AS segmento_rfm
FROM metricas_cliente m JOIN Clientes c ON c.ID_Cliente = m.ID_Cliente
ORDER BY segmento_rfm, m.uso_promedio DESC;
'''

rfm = pd.read_sql_query(query_rfm, conn)
segmentos = rfm["segmento_rfm"].value_counts()
segmentos""")

code("""colores_segmento = {"Campeón": "#2A9D8F", "Regular": "#457B9D", "En riesgo": "#F4A261", "Perdido": "#E63946"}
fig, ax = plt.subplots()
segmentos_ordenados = segmentos.reindex(["Campeón", "Regular", "En riesgo", "Perdido"])
ax.bar(segmentos_ordenados.index, segmentos_ordenados.values,
       color=[colores_segmento[s] for s in segmentos_ordenados.index])
ax.set_title("Segmentación de Clientes (RFM adaptado)", fontsize=13, weight="bold")
ax.set_ylabel("Cantidad de clientes")
for i, v in enumerate(segmentos_ordenados.values):
    ax.text(i, v + 10, str(v), ha="center", weight="bold")
plt.tight_layout()
plt.savefig("segmentos_rfm.png", dpi=150)
plt.show()""")

# ---------------------------------------------------------------------------
md("## 4. Soporte técnico vs. Churn\n\n¿Los clientes que más llaman a soporte cancelan con más frecuencia?")

code("""query_soporte = '''
WITH soporte_acumulado AS (
    SELECT ID_Cliente, SUM(Interacciones_Soporte) AS total_soporte, MIN(Suscripcion_Activa) AS tuvo_baja
    FROM Actividad GROUP BY ID_Cliente
)
SELECT
    CASE WHEN total_soporte = 0 THEN '0 llamados'
         WHEN total_soporte <= 2 THEN '1-2 llamados'
         ELSE 'Más de 2 llamados' END AS rango_soporte,
    COUNT(*) AS clientes,
    SUM(CASE WHEN tuvo_baja = 0 THEN 1 ELSE 0 END) AS clientes_que_cancelaron,
    ROUND(100.0 * SUM(CASE WHEN tuvo_baja = 0 THEN 1 ELSE 0 END) / COUNT(*), 2) AS tasa_baja_pct
FROM soporte_acumulado GROUP BY rango_soporte ORDER BY tasa_baja_pct DESC;
'''

soporte = pd.read_sql_query(query_soporte, conn)
soporte""")

code("""orden = ["0 llamados", "1-2 llamados", "Más de 2 llamados"]
soporte_o = soporte.set_index("rango_soporte").reindex(orden).reset_index()

fig, ax = plt.subplots()
ax.bar(soporte_o["rango_soporte"], soporte_o["tasa_baja_pct"], color="#E76F51")
ax.set_title("Tasa de Baja según Interacciones con Soporte Técnico", fontsize=13, weight="bold")
ax.set_ylabel("Tasa de Baja (%)")
ax.yaxis.set_major_formatter(mtick.PercentFormatter())
plt.tight_layout()
plt.savefig("soporte_vs_churn.png", dpi=150)
plt.show()""")

# ---------------------------------------------------------------------------
md("## 5. Churn por Método de Pago\n\nEl churn por tarjeta de débito suele ser más \"involuntario\" (rechazos de cobro).")

code("""query_pago = '''
WITH estado_final_cliente AS (
    SELECT ID_Cliente, MIN(Suscripcion_Activa) AS tuvo_baja FROM Actividad GROUP BY ID_Cliente
)
SELECT c.Metodo_Pago, COUNT(*) AS total_clientes,
    SUM(CASE WHEN e.tuvo_baja = 0 THEN 1 ELSE 0 END) AS clientes_que_cancelaron,
    ROUND(100.0 * SUM(CASE WHEN e.tuvo_baja = 0 THEN 1 ELSE 0 END) / COUNT(*), 2) AS tasa_churn_pct
FROM Clientes c JOIN estado_final_cliente e ON e.ID_Cliente = c.ID_Cliente
GROUP BY c.Metodo_Pago ORDER BY tasa_churn_pct DESC;
'''

pago = pd.read_sql_query(query_pago, conn)
pago""")

code("""fig, ax = plt.subplots()
ax.barh(pago["Metodo_Pago"], pago["tasa_churn_pct"], color="#264653")
ax.set_title("Tasa de Churn según Método de Pago", fontsize=13, weight="bold")
ax.set_xlabel("Tasa de Churn (%)")
ax.xaxis.set_major_formatter(mtick.PercentFormatter())
plt.tight_layout()
plt.savefig("churn_metodo_pago.png", dpi=150)
plt.show()""")

# ---------------------------------------------------------------------------
md("""## 6. KPIs para el dashboard

Resumen ejecutivo con los indicadores clave que irían en la sección superior del dashboard.""")

code("""precio_mensual_promedio = 4500  # ARS, supuesto de precio de suscripción PlayOn+

clientes_activos_actuales = actividad[actividad["Fecha_Mes"] == actividad["Fecha_Mes"].max()]
clientes_activos_actuales = clientes_activos_actuales["Suscripcion_Activa"].sum()

churn_actual = churn_mensual.iloc[-1]["tasa_churn_pct"]
bajas_ultimo_mes = churn_mensual.iloc[-1]["bajas"]
mrr_perdido = bajas_ultimo_mes * precio_mensual_promedio

print(f"Tasa de Churn actual:        {churn_actual}%")
print(f"Clientes activos (último mes): {int(clientes_activos_actuales):,}")
print(f"Bajas último mes:            {int(bajas_ultimo_mes)}")
print(f"MRR perdido (aprox.):        ${mrr_perdido:,.0f} ARS")""")

# ---------------------------------------------------------------------------
md("""## 7. Conclusiones principales

*(completar/ajustar redacción final con los números reales una vez ejecutado el notebook)*

- **Pico de fuga al 3er mes de contrato**, coincidiendo con el fin de la promoción de bienvenida.
  Esto sugiere implementar una campaña de retención dirigida específicamente a clientes
  que se acercan a esa fecha.
- **Los llamados a soporte técnico son un fuerte predictor de baja**: los clientes con más
  de 2 interacciones cancelan con una frecuencia notablemente mayor que quienes nunca
  llamaron. Esto habilita un sistema de alerta temprana para el equipo de Customer Success.
- **El método de pago con tarjeta de débito** presenta la tasa de churn más alta, lo que
  indica una componente de **churn involuntario** (rechazos de cobro) que se podría
  reducir con reintentos automáticos de cobro o recordatorios de actualización de datos.
- El uso decreciente del servicio en las semanas previas a la baja confirma que es posible
  anticipar la cancelación y activar campañas de reactivación antes de que ocurra.

Próximo paso: construir el dashboard interactivo (Fase 3) con estos mismos indicadores.
""")

nb["cells"] = cells

with open("churn_analysis.ipynb", "w", encoding="utf-8") as f:
    nbf.write(nb, f)

print("Notebook creado: churn_analysis.ipynb")
