-- =============================================================================
-- Proyecto: Optimización de la Retención de Clientes en "PlayOn+"
-- Base de datos: churn_streaming.db (SQLite)
-- Tablas: Clientes(ID_Cliente, Nombre, Fecha_Alta, Edad, Ciudad, Metodo_Pago)
--         Actividad(ID_Cliente, Fecha_Mes, Suscripcion_Activa,
--                    Interacciones_Soporte, Uso_Del_Servicio)
-- =============================================================================


-- -----------------------------------------------------------------------------
-- 1) TASA DE CHURN MENSUAL
-- Tasa de Churn = (clientes que cancelaron en el mes / clientes activos al
-- inicio del mes) * 100
-- -----------------------------------------------------------------------------
WITH activos_inicio_mes AS (
    SELECT
        Fecha_Mes,
        COUNT(*) AS total_activos
    FROM Actividad
    GROUP BY Fecha_Mes
),
bajas_mes AS (
    SELECT
        Fecha_Mes,
        SUM(CASE WHEN Suscripcion_Activa = 0 THEN 1 ELSE 0 END) AS bajas
    FROM Actividad
    GROUP BY Fecha_Mes
)
SELECT
    a.Fecha_Mes,
    a.total_activos,
    b.bajas,
    ROUND(100.0 * b.bajas / a.total_activos, 2) AS tasa_churn_pct
FROM activos_inicio_mes a
JOIN bajas_mes b ON a.Fecha_Mes = b.Fecha_Mes
ORDER BY a.Fecha_Mes;


-- -----------------------------------------------------------------------------
-- 2) SEGMENTACIÓN RFM (Recencia, Frecuencia, Valor de uso)
-- Adaptada a un negocio de suscripción sin "monto de compra" transaccional:
--   Recencia   -> hace cuántos meses fue el último registro de actividad
--   Frecuencia -> cantidad de meses activos históricos (permanencia)
--   Valor      -> promedio de horas de uso del servicio
-- Clasificación:
--   Campeones : uso alto y activos recientemente
--   En riesgo : eran clientes frecuentes pero bajó su uso o no hay actividad
--               reciente
--   Perdidos  : dieron de baja la suscripción
-- -----------------------------------------------------------------------------
WITH ultima_fecha AS (
    SELECT MAX(Fecha_Mes) AS fecha_max FROM Actividad
),
metricas_cliente AS (
    SELECT
        ac.ID_Cliente,
        MAX(ac.Fecha_Mes) AS ultima_actividad,
        COUNT(*) AS meses_activos,
        ROUND(AVG(ac.Uso_Del_Servicio), 1) AS uso_promedio,
        MAX(CASE WHEN ac.Fecha_Mes = (SELECT fecha_max FROM ultima_fecha)
                 THEN ac.Suscripcion_Activa END) AS activo_ultimo_mes,
        MIN(ac.Suscripcion_Activa) AS tuvo_baja  -- 0 si en algún momento canceló
    FROM Actividad ac
    GROUP BY ac.ID_Cliente
)
SELECT
    m.ID_Cliente,
    c.Nombre,
    m.ultima_actividad,
    m.meses_activos,
    m.uso_promedio,
    CASE
        WHEN m.tuvo_baja = 0 THEN 'Perdido'
        WHEN m.uso_promedio >= 15 AND m.meses_activos >= 3 THEN 'Campeón'
        WHEN m.uso_promedio < 10 OR m.meses_activos <= 2 THEN 'En riesgo'
        ELSE 'Regular'
    END AS segmento_rfm
FROM metricas_cliente m
JOIN Clientes c ON c.ID_Cliente = m.ID_Cliente
ORDER BY segmento_rfm, m.uso_promedio DESC;


-- -----------------------------------------------------------------------------
-- 3) CHURN POR ANTIGÜEDAD (mes de contrato en el que se produce la baja)
-- Permite ver si la fuga ocurre al terminar una promo (mes 3) o al año.
-- -----------------------------------------------------------------------------
WITH actividad_con_antiguedad AS (
    SELECT
        a.ID_Cliente,
        a.Fecha_Mes,
        a.Suscripcion_Activa,
        CAST(
            (STRFTIME('%Y', a.Fecha_Mes) - STRFTIME('%Y', c.Fecha_Alta)) * 12 +
            (STRFTIME('%m', a.Fecha_Mes) - STRFTIME('%m', c.Fecha_Alta))
        AS INTEGER) AS antiguedad_meses
    FROM Actividad a
    JOIN Clientes c ON c.ID_Cliente = a.ID_Cliente
)
SELECT
    antiguedad_meses,
    COUNT(*) AS total_registros,
    SUM(CASE WHEN Suscripcion_Activa = 0 THEN 1 ELSE 0 END) AS bajas,
    ROUND(100.0 * SUM(CASE WHEN Suscripcion_Activa = 0 THEN 1 ELSE 0 END) / COUNT(*), 2) AS tasa_churn_pct
FROM actividad_con_antiguedad
GROUP BY antiguedad_meses
ORDER BY antiguedad_meses;


-- -----------------------------------------------------------------------------
-- 4) SOPORTE TÉCNICO VS. BAJA (¿más de 2 llamados aumenta el churn?)
-- -----------------------------------------------------------------------------
WITH soporte_acumulado AS (
    SELECT
        ID_Cliente,
        SUM(Interacciones_Soporte) AS total_soporte,
        MIN(Suscripcion_Activa) AS tuvo_baja
    FROM Actividad
    GROUP BY ID_Cliente
)
SELECT
    CASE
        WHEN total_soporte = 0 THEN '0 llamados'
        WHEN total_soporte <= 2 THEN '1-2 llamados'
        ELSE 'Más de 2 llamados'
    END AS rango_soporte,
    COUNT(*) AS clientes,
    SUM(CASE WHEN tuvo_baja = 0 THEN 1 ELSE 0 END) AS clientes_que_cancelaron,
    ROUND(100.0 * SUM(CASE WHEN tuvo_baja = 0 THEN 1 ELSE 0 END) / COUNT(*), 2) AS tasa_baja_pct
FROM soporte_acumulado
GROUP BY rango_soporte
ORDER BY tasa_baja_pct DESC;


-- -----------------------------------------------------------------------------
-- 5) CHURN POR MÉTODO DE PAGO (posible churn involuntario en débito)
-- -----------------------------------------------------------------------------
WITH estado_final_cliente AS (
    SELECT
        ID_Cliente,
        MIN(Suscripcion_Activa) AS tuvo_baja
    FROM Actividad
    GROUP BY ID_Cliente
)
SELECT
    c.Metodo_Pago,
    COUNT(*) AS total_clientes,
    SUM(CASE WHEN e.tuvo_baja = 0 THEN 1 ELSE 0 END) AS clientes_que_cancelaron,
    ROUND(100.0 * SUM(CASE WHEN e.tuvo_baja = 0 THEN 1 ELSE 0 END) / COUNT(*), 2) AS tasa_churn_pct
FROM Clientes c
JOIN estado_final_cliente e ON e.ID_Cliente = c.ID_Cliente
GROUP BY c.Metodo_Pago
ORDER BY tasa_churn_pct DESC;
