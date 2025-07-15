# pages/5_📈_Seguimiento_Individual.py
import streamlit as st
import pandas as pd
from utils import init_connection, add_logout_button
from postgrest import APIError
import time
from datetime import date

st.set_page_config(page_title="Seguimiento de Tesis", page_icon="📈", layout="wide")
supabase = init_connection()

# --- BLOQUE GUARDIÁN DE SEGURIDAD ---
if 'user_logged_in' not in st.session_state or not st.session_state['user_logged_in']:
    st.warning("Debes iniciar sesión para acceder a esta página.")
    st.page_link("App.py", label="Ir a la página de Login", icon="🔑")
    st.stop()
# --- FIN DEL BLOQUE GUARDIÁN ---

# --- LLAMADA AL BOTÓN DE LOGOUT ---
add_logout_button() # <-- Llamada

# --- FUNCIONES DE CARGA (sin cambios) ---
@st.cache_data(ttl=60)
def cargar_datos_para_filtros():
    try:
        cohortes_res = supabase.table("cohortes").select("id, nombre").order("nombre").execute()
        df_cohortes = pd.DataFrame(cohortes_res.data)
        tesis_res = supabase.table("tesis").select("id, titulo, alumnos(id, nombre_completo, cohorte_id)").execute()
        df_tesis = pd.DataFrame(tesis_res.data)
        if df_tesis.empty: return df_cohortes, df_tesis
        df_tesis['alumno_id'] = df_tesis['alumnos'].apply(lambda x: x['id'] if x and isinstance(x, dict) else None)
        df_tesis['alumno_nombre'] = df_tesis['alumnos'].apply(lambda x: x['nombre_completo'] if x and isinstance(x, dict) else "N/A")
        df_tesis['cohorte_id'] = df_tesis['alumnos'].apply(lambda x: x['cohorte_id'] if x and isinstance(x, dict) else None)
        return df_cohortes, df_tesis
    except APIError as e: st.error(f"Error al cargar datos: {e.message}"); return pd.DataFrame(), pd.DataFrame()

@st.cache_data(ttl=5)
def cargar_detalle_tesis(tesis_id):
    try:
        response = supabase.table("tesis_completas").select("*").eq("id", tesis_id).single().execute()
        return response.data
    except APIError as e: st.error(f"Error al cargar detalle de tesis: {e.message}"); return None

@st.cache_data(ttl=30)
def cargar_novedades(tesis_id):
    columnas = ['id', 'tesis_id', 'descripcion', 'fecha_novedad']
    try:
        resp = supabase.table("novedades_tesis").select("*").eq("tesis_id", tesis_id).order("fecha_novedad", desc=True).execute()
        df = pd.DataFrame(resp.data)
        if df.empty: return pd.DataFrame(columns=columnas)
        df['fecha_novedad'] = pd.to_datetime(df['fecha_novedad']).dt.date
        return df
    except APIError as e: st.error(f"Error al cargar novedades: {e.message}"); return pd.DataFrame(columns=columnas)

# --- FUNCIONES DE INTERFAZ Y GUARDADO (sin cambios) ---

