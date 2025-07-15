# pages/4_📝_ABM_Tesis.py
import streamlit as st
import pandas as pd
from utils import init_connection, add_logout_button
from postgrest import APIError
import time
from datetime import date
from dateutil.relativedelta import relativedelta

# 1. Configuración de página
st.set_page_config(page_title="Gestión de Tesis", page_icon="📝", layout="wide")

# 2. Guardián de seguridad
if 'user_logged_in' not in st.session_state or not st.session_state['user_logged_in']:
    st.warning("Debes iniciar sesión para acceder a esta página.")
    st.page_link("App.py", label="Volver a la página de Login", icon="🔑")
    st.stop()

# 3. Botón de logout e inicialización
add_logout_button()
supabase = init_connection()

# --- FUNCIONES ---
@st.cache_data(ttl=30)
def cargar_datos_maestros():
    try:
        tesis_res = supabase.table("tesis_completas").select("*").order("fecha_creacion", desc=True).execute()
        df_tesis = pd.DataFrame(tesis_res.data)
        if not df_tesis.empty and 'fecha_vencimiento_final' in df_tesis.columns:
            df_tesis['fecha_vencimiento_final'] = pd.to_datetime(df_tesis['fecha_vencimiento_final'], errors='coerce').dt.date
        alumnos_res = supabase.table("alumnos").select("id, nombre_completo, cohorte_id").execute()
        df_alumnos = pd.DataFrame(alumnos_res.data)
        tutores_res = supabase.table("tutores").select("id, nombre_completo").execute()
        df_tutores = pd.DataFrame(tutores_res.data)
        cohortes_res = supabase.table("cohortes").select("id, nombre, fecha_inicio").execute()
        df_cohortes = pd.DataFrame(cohortes_res.data)
        return df_tesis, df_alumnos, df_tutores, df_cohortes
    except APIError as e:
        st.error(f"Error al cargar datos: {e.message}"); return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

@st.cache_data(ttl=3600)
def get_plazo_tesis_meses():
    try:
        response = supabase.table("parametros").select("valor").eq("clave", "plazo_tesis_meses").single().execute()
        return int(response.data['valor'])
    except Exception:
        st.warning("No se encontró el parámetro 'plazo_tesis_meses'. Usando default de 24 meses.")
        return 24

def guardar_cambios(original_df, editado_df):
    original_dict = {rec['id']: rec for rec in original_df.to_dict('records')}
    editado_dict = {rec['id']: rec for rec in editado_df.to_dict('records') if pd.notna(rec.get('id'))}
    ids_eliminados = list(set(original_dict.keys()) - set(editado_dict.keys()))
    modificaciones = []
    for id, reg_editado in editado_dict.items():
        if id in original_dict and reg_editado != original_dict[id]:
             modificaciones.append(reg_editado)
    if not any([ids_eliminados, modificaciones]):
        st.toast("✅ No se detectaron cambios."); return
    progress_bar = st.progress(0, text="Guardando cambios...")
    try:
        if ids_eliminados: supabase.table("tesis").delete().in_("id", ids_eliminados).execute()
        if modificaciones:
            for item in modificaciones:
                update_data = {"titulo": item.get("titulo"), "estado": item.get("estado"), "anteproyecto_url": item.get("anteproyecto_url"), "fecha_vencimiento_tesis": str(item.get("fecha_vencimiento_final")) if pd.notna(item.get("fecha_vencimiento_final")) else None}
                supabase.table("tesis").update(update_data).eq("id", item['id']).execute()
        st.success("¡Cambios guardados!"); time.sleep(1); st.cache_data.clear(); st.rerun()
    except APIError as e: st.error(f"Error al guardar: {e.message}")
    finally: progress_bar.empty()

