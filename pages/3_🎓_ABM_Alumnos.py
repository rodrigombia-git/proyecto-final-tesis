# pages/2_🎓_ABM_Alumnos.py
import streamlit as st
import pandas as pd
from utils import init_connection, add_logout_button
from postgrest import APIError

st.set_page_config(page_title="ABM de Alumnos", page_icon="🎓", layout="wide")

# 2. CONEXIÓN A LA BASE DE DATOS
supabase = init_connection()

# --- BLOQUE GUARDIÁN DE SEGURIDAD ---
if 'user_logged_in' not in st.session_state or not st.session_state['user_logged_in']:
    st.warning("Debes iniciar sesión para acceder a esta página.")
    st.page_link("App.py", label="Ir a la página de Login", icon="🔑")
    st.stop()
# --- FIN DEL BLOQUE GUARDIÁN ---

# --- LLAMADA AL BOTÓN DE LOGOUT ---
add_logout_button() # <-- Llamada


# --- FUNCIONES ---
def cargar_datos():
    """Carga alumnos y cohortes, y devuelve ambos dataframes."""
    try:
        alumnos_res = supabase.table("alumnos").select("*").order("nombre_completo").execute()
        cohortes_res = supabase.table("cohortes").select("id, nombre").execute()
        return pd.DataFrame(alumnos_res.data), pd.DataFrame(cohortes_res.data)
    except APIError as e:
        st.error(f"Error al cargar datos: {e.message}")
        # Devolver dataframes vacíos pero con las columnas esperadas para evitar errores posteriores
        return pd.DataFrame(columns=['id', 'matricula', 'nombre_completo', 'email', 'cohorte_id', 'fecha_creacion']), pd.DataFrame(columns=['id', 'nombre'])

def guardar_cambios(original_df, editado_df, df_cohortes):
    """Guarda los cambios en la base de datos."""
    mapa_cohortes = df_cohortes.set_index('nombre')['id'].to_dict()
    editado_df['cohorte_id'] = editado_df['cohorte_nombre'].map(mapa_cohortes)

    original_dict = original_df.set_index('id').to_dict('index')
    editado_dict = editado_df.dropna(subset=['id']).set_index('id').to_dict('index')
    
    nuevas_filas = editado_df[editado_df['id'].isna()]
    eliminados_ids = list(set(original_dict.keys()) - set(editado_dict.keys()))
    modificaciones = []
    for item_id, datos_editados in editado_dict.items():
        if item_id in original_dict and datos_editados != original_dict[item_id]:
            update_data = {
                'matricula': datos_editados['matricula'],
                'nombre_completo': datos_editados['nombre_completo'],
                'email': datos_editados['email'],
                'cohorte_id': datos_editados['cohorte_id']
            }
            modificaciones.append({'id': item_id, **update_data})

    if nuevas_filas.empty and not modificaciones and not eliminados_ids:
        st.toast("No hay cambios que guardar.")
        return

    try:
        if not nuevas_filas.empty:
            datos_nuevos = nuevas_filas[['matricula', 'nombre_completo', 'email', 'cohorte_id']].to_dict('records')
            supabase.table("alumnos").insert(datos_nuevos).execute()
            st.toast(f"{len(datos_nuevos)} nuevo(s) alumno(s) agregado(s).")
        if modificaciones:
            for item in modificaciones:
                alumno_id = item.pop('id')
                supabase.table("alumnos").update(item).eq("id", alumno_id).execute()
            st.toast(f"{len(modificaciones)} alumno(s) actualizado(s).")
        if eliminados_ids:
            for alumno_id in eliminados_ids:
                supabase.table("alumnos").delete().eq("id", alumno_id).execute()
            st.toast(f"{len(eliminados_ids)} alumno(s) eliminado(s).")
        st.success("¡Cambios guardados exitosamente!")
    except APIError as e:
        st.error(f"Error al guardar los cambios: {e.message}")

# --- LAYOUT ---
st.title("🎓 Gestión de Alumnos (ABM)")

df_alumnos_actual, df_cohortes = cargar_datos()

# --- Comprobación de seguridad ---
if df_cohortes.empty:
    st.warning("No se encontraron Cohortes. Por favor, cree al menos una cohorte en 'ABM Cohortes' antes de gestionar alumnos.")
    st.stop() # Detener la ejecución si no hay cohortes

# Preparar datos para el editor
mapa_cohortes_inverso = df_cohortes.set_index('id')['nombre'].to_dict()
if 'cohorte_id' in df_alumnos_actual.columns:
    df_alumnos_actual['cohorte_nombre'] = df_alumnos_actual['cohorte_id'].map(mapa_cohortes_inverso)
else:
    df_alumnos_actual['cohorte_nombre'] = None


st.info("Para asignar una Cohorte, selecciónela de la lista desplegable en la tabla.")

edited_df = st.data_editor(
    df_alumnos_actual,
    key="alumnos_editor",
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "id": None, 
        "cohorte_id": None,
        "matricula": st.column_config.TextColumn("Matrícula (Legajo)", required=True),
        "nombre_completo": st.column_config.TextColumn("Nombre Completo", required=True),
        "email": st.column_config.TextColumn("Email"), 
        "cohorte_nombre": st.column_config.SelectboxColumn(
            "Cohorte",
            help="La generación a la que pertenece el alumno",
            options=df_cohortes['nombre'].tolist(),
            required=False,
        ),
        "fecha_creacion": st.column_config.DatetimeColumn("Fecha de Creación", disabled=True),
    },
    column_order=("matricula", "nombre_completo", "email", "cohorte_nombre"),
    hide_index=True,
)

if st.button("Guardar Cambios"):
    guardar_cambios(df_alumnos_actual, edited_df, df_cohortes)
    st.rerun()