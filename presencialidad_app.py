import streamlit as st
import pandas as pd
import math
import gspread
from google.oauth2.service_account import Credentials
import calendar
from datetime import date

# --- Conectar con Google Sheets ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
client = gspread.authorize(creds)
spreadsheet = client.open_by_key(st.secrets["gcp_service_account"]["SHEET_ID"])
sheet_registro = spreadsheet.sheet1
sheet_usuarios = spreadsheet.worksheet("Hoja 2")

# --- Supervisores ---
SUPERVISORES = ["MARTIN, IGNACIO", "SALOMON, NICOLAS", "CHAMBERS, SOLEDAD", "CIRCELLI, MARTIN", "AYALA, CRISTIAN DANIEL"]
CODIGO_SUPER = "SUPER123"

# --- Cargar datos Excel ---
df = pd.read_excel("tablapresen.xlsx")
df["Fecha"] = pd.to_datetime(df["Fecha"], dayfirst=True, errors="coerce")
df["Mes"] = df["Fecha"].dt.month

# --- Título ---
st.title("📅 Presencialidad")

# --- SESSION STATE ---
if "usuario" not in st.session_state:
    st.session_state.usuario = None
if "es_supervisor" not in st.session_state:
    st.session_state.es_supervisor = False

# --- LOGIN ---
if st.session_state.usuario is None:
    st.subheader("🔐 Iniciar sesión")
    codigo = st.text_input("Código de acceso (supervisores) o dejá vacío", type="password")

    if codigo == CODIGO_SUPER:
        sup_sel = st.selectbox("Seleccioná tu nombre", SUPERVISORES)
        if st.button("Ingresar como supervisor"):
            st.session_state.es_supervisor = True
            st.session_state.usuario = sup_sel
            st.rerun()
    else:
        nombre = st.text_input("Tu nombre completo")
        dni = st.text_input("Tu DNI")

        if nombre and dni:
            usuarios = sheet_usuarios.get_all_records()
            usuario_existe = any(str(u["DNI"]) == str(dni) for u in usuarios)

            if usuario_existe:
                if st.button("Ingresar"):
                    usuario_data = next(u for u in usuarios if str(u["DNI"]) == str(dni))
                    st.session_state.usuario = usuario_data["Nombre"]
                    st.session_state.supervisor_sel = usuario_data["Supervisor"]
                    st.rerun()
            else:
                sup_sel = st.selectbox("Seleccioná tu supervisor", SUPERVISORES)
                if st.button("Registrarme e ingresar"):
                    sheet_usuarios.append_row([nombre, dni, sup_sel])
                    st.session_state.usuario = nombre
                    st.session_state.supervisor_sel = sup_sel
                    st.rerun()

# --- APP PRINCIPAL ---
else:
    st.write(f"👤 {st.session_state.usuario}")
    if st.button("Cerrar sesión"):
        st.session_state.usuario = None
        st.session_state.es_supervisor = False
        st.rerun()

    meses = {1:"Enero",2:"Febrero",3:"Marzo",4:"Abril",5:"Mayo",6:"Junio",
             7:"Julio",8:"Agosto",9:"Septiembre",10:"Octubre",11:"Noviembre",12:"Diciembre"}

    # --- VISTA SUPERVISOR ---
    if st.session_state.es_supervisor:
        st.subheader("👥 Panel del supervisor")
        mes_sel = st.selectbox("Mes", options=list(meses.keys()), format_func=lambda x: meses[x])

        registros = sheet_registro.get_all_records()
        df_reg = pd.DataFrame(registros) if registros else pd.DataFrame()
        usuarios = sheet_usuarios.get_all_records()
        df_usr = pd.DataFrame(usuarios) if usuarios else pd.DataFrame()

        if not df_reg.empty and not df_usr.empty:
            empleados_sup = df_usr[df_usr["Supervisor"] == st.session_state.usuario]["Nombre"].tolist()
            df_mes = df_reg[(df_reg["Mes"] == meses[mes_sel]) & (df_reg["Nombre"].isin(empleados_sup))]

            if not df_mes.empty:
                resumen = df_mes.groupby("Nombre").agg(
                    Dias_Presentes=("Dias_Presentes", "count"),
                    Objetivo=("Objetivo_40", "first")
                ).reset_index()
                resumen["Cumple"] = resumen["Dias_Presentes"] >= resumen["Objetivo"]
                resumen["Cumple"] = resumen["Cumple"].map({True: "✅", False: "❌"})
                st.dataframe(resumen)
            else:
                st.info("No hay registros para este mes.")
        else:
            st.info("No hay datos aún.")

    # --- VISTA EMPLEADO ---
    else:
        st.subheader("📋 Mi presencialidad")
        mes_sel = st.selectbox("Mes", options=list(meses.keys()), format_func=lambda x: meses[x])
        cr_sel = st.selectbox("Cronograma", options=df["CR"].unique())
        letra_sel = st.selectbox("Letra", options=df[df["CR"] == cr_sel]["Letra"].unique())

        filtro = df[(df["Mes"] == mes_sel) & (df["CR"] == cr_sel) & (df["Letra"] == letra_sel)]

        if cr_sel == "5 x 1":
            habiles = filtro[~filtro["Semana"].isin(["sábado","domingo"]) & ~filtro["Valor"].isin(["FL", "F"])]
        else:
            habiles = filtro[filtro["Valor"] == "T"]

        dias_habiles = len(habiles)
        dias_habiles_lista = habiles["Fecha"].dt.date.tolist()

        # --- Licencias ---
        st.subheader("Licencias")
        col1, col2 = st.columns(2)
        with col1:
            fecha_desde = st.date_input("Desde", value=None)
        with col2:
            fecha_hasta = st.date_input("Hasta", value=None)

        if fecha_desde and fecha_hasta:
            rango_lic = pd.date_range(fecha_desde, fecha_hasta).date
            licencias = sum(1 for f in dias_habiles_lista if f in rango_lic)
            habiles_netos = dias_habiles - licencias
        else:
            licencias = 0
            habiles_netos = dias_habiles

        objetivo = math.ceil(habiles_netos * 0.40)

        # Cargar días ya registrados
        registros = sheet_registro.get_all_records()
        dias_registrados = [r["Dias_Presentes"] for r in registros
                           if r["Nombre"] == st.session_state.usuario
                           and r["Mes"] == meses[mes_sel]]
        dias_registrados = [date.fromisoformat(d) for d in dias_registrados if d]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Días Hábiles", dias_habiles)
        c2.metric("Días Hábiles Netos", habiles_netos)
        c3.metric("Objetivo 40%", objetivo)
        c4.metric("Días registrados", len(dias_registrados))

        # --- Calendario ---
        st.write("Seleccioná los días que fuiste presencial:")
        cal = calendar.monthcalendar(2026, mes_sel)
        dias_nuevos = []

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
                    fecha = date(2026, mes_sel, dia)
                    if fecha in dias_registrados:
                        cols[i].markdown(f"✅ {dia}")
                    elif fecha in dias_habiles_lista:
                        if cols[i].checkbox(str(dia), key=f"dia_{dia}"):
                            dias_nuevos.append(fecha)
                    else:
                        cols[i].markdown(f"~~{dia}~~")

        if st.button("Guardar"):
            if dias_nuevos:
                for fecha in dias_nuevos:
                    sheet_registro.append_row([
                        st.session_state.usuario, cr_sel, letra_sel,
                        meses[mes_sel], 2026, str(fecha), objetivo
                    ])
                st.success(f"✅ Se registraron {len(dias_nuevos)} días!")
                st.rerun()
            else:
                st.warning("Seleccioná al menos un día nuevo.")