def panel_de_avance(detalle_tesis):
    st.subheader("📊 Estado General del Avance")
    
    avance_real = detalle_tesis.get('porcentaje_avance', 0)
    baseline_str = detalle_tesis.get('porcentaje_tiempo_baseline')
    baseline_esperado = int(float(baseline_str)) if baseline_str is not None else 0
    ritmo = detalle_tesis.get('ritmo_avance', 'No calculable')

    col_progreso, col_ritmo = st.columns([3, 1])
    
    with col_progreso:
        st.write("**Avance Real vs. Baseline Esperado a Hoy**")
        st.progress(avance_real, text=f"{avance_real}% - Avance Real")
        st.progress(baseline_esperado, text=f"{baseline_esperado}% - Baseline Esperado (a hoy)")
    
    with col_ritmo:
        diferencia = avance_real - baseline_esperado
        st.metric(
            label="Ritmo vs Baseline Actual", 
            value=ritmo, 
            delta=f"{diferencia}%",
            delta_color="off" if ritmo in ["No calculable", "N/A"] else ("normal" if diferencia >= 0 else "inverse")
        )
        st.caption(f"El avance real está {abs(diferencia)} puntos {'por debajo de' if diferencia < 0 else 'por encima o igual a'} la línea base.")

    with st.expander("✏️ **Registrar o Modificar Avance**"):
        with st.form(key="form_avance"):
            fecha_actual_str = detalle_tesis.get('fecha_actualizacion_avance')
            fecha_actual_obj = pd.to_datetime(fecha_actual_str).date() if fecha_actual_str else date.today()
            
            col_slider, col_date = st.columns(2)
            with col_slider:
                nuevo_porcentaje = st.slider("Porcentaje de avance:", 0, 100, avance_real)
            with col_date:
                nueva_fecha = st.date_input("Fecha de la actualización:", value=fecha_actual_obj)
            
            submitted = st.form_submit_button("💾 Guardar Avance")
            if submitted:
                try:
                    payload = {"porcentaje_avance": nuevo_porcentaje, "fecha_actualizacion_avance": str(nueva_fecha)}
                    supabase.table("tesis").update(payload).eq("id", detalle_tesis['id']).execute()
                    st.success(f"¡Avance actualizado!"); 
                    st.cache_data.clear()
                    time.sleep(1)
                    st.rerun()
                except APIError as e: st.error(f"Error al guardar: {e.message}")

def guardar_cambios_novedades(tesis_id, original_df, editado_df):
    original_dict = {rec['id']: rec for rec in original_df.to_dict('records')}
    editado_dict = {rec['id']: rec for rec in editado_df.to_dict('records') if pd.notna(rec.get('id'))}
    ids_eliminados = list(set(original_dict.keys()) - set(editado_dict.keys()))
    modificaciones = [rec for id, rec in editado_dict.items() if id in original_dict and rec != original_dict[id]]
    
    filas_nuevas_validas = editado_df[pd.isna(editado_df['id']) & editado_df['descripcion'].notna() & pd.notna(editado_df['fecha_novedad'])]
    nuevos_registros = []
    if not filas_nuevas_validas.empty:
        nuevos_registros = filas_nuevas_validas[['descripcion', 'fecha_novedad']].to_dict('records')
        for r in nuevos_registros:
            r['tesis_id'] = tesis_id
            r['fecha_novedad'] = r['fecha_novedad'].isoformat()
            
    if not any([ids_eliminados, modificaciones, nuevos_registros]): 
        st.toast("✅ No hay cambios en la bitácora."); return

    progress_bar = st.progress(0, text="Guardando bitácora...");
    try:
        if ids_eliminados: supabase.table("novedades_tesis").delete().in_("id", ids_eliminados).execute()
        if modificaciones:
            for item in modificaciones:
                novedad_id = item.pop('id'); item.pop('tesis_id', None)
                if isinstance(item.get('fecha_novedad'), date):
                    item['fecha_novedad'] = item.get('fecha_novedad').isoformat()
                supabase.table("novedades_tesis").update(item).eq("id", novedad_id).execute()
        if nuevos_registros: supabase.table("novedades_tesis").insert(nuevos_registros).execute()

        st.success("¡Bitácora actualizada!"); 
        time.sleep(1); progress_bar.empty(); st.cache_data.clear()
        if 'df_novedades' in st.session_state: del st.session_state.df_novedades
        if 'tesis_id' in st.session_state: del st.session_state.tesis_id
        st.rerun()

    except APIError as e: 
        progress_bar.empty(); st.error(f"❌ Error al guardar: {e.message}")


# --- LAYOUT PRINCIPAL ---
st.title("📈 Seguimiento Individual de Tesis")
st.write("Selecciona una tesis para ver su detalle, actualizar su avance y gestionar su bitácora.")
df_cohortes, df_tesis = cargar_datos_para_filtros()
if df_cohortes.empty: st.warning("No hay cohortes registradas."); st.stop()

