# 📉 Optimización de la Retención de Clientes en PlayOn+

Análisis de Churn para una plataforma de streaming (datos sintéticos) — identificación
de causas raíz de la cancelación de suscripciones y propuesta de estrategias de
retención basadas en datos.

## Contexto

PlayOn+ (empresa ficticia) detectó un incremento en la pérdida de usuarios en el
último trimestre. El objetivo de este proyecto es identificar las causas raíz de esa
fuga y proponer estrategias de retención basadas en datos, utilizando SQL para el
modelado de indicadores y Python para el análisis exploratorio y la visualización.

## Tecnologías usadas

- **SQLite** — base de datos y queries analíticas
- **Python** (Pandas, Matplotlib, Seaborn) — análisis exploratorio y visualización
- **Jupyter Notebook** — desarrollo del análisis

## Estructura del repositorio

```
churn_project/
├── data/
│   ├── generate_data.py      # Generación de datos sintéticos (clientes + actividad)
│   ├── clientes.csv
│   ├── actividad.csv
│   └── churn_streaming.db    # Base SQLite con las tablas Clientes y Actividad
├── sql/
│   └── queries.sql           # Queries documentadas: tasa de churn, RFM, antigüedad,
│                              # soporte técnico y método de pago
├── analysis/
│   ├── build_notebook.py     # Script que genera el notebook
│   ├── churn_analysis.ipynb  # Notebook con el análisis completo y gráficos
│   └── *.png                 # Gráficos exportados
├── dashboard/
│   ├── build_dashboard.py    # Script que genera el dashboard interactivo
│   └── dashboard.html        # Dashboard de una página (KPIs + gráficos), autocontenido
├── linkedin_post.md          # Borrador del post de LinkedIn (Fase 5)
└── README.md
```

## Modelo de datos

**Clientes**: `ID_Cliente, Nombre, Fecha_Alta, Edad, Ciudad, Metodo_Pago`

**Actividad** (un registro por cliente y mes): `ID_Cliente, Fecha_Mes,
Suscripcion_Activa, Interacciones_Soporte, Uso_Del_Servicio`

Datos simulados: 1.200 clientes y ~6.100 registros de actividad mensual a lo largo
de 18 meses, con patrones de comportamiento realistas (caída de uso previa a la baja,
pico de cancelación al finalizar la promoción de bienvenida, mayor churn involuntario
en tarjeta de débito).

## Principales insights

- **Pico de fuga en el 3er mes de contrato (26,4% de tasa de churn)**, justo al
  finalizar la promoción de bienvenida — muy por encima del promedio general (~12%).
- **La cantidad de llamados a soporte técnico es un fuerte predictor de cancelación**:
  los clientes con más de 2 interacciones cancelan en un 77,6% de los casos, frente a
  un 54,5% de quienes nunca contactaron a soporte.
- **El método de pago con tarjeta de débito** presenta la tasa de churn más alta
  (77,5%), lo que sugiere un componente relevante de **churn involuntario** por
  rechazos de cobro, además del churn voluntario.
- El 66% de la base analizada canceló su suscripción en algún momento de la ventana
  de 18 meses observada, con una tasa de churn mensual promedio del 12,3%.

## Cómo reproducir el análisis

```bash
cd data
python generate_data.py        # genera los datos sintéticos y la base SQLite

cd ../analysis
python build_notebook.py       # (re)genera el notebook
jupyter nbconvert --to notebook --execute --inplace churn_analysis.ipynb
```

Las queries SQL documentadas también pueden ejecutarse directamente contra
`data/churn_streaming.db` con cualquier cliente SQLite.

## Dashboard

`dashboard/dashboard.html` es un dashboard interactivo de una sola página (KPIs +
evolución de churn + segmentación + disparadores de baja), armado con Plotly.
Es un archivo autocontenido: se abre directamente en el navegador, sin necesidad
de correr un servidor. Para regenerarlo:

```bash
cd dashboard
python build_dashboard.py
```

## Próximos pasos

- Diseñar el sistema de alertas tempranas propuesto (caída de uso + 2+ llamados a
  soporte) para activar campañas de retención automáticas.
- Publicar el proyecto en GitHub y compartir el post de LinkedIn (`linkedin_post.md`).
