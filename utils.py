# utils.py
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client
import os

# --- CONEXIÓN A SUPERBASE ---
# Usa @st.cache_resource para la conexión, asegurando que se cree una sola vez por sesión de usuario.
# Esto es crucial para el rendimiento.
@st.cache_resource
def init_connection() -> Client:
    """
    Inicializa y devuelve el cliente de Supabase.
    Lee las credenciales desde el archivo .env.
    """
    load_dotenv()  # Carga las variables del archivo .env
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    # Validamos que las credenciales existan
    if not url or not key:
        st.error("Error: Credenciales de Supabase no encontradas. Asegúrate de que tu archivo .env está configurado correctamente.")
        # Detiene la ejecución de la app si no hay credenciales.
        st.stop()
        
    return create_client(url, key)

# --- CONSULTAS A LA BASE DE DATOS ---
# Usa @st.cache_data para las consultas. Si los argumentos no cambian, Streamlit
# devolverá el resultado cacheado en lugar de volver a ejecutar la consulta.
# El parámetro 'ttl' (Time To Live) define cuánto tiempo (en segundos) la caché es válida.
@st.cache_data(ttl=600) # Cachea los resultados por 10 minutos
def run_query(_supabase_client: Client, table_name: str) -> pd.DataFrame:
    """
    Ejecuta una consulta SELECT * en una tabla específica y devuelve los resultados
    como un DataFrame de Pandas.
    
    Args:
        _supabase_client: El cliente de Supabase conectado.
        table_name: El nombre de la tabla a consultar.
    
    Returns:
        Un DataFrame de Pandas con los datos de la tabla.
    """
    try:
        # La función select("*") obtiene todas las columnas. execute() corre la consulta.
        response = _supabase_client.table(table_name).select("*").execute()
        
        # Los datos vienen en el atributo 'data' de la respuesta.
        # Si no hay datos, devolvemos un DataFrame vacío para evitar errores.
        if not response.data:
            return pd.DataFrame()
            
        return pd.DataFrame(response.data)
    except Exception as e:
        # Mostramos un error amigable en la app si la consulta falla.
        st.error(f"Error al consultar la tabla '{table_name}': {e}")
        return pd.DataFrame()
    
    # En utils.py, al final del archivo

def add_logout_button():
    """Añade un botón de logout en la barra lateral."""
    if 'user_logged_in' in st.session_state and st.session_state['user_logged_in']:
        if st.sidebar.button("Cerrar Sesión"):
            # Limpiamos todo el session_state para un logout completo
            for key in st.session_state.keys():
                del st.session_state[key]
            # Redirigimos a la página principal (que ahora es el login)
            st.rerun()