
# # pages/4_⚙️_ABM_Parametros.py
import streamlit as st
import pandas as pd
from utils import init_connection, add_logout_button
from postgrest import APIError
import time

st.set_page_config(page_title="Gestión de Parámetros", page_icon="⚙️", layout="wide")
supabase = init_connection()

# --- BLOQUE GUARDIÁN DE SEGURIDAD ---
if 'user_logged_in' not in st.session_state or not st.session_state['user_logged_in']:
    st.warning("Debes iniciar sesión para acceder a esta página.")
    st.page_link("App.py", label="Ir a la página de Login", icon="🔑")
    st.stop()
# --- FIN DEL BLOQUE GUARDIÁN ---

# --- LLAMADA AL BOTÓN DE LOGOUT ---
add_logout_button() # <-- Llamada

@st.cache_data(ttl=60)
def cargar_parametros():
    columnas_esperadas = ['id', 'clave', 'valor', 'descripcion', 'fecha_modificacion']
    try:
        response = supabase.table("parametros").select("*").order("clave").execute()
        df = pd.DataFrame(response.data)
        if df.empty:
            return pd.DataFrame(columns=columnas_esperadas)
        return df
    except APIError as e:
        st.error(f"Error al cargar parámetros: {e.message}")
        return pd.DataFrame(columns=columnas_esperadas)

def guardar_cambios_parametros(original_df, editado_df):
    """Compara los dataframes y aplica cambios (altas, bajas, modificaciones) a la base de datos de forma robusta."""
    
    # Convertimos los dataframes a diccionarios para facilitar la comparación
    original_dict = {rec['id']: rec for rec in original_df.to_dict('records')}
    editado_dict = {rec['id']: rec for rec in editado_df.to_dict('records') if pd.notna(rec.get('id'))}
    
    # 1. Detectar Eliminaciones
    ids_originales = set(original_dict.keys())
    ids_editados = set(editado_dict.keys())
    ids_eliminados = list(ids_originales - ids_editados)

    # 2. Detectar Modificaciones
    modificaciones = []
    for id, reg_editado in editado_dict.items():
        if id in original_dict:
            reg_original = original_dict[id]
            # Comparamos campo por campo los valores que nos interesan
            if (reg_editado.get('valor') != reg_original.get('valor') or 
                reg_editado.get('descripcion') != reg_original.get('descripcion')):
                # La clave no debe ser modificable, la usamos para el WHERE
                modificaciones.append({'clave': reg_original['clave'], 'valor': reg_editado['valor'], 'descripcion': reg_editado['descripcion']})
    
    # 3. Detectar Adiciones
    nuevas_filas = editado_df[pd.isna(editado_df['id'])]
    # Nos aseguramos de que los campos requeridos no estén vacíos
    nuevos_registros = [
        {'clave': r['clave'], 'valor': r['valor'], 'descripcion': r.get('descripcion')}
        for r in nuevas_filas.to_dict('records')
        if r.get('clave') and r.get('valor')
    ]

    if not any([ids_eliminados, modificaciones, nuevos_registros]):
        st.toast("✅ No se detectaron cambios válidos para guardar."); return

    progress_bar = st.progress(0, text="Guardando cambios...")
    try:
        if ids_eliminados:
            progress_bar.progress(10, text=f"Eliminando {len(ids_eliminados)} parámetro(s)...")
            supabase.table("parametros").delete().in_("id", ids_eliminados).execute()
        
        if modificaciones:
            progress_bar.progress(40, text=f"Actualizando {len(modificaciones)} parámetro(s)...")
            for item in modificaciones:
                clave_original = item.pop('clave')
                supabase.table("parametros").update(item).eq("clave", clave_original).execute()

        if nuevos_registros:
            progress_bar.progress(70, text=f"Agregando {len(nuevos_registros)} parámetro(s)...")
            supabase.table("parametros").insert(nuevos_registros).execute()

        st.success("¡Parámetros guardados exitosamente!")
        time.sleep(1); st.cache_data.clear(); st.rerun()

    except APIError as e:
        st.error(f"❌ Error al guardar: {e.message}")
    finally:
        progress_bar.empty()

st.title("⚙️ Gestión de Parámetros del Sistema")
st.write("Gestiona los parámetros globales. **La 'clave' no debe modificarse una vez creada.**")

if 'parametros_df' not in st.session_state:
    st.session_state.parametros_df = cargar_parametros()

with st.form(key="form_parametros"):
    edited_df = st.data_editor(
        st.session_state.parametros_df.copy(), # Usamos una copia para evitar mutaciones inesperadas
        key="parametros_editor",
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "id": None,
            "clave": st.column_config.TextColumn("Clave", help="Identificador único. No cambiar una vez creado.", required=True),
            "valor": st.column_config.TextColumn("Valor", required=True),
            "descripcion": st.column_config.TextColumn("Descripción", width="large"),
            "fecha_modificacion": st.column_config.DatetimeColumn("Última Modificación", disabled=True, format="YYYY-MM-DD HH:mm")
        },
        hide_index=True
    )
    submitted = st.form_submit_button("💾 Guardar Cambios")

if submitted:
    guardar_cambios_parametros(st.session_state.parametros_df, edited_df)
    if 'parametros_df' in st.session_state: del st.session_state.parametros_df