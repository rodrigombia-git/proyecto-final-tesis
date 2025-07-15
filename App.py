# App.py (Versión Monolítica Definitiva)
import streamlit as st
import pandas as pd
import bcrypt
from utils import init_connection
import plotly.express as px
from datetime import date, datetime
import time

# --- Configuración de Página ---
st.set_page_config(page_title="Gestor de Tesis", page_icon="🎓", layout="wide")

# --- FUNCIONES DE LA APP ---

def check_password(email, password):
    supabase = init_connection()
    try:
        user = supabase.table("usuarios").select("password_hash").eq("email", email).single().execute().data
        if not user or not user.get("password_hash"): return False
        password_bytes = password.encode('utf-8')
        hashed_password_bytes = user["password_hash"].encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_password_bytes)
    except Exception:
        return False

@st.cache_data(ttl=300)
def cargar_datos_dashboard():
    supabase = init_connection()
    try:
        df = pd.DataFrame(supabase.table("tesis_completas").select("*").execute().data)
        if not df.empty:
            df['porcentaje_avance'] = pd.to_numeric(df['porcentaje_avance'], errors='coerce').fillna(0)
            df['porcentaje_tiempo_baseline'] = pd.to_numeric(df['porcentaje_tiempo_baseline'], errors='coerce').fillna(0)
            df['fecha_vencimiento_final'] = pd.to_datetime(df['fecha_vencimiento_final'], errors='coerce')
        return df
    except Exception as e:
        st.error(f"Error al cargar datos: {e}"); return pd.DataFrame()

def render_dashboard():
    # --- Este es el código de tu antiguo 1_Dashboard.py ---
    st.sidebar.success("Sesión iniciada.")
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state['user_logged_in'] = False
        st.rerun()

    df = cargar_datos_dashboard()

    st.markdown("<h1 style='text-align: center; color: #FAFAFA;'>🎓 Dashboard de Seguimiento de Tesis</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: #A0A0A0;'>Actualizado al {date.today().strftime('%d/%m/%Y')}</p>", unsafe_allow_html=True)
    st.write("---")

    if df.empty:
        st.warning("No hay datos de tesis para mostrar."); st.stop()

    df_activas = df[~df['estado'].isin(['Defendida', 'Cancelada', 'Vencida'])]
    avg_avance = int(df_activas['porcentaje_avance'].mean()) if not df_activas.empty else 0
    atrasadas = len(df_activas[df_activas['ritmo_avance'] == 'Atrasada'])
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Tesis Activas", len(df_activas))
    col2.metric("Avance Promedio", f"{avg_avance}%")
    col3.metric("Tesis Atrasadas", atrasadas)
    
    # Aquí puedes añadir el resto de los gráficos y KPIs del dashboard...

def render_login():
    # --- Este es el código de tu antiguo App.py ---
    st.title("🔑 Acceso al Sistema de Gestión de Tesis")
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Contraseña", type="password")
        submitted = st.form_submit_button("Entrar")
        if submitted:
            if check_password(email, password):
                st.session_state['user_logged_in'] = True
                st.rerun()
            else:
                st.error("Email o contraseña incorrectos.")

# --- LÓGICA DE ENRUTAMIENTO PRINCIPAL ---
if 'user_logged_in' not in st.session_state:
    st.session_state['user_logged_in'] = False

if st.session_state['user_logged_in']:
    render_dashboard()
else:
    render_login()