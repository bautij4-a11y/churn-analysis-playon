"""
Generador de datos sintéticos - Análisis de Churn para servicio de streaming
------------------------------------------------------------------------------
Simula una base de clientes de una plataforma de streaming (ficticia: "PlayOn+")
con datos de Argentina, y su actividad mensual durante 18 meses.

Salida:
  - churn_streaming.db   (SQLite con tablas Clientes y Actividad)
  - clientes.csv
  - actividad.csv
"""

import sqlite3
import random
from datetime import date, timedelta
import numpy as np
import pandas as pd

random.seed(42)
np.random.seed(42)

# ---------------------------------------------------------------------------
# Parámetros generales
# ---------------------------------------------------------------------------
N_CLIENTES = 1200
FECHA_FIN_ANALISIS = date(2025, 12, 31)   # "hoy" ficticio para el análisis
MESES_HISTORICOS = 18                      # ventana de observación

CIUDADES = [
    "Buenos Aires", "Córdoba", "Rosario", "Mendoza", "La Plata",
    "San Miguel de Tucumán", "Mar del Plata", "Salta", "Santa Fe", "Neuquén"
]

METODOS_PAGO = {
    "Tarjeta de Crédito": 0.45,
    "Tarjeta de Débito": 0.30,
    "Mercado Pago": 0.20,
    "Transferencia Bancaria": 0.05,
}

NOMBRES = [
    "Mateo", "Sofía", "Lucas", "Valentina", "Benjamín", "Martina", "Thiago",
    "Emma", "Santiago", "Isabella", "Joaquín", "Catalina", "Bautista", "Mía",
    "Facundo", "Julieta", "Tomás", "Renata", "Agustín", "Delfina", "Nicolás",
    "Victoria", "Ignacio", "Pilar", "Franco", "Lucía", "Gael", "Antonella",
    "Dante", "Guadalupe"
]
APELLIDOS = [
    "González", "Rodríguez", "Fernández", "López", "Martínez", "Pérez",
    "Gómez", "Sánchez", "Romero", "Díaz", "Torres", "Álvarez", "Ruiz",
    "Ramírez", "Flores", "Acosta", "Benítez", "Medina", "Herrera", "Suárez"
]


def generar_clientes(n):
    filas = []
    for i in range(1, n + 1):
        nombre = f"{random.choice(NOMBRES)} {random.choice(APELLIDOS)}"
        edad = int(np.clip(np.random.normal(32, 10), 16, 75))
        ciudad = random.choice(CIUDADES)
        metodo_pago = random.choices(
            list(METODOS_PAGO.keys()), weights=list(METODOS_PAGO.values())
        )[0]

        # Fecha de alta distribuida en los últimos MESES_HISTORICOS meses
        dias_atras = random.randint(0, MESES_HISTORICOS * 30)
        fecha_alta = FECHA_FIN_ANALISIS - timedelta(days=dias_atras)
        # normalizamos al día 1 del mes de alta
        fecha_alta = fecha_alta.replace(day=1)

        filas.append({
            "ID_Cliente": i,
            "Nombre": nombre,
            "Fecha_Alta": fecha_alta.isoformat(),
            "Edad": edad,
            "Ciudad": ciudad,
            "Metodo_Pago": metodo_pago,
        })
    return pd.DataFrame(filas)


def meses_entre(f_inicio: date, f_fin: date):
    meses = []
    y, m = f_inicio.year, f_inicio.month
    while (y, m) <= (f_fin.year, f_fin.month):
        meses.append(date(y, m, 1))
        m += 1
        if m > 12:
            m = 1
            y += 1
    return meses


def generar_actividad(df_clientes):
    filas = []

    for _, cliente in df_clientes.iterrows():
        fecha_alta = date.fromisoformat(cliente["Fecha_Alta"])
        meses_posibles = meses_entre(fecha_alta, FECHA_FIN_ANALISIS)

        # Uso base del cliente (algunos clientes son "power users", otros no)
        uso_base = np.clip(np.random.normal(18, 8), 1, 45)  # horas/mes
        tendencia_decaimiento = random.random() < 0.35  # 35% de clientes con uso decreciente

        activo = True
        soporte_acumulado = 0

        for idx_mes, fecha_mes in enumerate(meses_posibles):
            if not activo:
                break

            antiguedad_meses = idx_mes  # 0 = mes de alta

            # --- Uso del servicio ---
            factor_tendencia = 1.0
            if tendencia_decaimiento and antiguedad_meses >= 1:
                factor_tendencia = max(0.15, 1 - 0.12 * antiguedad_meses)
            ruido = np.random.normal(0, 3)
            uso_horas = max(0, round(uso_base * factor_tendencia + ruido, 1))

            # --- Interacciones a soporte técnico ---
            prob_llamado = 0.12 if uso_horas > 8 else 0.28
            interacciones_soporte = np.random.poisson(prob_llamado * 3)
            soporte_acumulado += interacciones_soporte

            # --- Probabilidad de cancelar este mes ---
            prob_churn = 0.02  # base

            # Pico de cancelación al 3er mes (fin de promo)
            if antiguedad_meses == 2:
                prob_churn += 0.18

            # Uso bajo o en caída aumenta la probabilidad
            if uso_horas < 5:
                prob_churn += 0.15
            elif uso_horas < 10:
                prob_churn += 0.06

            # Muchos llamados a soporte
            if soporte_acumulado >= 3:
                prob_churn += 0.20
            elif soporte_acumulado == 2:
                prob_churn += 0.08

            # Método de pago (débito con mayor churn involuntario)
            if cliente["Metodo_Pago"] == "Tarjeta de Débito":
                prob_churn += 0.05

            prob_churn = min(prob_churn, 0.9)

            cancela_este_mes = random.random() < prob_churn
            suscripcion_activa = 0 if cancela_este_mes else 1

            filas.append({
                "ID_Cliente": cliente["ID_Cliente"],
                "Fecha_Mes": fecha_mes.isoformat(),
                "Suscripcion_Activa": suscripcion_activa,
                "Interacciones_Soporte": int(interacciones_soporte),
                "Uso_Del_Servicio": uso_horas,
            })

            if cancela_este_mes:
                activo = False

    return pd.DataFrame(filas)


def main():
    df_clientes = generar_clientes(N_CLIENTES)
    df_actividad = generar_actividad(df_clientes)

    df_clientes.to_csv("/home/claude/churn_project/data/clientes.csv", index=False)
    df_actividad.to_csv("/home/claude/churn_project/data/actividad.csv", index=False)

    conn = sqlite3.connect("/home/claude/churn_project/data/churn_streaming.db")
    df_clientes.to_sql("Clientes", conn, if_exists="replace", index=False)
    df_actividad.to_sql("Actividad", conn, if_exists="replace", index=False)
    conn.close()

    print(f"Clientes generados: {len(df_clientes)}")
    print(f"Filas de actividad generadas: {len(df_actividad)}")
    print(f"Clientes que cancelaron alguna vez: {df_actividad[df_actividad['Suscripcion_Activa']==0]['ID_Cliente'].nunique()}")


if __name__ == "__main__":
    main()
