# utils.py (Versión Corregida)
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client
import os

@st.cache_resource
def init_connection() -> Client:
    """
    Inicializa y devuelve el cliente de Supabase.
    Lee las credenciales desde las variables de entorno.
    """
    # Esta línea es solo para desarrollo local, no afecta al despliegue.
    load_dotenv()
    
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    # Si las credenciales no se encuentran, mostramos un error más claro.
    if not url or not key:
        st.error(
            "Error: Credenciales de Supabase no encontradas. "
            "Asegúrate de que tus 'Secrets' están configurados correctamente en la configuración de la app en Streamlit Cloud. "
            "Localmente, verifica tu archivo .env."
        )
        st.stop()
        
    return create_client(url, key)

def add_logout_button():
    """Añade un botón de logout en la barra lateral."""
    if 'user_logged_in' in st.session_state and st.session_state['user_logged_in']:
        if st.sidebar.button("Cerrar Sesión"):
            for key in st.session_state.keys():
                del st.session_state[key]
            st.rerun()