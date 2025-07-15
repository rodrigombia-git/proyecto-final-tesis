# # pages/1_👨‍🏫_ABM_Tutores.py
import streamlit as st
import pandas as pd
from utils import init_connection, add_logout_button
from postgrest import APIError

# --- Configuración de la Página ---
st.set_page_config(
    page_title="ABM de Tutores",
    page_icon="👨‍🏫",
    layout="wide"
)

# --- Conexión a la Base de Datos ---
# Se inicializa una única vez y se guarda en el session_state de Streamlit
if 'supabase' not in st.session_state:
    st.session_state['supabase'] = init_connection()
supabase = st.session_state['supabase']

# --- BLOQUE GUARDIÁN DE SEGURIDAD ---
if 'user_logged_in' not in st.session_state or not st.session_state['user_logged_in']:
    st.warning("Debes iniciar sesión para acceder a esta página.")
    st.page_link("App.py", label="Ir a la página de Login", icon="🔑")
    st.stop()
# --- FIN DEL BLOQUE GUARDIÁN ---

# --- LLAMADA AL BOTÓN DE LOGOUT ---
add_logout_button() # <-- Llamada

# --- Funciones de la Página ---

def cargar_tutores():
    """Carga los tutores desde la base de datos."""
    try:
        # Usamos una consulta simple que puede ser cacheada
        response = supabase.table("tutores").select("*").order("nombre_completo").execute()
        return pd.DataFrame(response.data)
    except APIError as e:
        st.error(f"Error al cargar tutores: {e.message}")
        return pd.DataFrame()

def guardar_cambios(original_df, editado_df):
    """Compara los dataframes y aplica los cambios a la base de datos."""
    
    # Preparamos los dataframes para la comparación
    original_df.set_index('id', inplace=True)
    editado_df.set_index('id', inplace=True)
    
    # Detectar filas modificadas
    modificaciones = editado_df[editado_df.ne(original_df.reindex_like(editado_df))].dropna(how='all')
    
    # Detectar filas eliminadas
    eliminados_ids = list(set(original_df.index) - set(editado_df.index))
    
    # Detectar filas añadidas (aquellas con ID nulo/NaN)
    nuevos = editado_df[editado_df.index.isna()]
    
    total_cambios = len(modificaciones) + len(eliminados_ids) + len(nuevos)
    if total_cambios == 0:
        st.toast("No hay cambios que guardar.")
        return

    progress_text = "Guardando cambios... Por favor, espere."
    progress_bar = st.progress(0, text=progress_text)
    
    try:
        # 1. Procesar Eliminaciones
        if eliminados_ids:
            for tutor_id in eliminados_ids:
                supabase.table("tutores").delete().eq("id", tutor_id).execute()
            st.toast(f"{len(eliminados_ids)} tutor(es) eliminado(s).")
        
        # 2. Procesar Modificaciones
        if not modificaciones.empty:
            # Iteramos sobre las filas modificadas
            for tutor_id, row in modificaciones.iterrows():
                # Creamos un diccionario solo con los valores que cambiaron (no nulos)
                update_data = row.dropna().to_dict()
                supabase.table("tutores").update(update_data).eq("id", tutor_id).execute()
            st.toast(f"{len(modificaciones)} tutor(es) actualizado(s).")

        # 3. Procesar Adiciones
        if not nuevos.empty:
            # Quitamos el índice (que es NaN) y la columna de fecha_creacion
            nuevos_data = nuevos.drop(columns=['fecha_creacion']).to_dict('records')
            supabase.table("tutores").insert(nuevos_data).execute()
            st.toast(f"{len(nuevos)} nuevo(s) tutor(es) agregado(s).")

        # Actualización finalizada
        progress_bar.progress(100, text="¡Cambios guardados exitosamente!")
        st.success("¡Todos los cambios han sido guardados en la base de datos!")
        
        # Limpiamos el session_state para forzar la recarga de datos frescos
        if 'tutores_df' in st.session_state:
            del st.session_state['tutores_df']

    except APIError as e:
        st.error(f"Error al guardar los cambios: {e.message}")
    finally:
        # Ocultar la barra de progreso después de un momento
        import time
        time.sleep(2)
        progress_bar.empty()


# --- Layout Principal de la Página ---
st.title("👨‍🏫 Gestión de Tutores (ABM)")
st.write("Utiliza la tabla para agregar, editar o eliminar tutores. **Haz clic en 'Guardar Cambios' para aplicar tus modificaciones.**")

# --- Carga de datos y cacheo en session_state ---
# Esto evita recargar los datos de la DB en cada interacción, solo cuando se guardan cambios.
if 'tutores_df' not in st.session_state:
    st.session_state.tutores_df = cargar_tutores()

# --- Interfaz de Edición ---
with st.form(key="data_editor_form"):
    st.caption("Tabla de Tutores")
    # El data_editor se alimenta del dataframe en el estado de la sesión
    edited_df = st.data_editor(
        st.session_state.tutores_df,
        key="tutores_editor",
        num_rows="dynamic", # Permite agregar y eliminar filas
        use_container_width=True,
        column_config={
            "id": None, # Ocultamos la columna 'id'
            "nombre_completo": st.column_config.TextColumn("Nombre Completo", required=True),
            "email": st.column_config.TextColumn("Email", required=True),
            "area_experiencia": st.column_config.TextColumn("Área de Experiencia", required=True),
            "fecha_creacion": st.column_config.DatetimeColumn(
                "Fecha de Creación",
                disabled=True,
            ),
        },
        hide_index=True,
    )

    submitted = st.form_submit_button("Guardar Cambios")

if submitted:
    # Cuando se presiona el botón, se compara el DF original con el editado
    guardar_cambios(st.session_state.tutores_df, edited_df)
    # Forzamos un rerun para que la tabla se redibuje con los datos actualizados
    st.rerun()