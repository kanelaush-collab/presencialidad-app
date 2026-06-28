import streamlit as st
import pandas as pd

# --- Cargar datos ---
df = pd.read_excel("tablapresen.xlsx")
df["Fecha"] = pd.to_datetime(df["Fecha"], dayfirst=True, errors="coerce")
df["Mes"] = df["Fecha"].dt.month

# --- Título ---
st.title("📅 Presencialidad")

# --- Filtros ---
meses = {1:"Enero",2:"Febrero",3:"Marzo",4:"Abril",5:"Mayo",6:"Junio",
         7:"Julio",8:"Agosto",9:"Septiembre",10:"Octubre",11:"Noviembre",12:"Diciembre"}

mes_sel = st.selectbox("Mes", options=list(meses.keys()), format_func=lambda x: meses[x])
cr_sel = st.selectbox("Cronograma", options=df["CR"].unique())
letra_sel = st.selectbox("Letra", options=df[df["CR"] == cr_sel]["Letra"].unique())

# --- Filtrar datos ---
filtro = df[(df["Mes"] == mes_sel) & (df["CR"] == cr_sel) & (df["Letra"] == letra_sel)]

# --- Calcular días hábiles según cronograma ---
if cr_sel == "5 x 1":
    habiles = filtro[~filtro["Semana"].isin(["sábado","domingo"]) & (filtro["Valor"] != "FL")]
else:
    habiles = filtro[filtro["Valor"] == "T"]

# --- Licencias ---
st.subheader("Licencias")
col1, col2 = st.columns(2)
with col1:
    fecha_desde = st.date_input("Desde", value=None)
with col2:
    fecha_hasta = st.date_input("Hasta", value=None)

# --- Calcular métricas ---
dias_habiles = len(habiles)
presencialidad = len(habiles[habiles["Valor"] == "T"])

if fecha_desde and fecha_hasta:
    mascara_lic = (habiles["Fecha"].dt.date >= fecha_desde) & (habiles["Fecha"].dt.date <= fecha_hasta)
    licencias = int(mascara_lic.sum())
    habiles_netos = dias_habiles - licencias
else:
    licencias = 0
    habiles_netos = dias_habiles

import math
objetivo = math.ceil(dias_habiles * 0.40)
pres_neta = math.ceil(habiles_netos * 0.40)

# --- Mostrar métricas ---

c1, c2, c3, c4 = st.columns(4)
c1.metric("Días Hábiles", dias_habiles)
c2.metric("Días Hábiles Netos", habiles_netos)
c3.metric("Objetivo 40%", objetivo)
c4.metric("Presencialidad Neta", pres_neta)