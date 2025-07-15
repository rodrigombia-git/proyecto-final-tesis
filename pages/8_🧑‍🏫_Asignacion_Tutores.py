# pages/8_🧑‍🏫_Asignacion_Tutores.py
import streamlit as st
import pandas as pd
from utils import init_connection, add_logout_button
from postgrest import APIError
import time

# 1. Configuración de página
st.set_page_config(page_title="Asignación de Tutores", page_icon="🧑‍🏫", layout="centered")
supabase = init_connection()

# 2. Guardián de seguridad
if 'user_logged_in' not in st.session_state or not st.session_state['user_logged_in']:
    st.warning("Debes iniciar sesión para acceder a esta página.")
    st.page_link("App.py", label="Ir a la página de Login", icon="🔑")
    st.stop()

# 3. Botón de logout
add_logout_button()

# --- FUNCIONES ---

@st.cache_data(ttl=60)
def cargar_datos_maestros():
    """Carga cohortes, tesis y tutores para los selectores."""
    try:
        # Cargar cohortes (sin cambios)
        cohortes_res = supabase.table("cohortes").select("id, nombre").order("nombre").execute()
        df_cohortes = pd.DataFrame(cohortes_res.data)

        # --- INICIO DE LA CORRECCIÓN ---
        # En lugar de usar 'tesis_completas', consultamos 'tesis' y pedimos los datos
        # relacionados de la tabla 'alumnos' para obtener cohorte_id y nombre_completo.
        tesis_res = supabase.table("tesis").select(
            "id, titulo, alumnos(nombre_completo, cohorte_id)"
        ).execute()

        # Procesamos la respuesta anidada para crear un DataFrame plano
        tesis_data = []
        for item in tesis_res.data:
            # Nos aseguramos de que la tesis tenga un alumno asignado
            if item.get('alumnos'):
                tesis_data.append({
                    'id': item['id'],
                    'titulo': item['titulo'],
                    'alumno_nombre': item['alumnos']['nombre_completo'],
                    'cohorte_id': item['alumnos']['cohorte_id']
                })
        df_tesis = pd.DataFrame(tesis_data)
        # --- FIN DE LA CORRECIÓn ---
        
        # Cargar tutores (sin cambios)
        tutores_res = supabase.table("tutores").select("id, nombre_completo").order("nombre_completo").execute()
        df_tutores = pd.DataFrame(tutores_res.data)
        
        return df_cohortes, df_tesis, df_tutores
    except APIError as e:
        st.error(f"Error al cargar datos maestros: {e.message}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

def guardar_asignacion(tesis_id, nuevos_tutores_ids):
    """
    Sincroniza los tutores de una tesis en la tabla 'tesis_tutores'.
    Este método es robusto: primero borra las asignaciones viejas y luego inserta las nuevas.
    """
    try:
        supabase.table("tesis_tutores").delete().eq("tesis_id", tesis_id).execute()

        if nuevos_tutores_ids:
            registros_a_insertar = [
                {"tesis_id": tesis_id, "tutor_id": tutor_id} 
                for tutor_id in nuevos_tutores_ids
            ]
            supabase.table("tesis_tutores").insert(registros_a_insertar).execute()
        
        st.success("¡Asignación de tutores guardada exitosamente!")
        st.cache_data.clear()
        time.sleep(1)
        st.rerun()

    except APIError as e:
        st.error(f"Error al guardar la asignación: {e.message}")


# --- LAYOUT PRINCIPAL ---
st.title("🧑‍🏫 Asignación de Tutores a Tesis")
st.write(
    "Esta sección permite cambiar o reasignar los tutores de una tesis existente. "
    "Los cambios se reflejarán en toda la aplicación."
)

df_cohortes, df_tesis, df_tutores = cargar_datos_maestros()

if df_cohortes.empty or df_tutores.empty:
    st.warning("Debe haber al menos una cohorte y un tutor registrados para usar esta funcionalidad.")
    st.stop()

# --- PASO 1: Seleccionar la Cohorte ---
st.header("1. Filtre por Cohorte")
mapa_cohortes = df_cohortes.set_index('nombre')['id'].to_dict()
cohorte_seleccionada_nombre = st.selectbox(
    "Cohorte",
    options=mapa_cohortes.keys(),
    index=None,
    placeholder="Seleccione una cohorte para ver sus tesis..."
)

# --- PASO 2: Seleccionar la Tesis (si se seleccionó una cohorte) ---
if cohorte_seleccionada_nombre:
    st.divider()
    st.header("2. Seleccione la Tesis")
    
    cohorte_id_seleccionada = mapa_cohortes[cohorte_seleccionada_nombre]
    tesis_filtradas = df_tesis[df_tesis['cohorte_id'] == cohorte_id_seleccionada].copy()

    if tesis_filtradas.empty:
        st.info("Esta cohorte no tiene tesis registradas.")
        st.stop()

    tesis_filtradas['display'] = tesis_filtradas.apply(
        lambda row: f"{row['alumno_nombre']} - {row['titulo'][:50]}...", axis=1
    )
    
    tesis_seleccionada_display = st.selectbox(
        "Tesis",
        options=tesis_filtradas['display'],
        index=None,
        placeholder="Busque por nombre de alumno o título de tesis..."
    )

    # --- PASO 3: Asignar Tutores (si se seleccionó una tesis) ---
    if tesis_seleccionada_display:
        st.divider()
        st.header("3. Asigne los Tutores")

        tesis_id_seleccionada = tesis_filtradas[tesis_filtradas['display'] == tesis_seleccionada_display]['id'].iloc[0]
        
        try:
            tutores_actuales_res = supabase.table("tesis_tutores").select("tutor_id").eq("tesis_id", tesis_id_seleccionada).execute()
            tutores_actuales_ids = [item['tutor_id'] for item in tutores_actuales_res.data]
        except APIError:
            tutores_actuales_ids = []

        st.info(f"Modifique la selección de tutores para la tesis seleccionada.")

        opciones_tutores = df_tutores.set_index('id')['nombre_completo'].to_dict()
        
        ids_tutores_seleccionados = st.multiselect(
            "Tutores Asignados",
            options=opciones_tutores.keys(),
            format_func=lambda id: opciones_tutores.get(id, "Tutor no encontrado"),
            default=tutores_actuales_ids
        )

        if st.button("💾 Guardar Asignación", type="primary"):
            guardar_asignacion(tesis_id_seleccionada, ids_tutores_seleccionados)