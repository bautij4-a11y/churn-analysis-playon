¿Cómo detectar quién está por cancelar antes de que lo haga? 📉💡

Recientemente terminé un proyecto de Churn Analysis para una plataforma de
streaming, analizando 1.200 clientes y más de 6.000 registros mensuales de
actividad con SQL y Python.

Algunos hallazgos:

📌 El 26% de las bajas se concentra en el 3er mes de contrato, justo cuando
termina la promoción de bienvenida — más del doble del churn promedio (12%).

📌 Los clientes que llamaron más de 2 veces a soporte técnico cancelaron en
el 78% de los casos, contra un 55% de quienes nunca tuvieron que llamar.

📌 El método de pago también importa: los usuarios con tarjeta de débito
muestran la tasa de baja más alta, lo que sugiere que buena parte del churn
es "involuntario" (cobros rechazados) y no solo una decisión del cliente.

¿La propuesta? Un sistema de alertas tempranas que cruce caída de uso +
llamados a soporte para que el equipo de retención actúe antes del mes 3,
en vez de después.

Dejo el link al repositorio con las queries SQL documentadas y el notebook
completo de análisis 👇 ¡Todo el feedback es bienvenido!

#DataAnalytics #SQL #Python #DataPortfolio #ChurnAnalysis
