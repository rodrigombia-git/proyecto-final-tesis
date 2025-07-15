# App.py
import streamlit as st
import bcrypt
from utils import init_connection
import time

# Usamos una configuración de página inicial simple
st.set_page_config(page_title="Gestor de Tesis", page_icon="🔑", layout="centered")

supabase = init_connection()

# --- Funciones de Verificación ---
def check_password(email, password):
    try:
        user = supabase.table("usuarios").select("password_hash").eq("email", email).single().execute().data
        if not user or not user.get("password_hash"): return False
        password_bytes = password.encode('utf-8')
        hashed_password_bytes = user["password_hash"].encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_password_bytes)
    except Exception:
        return False

# --- LÓGICA DE ROUTING ---

# Si el usuario NO ha iniciado sesión, muestra el formulario de login.
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
                    # Almacenamos el email para saludar al usuario
                    st.session_state['user_email'] = email
                    # Forzamos la recarga de la página
                    st.rerun() 
                else:
                    st.error("Email o contraseña incorrectos.")

# Si el usuario SÍ ha iniciado sesión, muestra la bienvenida y el redirect.
else:
    st.title(f"¡Bienvenido, {st.session_state['user_email']}!")
    st.success("Sesión iniciada correctamente.")
    st.write("Serás redirigido al Dashboard en un momento...")
    
    # Este es el redirect automático
    time.sleep(1) # Pequeña pausa para que el usuario pueda leer el mensaje
    st.switch_page("pages/1_📊_Dashboard.py")