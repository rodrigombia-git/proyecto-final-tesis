# pages/1_📊_Dashboard.py
import streamlit as st
import pandas as pd
from utils import init_connection, add_logout_button
from datetime import date, datetime
import plotly.express as px

# --- 1. CONFIGURACIÓN Y ESTILO ---
st.set_page_config(
    page_title="Dashboard General de Tesis",
    page_icon="🎓",
    layout="wide"
)

# --- BLOQUE GUARDIÁN DE SEGURIDAD ---
if 'user_logged_in' not in st.session_state or not st.session_state['user_logged_in']:
    st.warning("Debes iniciar sesión para acceder a esta página.")
    st.page_link("App.py", label="Ir a la página de Login", icon="🔑")
    st.stop()
# --- FIN DEL BLOQUE GUARDIÁN ---

# --- LLAMADA AL BOTÓN DE LOGOUT ---
add_logout_button()

# --- CONEXIÓN Y CARGA DE DATOS ---
supabase = init_connection()

@st.cache_data(ttl=300)
def cargar_datos_dashboard():
    """Carga todos los datos de la vista 'tesis_completas'."""
    try:
        df = pd.DataFrame(supabase.table("tesis_completas").select("*").execute().data)
        if not df.empty:
            df['porcentaje_avance'] = pd.to_numeric(df['porcentaje_avance'], errors='coerce').fillna(0)
            df['porcentaje_tiempo_baseline'] = pd.to_numeric(df['porcentaje_tiempo_baseline'], errors='coerce').fillna(0)
            df['fecha_vencimiento_final'] = pd.to_datetime(df['fecha_vencimiento_final'], errors='coerce')
        return df
    except Exception as e:
        st.error(f"Error al cargar datos: {e}"); return pd.DataFrame()

@st.cache_data(ttl=600)
def cargar_cohortes():
    """Carga los nombres de las cohortes para el filtro."""
    try:
        cohortes_res = supabase.table("cohortes").select("nombre").order("nombre").execute()
        return [c['nombre'] for c in cohortes_res.data]
    except Exception as e:
        st.error(f"Error al cargar cohortes: {e}")
        return []

df = cargar_datos_dashboard()
cohortes = ["Todas las Cohortes"] + cargar_cohortes()

# --- TÍTULO Y FILTRO ---
st.markdown(
    "<h1 style='text-align: center; color: #FAFAFA;'>🎓 Dashboard de Seguimiento de Tesis</h1>", 
    unsafe_allow_html=True
)
st.markdown(
    f"<p style='text-align: center; color: #A0A0A0;'>Estado de situación actualizado al {date.today().strftime('%d/%m/%Y')}</p>", 
    unsafe_allow_html=True
)

# --- NUEVO WIDGET DE FILTRO POR COHORTE ---
cohorte_seleccionada = st.selectbox(
    "Filtrar por Cohorte",
    options=cohortes,
    index=0  # 'Todas las Cohortes' por defecto
)

st.write("---")

# --- FILTRADO DEL DATAFRAME ---
if df.empty:
    st.warning("No hay datos de tesis para mostrar."); st.stop()

if cohorte_seleccionada == "Todas las Cohortes":
    df_filtrado = df.copy()
else:
    df_filtrado = df[df['cohorte_nombre'] == cohorte_seleccionada].copy()

if df_filtrado.empty:
    st.info(f"No hay datos de tesis para la cohorte '{cohorte_seleccionada}'.")
    st.stop()


# --- 4. TARJETAS DE KPIs (Ahora usan df_filtrado) ---
df_activas = df_filtrado[~df_filtrado['estado'].isin(['Defendida', 'Cancelada', 'Vencida'])]
hoy = pd.Timestamp.now()
atrasadas = len(df_activas[df_activas['ritmo_avance'] == 'Atrasada'])
vencimiento_limite = hoy + pd.Timedelta(days=90)
proximas_a_vencer = len(df_activas[(df_activas['fecha_vencimiento_final'] >= hoy) & (df_activas['fecha_vencimiento_final'] <= vencimiento_limite)])
avg_avance = int(df_activas['porcentaje_avance'].mean()) if not df_activas.empty else 0

# (El código CSS de las métricas no cambia)
st.markdown("""
<style>
.metric-card { background-color: #262730; border-radius: 10px; padding: 20px; margin: 10px; text-align: center; border: 1px solid #444; }
.metric-card h3 { color: #A0A0A0; font-size: 18px; margin-bottom: 5px; }
.metric-card p { color: #FAFAFA; font-size: 32px; font-weight: bold; }
.metric-card .delta { color: #FF4B4B; font-size: 16px; }
</style>
""", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f'<div class="metric-card"><h3>📝 Tesis Activas</h3><p>{len(df_activas)}</p></div>', unsafe_allow_html=True)
with col2:
    st.markdown(f'<div class="metric-card"><h3>📊 Avance Promedio</h3><p>{avg_avance}%</p></div>', unsafe_allow_html=True)
