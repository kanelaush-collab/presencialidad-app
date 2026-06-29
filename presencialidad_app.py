import streamlit as st
import pandas as pd
import math
import gspread
from google.oauth2.service_account import Credentials

# --- Conectar con Google Sheets ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(st.secrets["SHEET_ID"]).sheet1

# --- Cargar datos Excel ---
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

# --- Calcular días hábiles ---
if cr_sel == "5 x 1":
    habiles = filtro[~filtro["Semana"].isin(["sábado","domingo"]) & ~filtro["Valor"].isin(["FL", "F"])]
else:
    habiles = filtro[filtro["Valor"] == "T"]

# --- Licencias ---
st.subheader("Licencias")
col1, col2 = st.columns(2)
with col1:
    fecha_desde = st.date_input("Desde", value=None)
with col2:
    fecha_hasta = st.date_input("Hasta", value=None)

if fecha_desde and fecha_hasta:
    mascara_lic = (habiles["Fecha"].dt.date >= fecha_desde) & (habiles["Fecha"].dt.date <= fecha_hasta)
    licencias = int(mascara_lic.sum())
    habiles_netos = len(habiles) - licencias
else:
    licencias = 0
    habiles_netos = len(habiles)

dias_habiles = len(habiles)
objetivo = math.ceil(dias_habiles * 0.40)
pres_neta = math.ceil(habiles_netos * 0.40)

# --- Resultados ---
st.subheader("Resultados")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Días Hábiles", dias_habiles)
c2.metric("Días Hábiles Netos", habiles_netos)
c3.metric("Objetivo 40%", objetivo)
c4.metric("Presencialidad Neta", pres_neta)

# --- Registro ---
st.subheader("📝 Registrar asistencia")
nombre = st.text_input("Tu nombre")
dias_presentes = st.number_input("Días que fuiste presencial este mes", min_value=0, max_value=dias_habiles, step=1)

if st.button("Guardar registro"):
    if nombre:
        nueva_fila = [nombre, cr_sel, letra_sel, meses[mes_sel], 2026, int(dias_presentes), dias_habiles, objetivo]
        sheet.append_row(nueva_fila)
        st.success(f"✅ Registro guardado para {nombre}!")
    else:
        st.warning("Por favor ingresá tu nombre.")
