# pages/5_📚_ABM_Cohortes.py
import streamlit as st
import pandas as pd
from utils import init_connection, add_logout_button
from postgrest import APIError
import time

st.set_page_config(page_title="ABM de Cohortes", page_icon="📚", layout="wide")
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
def cargar_cohortes():
    try:
        response = supabase.table("cohortes").select("*").order("fecha_inicio", desc=True).execute()
        df = pd.DataFrame(response.data)
        # Aseguramos el tipo de dato para la columna de fecha
        if 'fecha_inicio' in df.columns:
            df['fecha_inicio'] = pd.to_datetime(df['fecha_inicio']).dt.date
        return df
    except APIError as e:
        st.error(f"Error al cargar cohortes: {e.message}"); return pd.DataFrame()

def guardar_cambios_cohortes(original_df, editado_df):
    original_df.set_index('id', inplace=True, drop=False)
    nuevas_filas = editado_df[editado_df['id'].isna()]
    editado_df_existente = editado_df.dropna(subset=['id']).set_index('id', drop=False)
    eliminados_ids = list(set(original_df.index) - set(editado_df_existente.index))
    modificaciones = [row.to_dict() for id, row in editado_df_existente.iterrows() if id in original_df.index and not row.equals(original_df.loc[id])]
    columnas_insercion = ['nombre', 'descripcion', 'fecha_inicio'] # <-- Nueva columna
    nuevos_registros = nuevas_filas[columnas_insercion].to_dict('records')
    nuevos_registros = [r for r in nuevos_registros if r.get('nombre') and pd.notna(r.get('fecha_inicio'))]

    if not any([eliminados_ids, modificaciones, nuevos_registros]):
        st.toast("✅ No hay cambios que guardar."); return

    progress_bar = st.progress(0, text="Iniciando guardado...")
    try:
        if eliminados_ids:
            progress_bar.progress(10, text=f"Eliminando {len(eliminados_ids)} cohorte(s)...")
            supabase.table("cohortes").delete().in_("id", eliminados_ids).execute()
        if modificaciones:
            progress_bar.progress(40, text=f"Actualizando {len(modificaciones)} cohorte(s)...")
            for item in modificaciones:
                cohorte_id = item.pop('id'); item.pop('fecha_creacion', None)
                item['fecha_inicio'] = str(item.get('fecha_inicio')) # Convertir fecha a string para la DB
                supabase.table("cohortes").update(item).eq("id", cohorte_id).execute()
        if nuevos_registros:
            progress_bar.progress(70, text=f"Agregando {len(nuevos_registros)} cohorte(s)...")
            supabase.table("cohortes").insert(nuevos_registros).execute()
        
        st.success("¡Todos los cambios han sido guardados en la base de datos!")
        time.sleep(1); st.cache_data.clear(); st.rerun()
    except APIError as e:
        st.error(f"❌ Error al guardar los cambios: {e.message}")
    finally:
        progress_bar.empty()

st.title("📚 Gestión de Cohortes")
st.write("Gestiona las cohortes, incluyendo su **fecha de inicio**, que es clave para calcular los plazos de las tesis.")
if 'cohortes_df' not in st.session_state:
    st.session_state.cohortes_df = cargar_cohortes()

with st.form(key="data_editor_form_cohortes"):
    edited_df = st.data_editor(
        st.session_state.cohortes_df, key="cohortes_editor", num_rows="dynamic", use_container_width=True,
        column_config={
            "id": None, "fecha_creacion": None,
            "nombre": st.column_config.TextColumn("Nombre de la Cohorte", required=True),
            # <<< CAMBIO CLAVE >>>
            "fecha_inicio": st.column_config.DateColumn("Fecha de Inicio", help="Fecha oficial de inicio de la cohorte.", required=True),
            "descripcion": st.column_config.TextColumn("Descripción"),
        },
        hide_index=True,
        column_order=("nombre", "fecha_inicio", "descripcion")
    )
    submitted = st.form_submit_button("💾 Guardar Cambios")
if submitted:
    guardar_cambios_cohortes(st.session_state.cohortes_df.copy(), edited_df)
    if 'cohortes_df' in st.session_state: del st.session_state.cohortes_df