with col3:
    st.markdown(f'<div class="metric-card"><h3>⚠️ Tesis Atrasadas</h3><p>{atrasadas}</p><span class="delta">{atrasadas} en riesgo</span></div>', unsafe_allow_html=True)
with col4:
    st.markdown(f'<div class="metric-card"><h3>⏰ Vencen < 90 días</h3><p>{proximas_a_vencer}</p><span class="delta">{proximas_a_vencer} con urgencia</span></div>', unsafe_allow_html=True)

st.write("---")

# --- 5. GRÁFICOS Y FOCO DE ATENCIÓN (Ahora usan df_activas, que ya está filtrado) ---
col_graf, col_foco = st.columns([3, 2])

with col_graf:
    st.subheader("Distribución General")
    ritmo_counts = df_activas['ritmo_avance'].value_counts().reindex(['Adelantada', 'En curso normal', 'Atrasada']).fillna(0)
    fig_ritmo = px.bar(ritmo_counts, x=ritmo_counts.index, y=ritmo_counts.values,
                       color=ritmo_counts.index, text_auto=True,
                       color_discrete_map={'Adelantada': '#28a745', 'En curso normal': '#17a2b8', 'Atrasada': '#dc3545'},
                       labels={'x': '', 'y': ''})
    fig_ritmo.update_layout(showlegend=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#FAFAFA')
    st.plotly_chart(fig_ritmo, use_container_width=True)

with col_foco:
    st.subheader("Foco de Atención")
    df_atrasadas = df_activas[df_activas['ritmo_avance'] == 'Atrasada'].copy()
    df_atrasadas['diferencia'] = df_atrasadas['porcentaje_tiempo_baseline'] - df_atrasadas['porcentaje_avance']
    df_top_atrasadas = df_atrasadas.sort_values('diferencia', ascending=False).head(3)

    if df_top_atrasadas.empty:
        st.success("¡Excelente! No hay tesis en foco de atención por atraso en esta selección.")
    else:
        for index, row in df_top_atrasadas.iterrows():
            st.markdown(f"""
            <div class="metric-card" style="text-align: left; border-left: 5px solid #dc3545; margin-bottom: 15px;">
                <span style="font-weight: bold; color: #FAFAFA;">{row['alumno_nombre']}</span><br>
                <span style="font-size: 14px; color: #A0A0A0;">Avance Real: {row['porcentaje_avance']:.0f}% vs Esperado: {row['porcentaje_tiempo_baseline']:.0f}%</span>
            </div>
            """, unsafe_allow_html=True)

st.write("---")

# --- 6. DATOS DETALLADOS (Ahora usan dataframes ya filtrados) ---
with st.expander("Ver Datos Detallados y Listas de Seguimiento"):
    col_tabla_1, col_tabla_2 = st.columns(2)
    with col_tabla_1:
        st.subheader("Tesis con Mayor Atraso")
        if df_atrasadas.empty:
            st.info("No hay tesis activas clasificadas como 'Atrasadas' en esta selección.")
        else:
            st.dataframe(df_atrasadas[['alumno_nombre', 'porcentaje_avance', 'porcentaje_tiempo_baseline', 'diferencia']].sort_values('diferencia', ascending=False),
                column_config={"alumno_nombre": "Alumno", "porcentaje_avance": st.column_config.ProgressColumn("Avance Real"), "porcentaje_tiempo_baseline": st.column_config.ProgressColumn("Avance Esperado"), "diferencia": "Brecha (%)"},
                use_container_width=True, hide_index=True)
    
    with col_tabla_2:
        st.subheader("Próximos Vencimientos (Activas)")
        df_vencimientos = df_activas[df_activas['fecha_vencimiento_final'] >= datetime.now()].copy()
        if df_vencimientos.empty:
            st.info("No hay tesis activas con vencimientos futuros en esta selección.")
        else:
            df_vencimientos['dias_restantes'] = (df_vencimientos['fecha_vencimiento_final'] - pd.Timestamp.now()).dt.days
            st.dataframe(df_vencimientos[['alumno_nombre', 'fecha_vencimiento_final', 'dias_restantes']].sort_values('dias_restantes'),
                column_config={"alumno_nombre": "Alumno", "fecha_vencimiento_final": st.column_config.DateColumn("Fecha Límite", format="DD/MM/YYYY"), "dias_restantes": "Días Restantes"},
                use_container_width=True, hide_index=True)