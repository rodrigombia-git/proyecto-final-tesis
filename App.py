# App.py (Versión de Prueba Quirúrgica)
import streamlit as st
import bcrypt
from utils import init_connection
import time

st.set_page_config(page_title="Gestor de Tesis", page_icon="🔑", layout="centered")

# --- NO HAY NINGUNA CONEXIÓN A LA BASE DE DATOS AQUÍ ---

def check_password(email, password):
    # La conexión se intenta crear JUSTO AHORA, cuando se necesita.
    supabase = init_connection() # <-- CAMBIO CLAVE
    try:
        user = supabase.table("usuarios").select("password_hash").eq("email", email).single().execute().data
        if not user or not user.get("password_hash"): return False
        password_bytes = password.encode('utf-8')
        hashed_password_bytes = user["password_hash"].encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_password_bytes)
    except Exception as e:
        st.error(f"Error de base de datos: {e}")
        return False

# El resto del código de la lógica de la página no cambia.
if 'user_logged_in' not in st.session_state or not st.session_state['user_logged_in']:
    st.title("🔑 Acceso al Sistema de Gestión de Tesis")
    
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Contraseña", type="password")
        submitted = st.form_submit_button("Entrar")

        if submitted:
            with st.spinner("Verificando..."):
                if check_password(email, password):
                    st.session_state['user_logged_in'] = True
                    st.session_state['user_email'] = email
                    st.rerun() 
                else:
                    st.error("Email o contraseña incorrectos.")
else:
    st.title(f"¡Bienvenido, {st.session_state['user_email']}!")
    st.success("Sesión iniciada correctamente.")
    st.write("Serás redirigido al Dashboard en un momento...")
    
    time.sleep(1)
    st.switch_page("pages/1_Dashboard.py")