def formulario_alta_tesis(df_alumnos, df_tutores, df_cohortes):
    st.subheader("➕ Agregar Nueva Tesis")
    
    alumnos_con_tesis_res = supabase.table("tesis").select("alumno_id", count='exact').execute()
    ids_alumnos_con_tesis = [item['alumno_id'] for item in alumnos_con_tesis_res.data] if alumnos_con_tesis_res.count > 0 else []
    alumnos_disponibles = df_alumnos[~df_alumnos['id'].isin(ids_alumnos_con_tesis)]

    if alumnos_disponibles.empty or df_tutores.empty:
        st.warning("Asegúrese de que existan alumnos disponibles (sin tesis) y tutores registrados."); return

    mapa_cohortes = df_cohortes.set_index('id')
    plazo_meses = get_plazo_tesis_meses()

    # <<< INICIO DE LA ARQUITECTURA CORRECTA >>>
    # Paso 1: Seleccionar el alumno. Su selección se guarda automáticamente en el session_state
    st.info("Paso 1: Selecciona un alumno para cargar su información.")
    st.selectbox(
        "Alumno", 
        options=alumnos_disponibles.to_dict('records'), 
        format_func=lambda x: x['nombre_completo'], 
        index=None, 
        placeholder="Elige un alumno disponible",
        key='alumno_seleccionado' # Clave para guardar la selección
    )

    # Paso 2: Si hay un alumno seleccionado, mostramos el formulario de alta
    alumno_sel = st.session_state.get('alumno_seleccionado')
    if alumno_sel:
        # Calculamos la fecha de vencimiento ANTES de dibujar el formulario
        fecha_vencimiento_default = None
        cohorte_id = alumno_sel.get('cohorte_id')
        if cohorte_id and cohorte_id in mapa_cohortes.index:
            fecha_inicio_str = mapa_cohortes.loc[cohorte_id, 'fecha_inicio']
            if fecha_inicio_str:
                fecha_inicio = pd.to_datetime(fecha_inicio_str).date()
                fecha_vencimiento_default = fecha_inicio + relativedelta(months=plazo_meses)
        
        # El formulario ahora es un contenedor simple
        st.info(f"Paso 2: Completa los datos para la tesis de **{alumno_sel['nombre_completo']}**.")
        with st.form(key="add_tesis_form", clear_on_submit=True):
            titulo = st.text_input("Título de la Tesis")
            tutores_sel = st.multiselect("Tutor(es)", options=df_tutores.to_dict('records'), format_func=lambda x: x['nombre_completo'])
            estado = st.selectbox("Estado", ["Propuesta", "En desarrollo", "Defendida", "Vencida", "Cancelada"])
            fecha_vencimiento = st.date_input("Fecha de Vencimiento", value=fecha_vencimiento_default)
            link_anteproyecto = st.text_input("Link al Anteproyecto (URL)")
            
            submitted = st.form_submit_button("💾 Agregar Tesis")
            if submitted:
                if not all([titulo, tutores_sel]): 
                    st.warning("Título y al menos un Tutor son obligatorios."); return
                try:
                    fecha_a_guardar = str(fecha_vencimiento) if fecha_vencimiento else None
                    nueva_tesis_data = {"titulo": titulo, "alumno_id": alumno_sel['id'], "estado": estado, "fecha_vencimiento_tesis": fecha_a_guardar, "anteproyecto_url": link_anteproyecto}
                    supabase.table("tesis").insert(nueva_tesis_data).execute()
                    st.success(f"Tesis '{titulo}' agregada."); 
                    # El clear_on_submit del formulario se encarga de resetear los campos.
                    st.session_state.alumno_seleccionado = None # Reseteamos la selección del alumno
                    time.sleep(1); 
                    st.cache_data.clear(); 
                    st.rerun()
                except APIError as e: st.error(f"Error al agregar tesis: {e.message}")
        
        # Botón para cambiar de alumno
        if st.button("Limpiar Selección de Alumno"):
            st.session_state.alumno_seleccionado = None
            st.rerun()
    # <<< FIN DE LA ARQUITECTURA CORRECTA >>>

# --- LAYOUT PRINCIPAL (sin cambios) ---
st.title("📝 Gestión de Tesis")
st.write("Usa la tabla para editar o eliminar tesis. Para agregar una nueva, utiliza el formulario al final.")
df_tesis, df_alumnos, df_tutores, df_cohortes = cargar_datos_maestros()
# ... (El resto del código de la grilla no cambia)
if 'df_tesis_edit' not in st.session_state: st.session_state.df_tesis_edit = df_tesis.copy()
with st.form(key="data_editor_form_tesis"):
    st.caption("Tabla de Tesis")
    edited_df = st.data_editor(st.session_state.df_tesis_edit, key="tesis_editor", num_rows="dynamic", use_container_width=True,
        column_config={
            "id": None, "alumno_id": None, "fecha_creacion": None, "porcentaje_avance": None,
            "fecha_actualizacion_avance": None, "porcentaje_tiempo_baseline": None, "ritmo_avance": None,
            "cohorte_nombre": st.column_config.TextColumn("Cohorte", disabled=True),
            "alumno_nombre": st.column_config.TextColumn("Alumno", disabled=True),
            "tutores": st.column_config.TextColumn("Tutor(es)", disabled=True),
            "estado": st.column_config.SelectboxColumn("Estado", options=["Propuesta", "En desarrollo", "Defendida", "Vencida", "Cancelada"], required=True),
            "anteproyecto_url": st.column_config.LinkColumn("Anteproyecto", display_text="🔗 Link"),
            "titulo": st.column_config.TextColumn("Título", width="large", required=True),
            "fecha_vencimiento_final": st.column_config.DateColumn("Vencimiento", help="Fecha límite manual o calculada por cohorte.")},
        column_order=("cohorte_nombre", "alumno_nombre", "tutores", "estado", "anteproyecto_url", "titulo", "fecha_vencimiento_final"),
        hide_index=True, disabled=["id", "alumno_id", "cohorte_nombre", "alumno_nombre", "tutores"])
    if st.form_submit_button("💾 Guardar Cambios"):
        guardar_cambios(st.session_state.df_tesis_edit, edited_df)
        del st.session_state.df_tesis_edit
st.divider()
formulario_alta_tesis(df_alumnos, df_tutores, df_cohortes)