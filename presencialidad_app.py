import streamlit as st
import pandas as pd
import math
import gspread
from google.oauth2.service_account import Credentials
import calendar

# --- Conectar con Google Sheets ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(st.secrets["gcp_service_account"]["SHEET_ID"]).sheet1

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

# --- Calendario de asistencia ---
st.subheader("📝 Registrar asistencia")
nombre = st.text_input("Tu nombre")

# Obtener días hábiles del mes como lista de fechas
dias_habiles_lista = habiles["Fecha"].dt.date.tolist()

# Construir calendario
st.write("Seleccioná los días que fuiste presencial:")
cal = calendar.monthcalendar(2026, mes_sel)
dias_seleccionados = []

dias_semana = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
cols_header = st.columns(7)
for i, dia in enumerate(dias_semana):
    cols_header[i].markdown(f"**{dia}**")

for semana in cal:
    cols = st.columns(7)
    for i, dia in enumerate(semana):
        if dia == 0:
            cols[i].write("")
        else:
            from datetime import date
            fecha = date(2026, mes_sel, dia)
            if fecha in dias_habiles_lista:
                key = f"dia_{dia}"
                if cols[i].checkbox(str(dia), key=key):
                    dias_seleccionados.append(fecha)
            else:
                cols[i].markdown(f"~~{dia}~~")

if st.button("Guardar registro"):
    if nombre and dias_seleccionados:
        for fecha in dias_seleccionados:
            nueva_fila = [nombre, cr_sel, letra_sel, meses[mes_sel], 2026, str(fecha), dias_habiles, objetivo]
            sheet.append_row(nueva_fila)
        st.success(f"✅ Se registraron {len(dias_seleccionados)} días para {nombre}!")
    elif not nombre:
        st.warning("Por favor ingresá tu nombre.")
    else:
        st.warning("Seleccioná al menos un día.")