col1, col2 = st.columns(2)
with col1:
    mapa_cohortes = df_cohortes.set_index('nombre')['id'].to_dict()
    cohorte_seleccionada_nombre = st.selectbox("1. Selecciona una Cohorte", options=mapa_cohortes.keys(), index=None, placeholder="Elegir cohorte...")
with col2:
    if cohorte_seleccionada_nombre:
        cohorte_id = mapa_cohortes[cohorte_seleccionada_nombre]
        tesis_filtradas = df_tesis[df_tesis['cohorte_id'] == cohorte_id].copy()
        tesis_filtradas['display'] = tesis_filtradas.apply(lambda r: f"{r['alumno_nombre']} - {r['titulo'][:40]}...", axis=1)
        mapa_tesis = tesis_filtradas.set_index('id')['display'].to_dict()
        tesis_id_seleccionada = st.selectbox("2. Selecciona una Tesis", options=mapa_tesis.keys(), format_func=lambda x: mapa_tesis.get(x, "N/A"), index=None, placeholder="Elegir tesis...", disabled=tesis_filtradas.empty)
    else:
        tesis_id_seleccionada = st.selectbox("2. Selecciona una Tesis", options=[], index=None, placeholder="Primero elige una cohorte", disabled=True)

st.divider()

if tesis_id_seleccionada:
    detalle_tesis = cargar_detalle_tesis(tesis_id_seleccionada)
    if detalle_tesis:
        st.header(f"Seguimiento de: *{detalle_tesis['titulo']}*")
        st.caption(f"Alumno: **{detalle_tesis['alumno_nombre']}** | Tutores: **{detalle_tesis['tutores']}**")
        panel_de_avance(detalle_tesis)
        st.divider()
        st.subheader("📖 Bitácora de Novedades")
        
        if 'df_novedades' not in st.session_state or st.session_state.get('tesis_id') != tesis_id_seleccionada:
            df_novedades = cargar_novedades(tesis_id_seleccionada)
            st.session_state.df_novedades = df_novedades.copy()
            st.session_state.tesis_id = tesis_id_seleccionada
        else:
            # Nos aseguramos de tener la variable disponible
            df_novedades = st.session_state.df_novedades

        # --- CAMBIO 1: SECCIÓN DE EDICIÓN EN UN EXPANDER ---
        with st.expander("✏️ **Editar o Agregar Novedades a la Bitácora**"):
            st.info("Para agregar un salto de línea en la descripción, presiona Shift + Enter.")
            with st.form(key="novedades_form"):
                edited_df = st.data_editor(
                    st.session_state.df_novedades, 
                    key="novedades_editor", 
                    num_rows="dynamic", 
                    use_container_width=True,
                    column_config={
                        "id": None, 
                        "tesis_id": None, 
                        "fecha_novedad": st.column_config.DateColumn("Fecha", required=True), 
                        "descripcion": st.column_config.TextColumn("Descripción", width="large", required=True)
                    },
                    hide_index=True, 
                    column_order=("fecha_novedad", "descripcion")
                )
                submitted = st.form_submit_button("💾 Guardar Cambios en Bitácora")
            
            if submitted:
                guardar_cambios_novedades(tesis_id_seleccionada, st.session_state.df_novedades.copy(), edited_df)
        
        st.divider()

        # --- CAMBIO 2: NUEVA SECCIÓN DE VISUALIZACIÓN ---
        st.subheader("👓 Vista Detallada de la Bitácora")
        if df_novedades.empty:
            st.info("Aún no hay novedades registradas para esta tesis.")
        else:
            # Iteramos sobre el DataFrame para mostrar cada entrada de forma formateada
            for index, row in df_novedades.sort_values(by="fecha_novedad", ascending=False).iterrows():
                st.markdown(f"**Fecha:** {row['fecha_novedad'].strftime('%d/%m/%Y')}")
                # Usamos st.markdown para que respete los saltos de línea y otros formatos
                st.markdown(f"<blockquote>{row['descripcion']}</blockquote>", unsafe_allow_html=True) 
                st.markdown("---")