import hashlib
import os
import sys
import uuid
import streamlit as st
from dotenv import load_dotenv

# Ensure the `constitucionbot` package can be imported when running from workspace root.
ROOT_DIR = os.path.dirname(__file__)
CONSTITUCIONBOT_PATH = os.path.join(ROOT_DIR, "constitucionbot")
if CONSTITUCIONBOT_PATH not in sys.path:
    sys.path.insert(0, CONSTITUCIONBOT_PATH)

load_dotenv(os.path.join(CONSTITUCIONBOT_PATH, ".env"))

from pipeline.chatbot_pipeline import ChatbotPipeline

@st.cache_resource
def get_pipeline() -> ChatbotPipeline:
    return ChatbotPipeline()


def get_user_id(api_key: str) -> str:
    conversation_id = st.session_state.get("conversation_id", "default")
    value = f"{api_key}:{conversation_id}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


st.markdown(
    """
    <style>
    .stApp,
    [data-testid="stAppViewContainer"] { background: var(--background-color); color: var(--text-color); }
    [data-testid="stHeader"] { background: var(--background-color); }
    [data-testid="stSidebar"] { background: var(--secondary-background-color); border-right: 1px solid var(--border-color, rgba(128, 128, 128, 0.25)); }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 { color: var(--text-color); }
    [data-testid="stSidebar"] button { border-radius: 6px; min-height: 2.6rem; }
    [data-testid="stSidebar"] button[kind="secondary"] {
        background: transparent; border-color: transparent; color: var(--text-color);
    }
    [data-testid="stSidebar"] button[kind="secondary"]:hover {
        border-color: var(--primary-color); color: var(--primary-color);
    }
    [data-testid="stSidebar"] button[kind="primary"] {
        background: var(--primary-color); border-color: var(--primary-color); color: var(--primary-text-color, #ffffff);
    }
    [data-testid="stSidebar"] button[kind="primary"]:hover {
        filter: brightness(0.9);
    }
    .home-kicker { color: var(--primary-color); font-size: 0.78rem; font-weight: 750; letter-spacing: 0.12em; text-transform: uppercase; }
    .home-title { color: #a8c686; font-size: 3.4rem; font-weight: 800; line-height: 1.05; max-width: 50rem; margin: 0.25rem 0 0.8rem; }
    .home-copy { color: var(--text-color); opacity: 0.75; font-size: 1.1rem; line-height: 1.6; max-width: 40rem; }
    .home-rule { border-top: 4px solid var(--primary-color); max-width: 5rem; margin: 2.4rem 0 1.5rem; }
    .home-panel { border-top: 1px solid var(--border-color, rgba(128, 128, 128, 0.25)); padding-top: 1rem; min-height: 8rem; }
    .home-panel-title { color: #a8c686; font-size: 1.05rem; font-weight: 750; margin-bottom: 0.5rem; }
    .about-intro { font-size: 1.25rem; line-height: 1.65; max-width: 52rem; }
    .about-link { color: #a8c686 !important; font-weight: 750; text-decoration: none; }
    .about-link:hover { text-decoration: underline; }
    .home-accent { color: #a8c686; font-weight: 750; }
    .home-mode-label { color: var(--text-color); }
    .home-mode { color: #a8c686; font-size: 1.3rem; font-weight: 750; }
    .sidebar-brand { color: #a8c686; margin-bottom: 0.2rem; }
    button[kind="primary"] { background: var(--primary-color); border-color: var(--primary-color); color: var(--primary-text-color, #ffffff); }
    button[kind="primary"]:hover { filter: brightness(0.9); }
    button[kind="primary"],
    [data-testid="stBaseButton-primary"] {
        background: #dce5c9 !important;
        color: #26311f !important;
        border: 1px solid #68784f !important;
    }
    button[kind="primary"] *,
    [data-testid="stBaseButton-primary"] * {
        color: #26311f !important;
    }
    button[kind="primary"]:hover,
    [data-testid="stBaseButton-primary"]:hover {
        background: #c8d6ac !important;
        border-color: #4f603b !important;
        color: #1c2617 !important;
    }
    [data-testid="stMetricValue"], [data-testid="stMarkdownContainer"], label { color: var(--text-color); }
    [data-testid="stCaptionContainer"], [data-testid="stMetricLabel"] { color: var(--text-color); opacity: 0.7; }
    hr { border-color: var(--border-color, rgba(128, 128, 128, 0.25)); }
    </style>
    """,
    unsafe_allow_html=True,
)


if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = str(uuid.uuid4())

views = {
    "home": "Home",
    "chat": "Chat",
    "about": "Sobre el proyecto",
}
view_key = st.query_params.get("view", "home")
if view_key not in views:
    view_key = "home"

with st.sidebar:
    st.markdown('<h2 class="sidebar-brand">Alberdi Bot</h2>', unsafe_allow_html=True)
    st.caption("Asistente constitucional")
    selected_view = view_key
    for key, label in views.items():
        if st.button(
            label,
            key=f"nav_{key}",
            type="primary" if key == view_key else "secondary",
            use_container_width=True,
        ):
            st.query_params["view"] = key
            st.rerun()

    st.write("")
    if st.button("+ Crear chat nuevo", type="primary", use_container_width=True):
        st.session_state.messages = []
        st.session_state.conversation_id = str(uuid.uuid4())
        st.query_params["view"] = "chat"
        st.rerun()

    groq_api_key = st.text_input(
        "API key de Groq",
        value=os.getenv("API_KEY_GROQ", ""),
        type="password",
    )

if selected_view == "home":
    st.markdown(
        """
        <style>
        </style>
        <div class="home-kicker">Constitución Nacional Argentina</div>
        <div class="home-title">La Constitución, más cerca de la pregunta.</div>
        <div class="home-copy">Alberdi Bot busca el contenido relevante en la base documental y lo convierte en una respuesta clara, con contexto y sin rodeos.</div>
        <div class="home-rule"></div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="home-mode-label">Modo</div><div class="home-mode">RAG documental</div>', unsafe_allow_html=True)
    st.markdown("<div class=\"home-rule\"></div>", unsafe_allow_html=True)
    st.divider()
    feature_one, feature_two, feature_three = st.columns(3)
    feature_one.markdown('<div class="home-panel"><div class="home-panel-title">Consulta enfocada</div>Preguntá en lenguaje natural y recibí una respuesta contextualizada.</div>', unsafe_allow_html=True)
    feature_two.markdown('<div class="home-panel"><div class="home-panel-title">Chats separados</div>Cada conversación mantiene su propio historial.</div>', unsafe_allow_html=True)
    feature_three.markdown('<div class="home-panel"><div class="home-panel-title">Base documental</div>Las respuestas se generan a partir del material indexado.</div>', unsafe_allow_html=True)
elif selected_view == "about":
    st.markdown('<h1 class="home-title">Sobre el proyecto</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="about-intro">Alberdi Bot combina recuperación semántica de documentos con un modelo de lenguaje para explorar la Constitución Nacional y material jurídico relacionado.</p>',
        unsafe_allow_html=True,
    )
    st.markdown("<div class=\"home-rule\"></div>", unsafe_allow_html=True)
    about_col, docs_col = st.columns(2, gap="large")
    with about_col:
        st.markdown(
            '<div class="home-panel"><div class="home-panel-title">Código fuente</div>El proyecto es abierto y su implementación puede consultarse en el repositorio de GitHub.<br><br><a class="about-link" href="https://github.com/alonns04/alberdi-bot" target="_blank">Ver repositorio en GitHub ↗</a></div>',
            unsafe_allow_html=True,
        )
    with docs_col:
        st.markdown(
            '<div class="home-panel"><div class="home-panel-title">Documentos de trabajo</div>Accedé a la carpeta con los PDFs utilizados y preparados para el procesamiento documental.<br><br><a class="about-link" href="https://github.com/alonns04/alberdi-bot/tree/main/constitucionbot/src/pdf" target="_blank">Ver PDFs preprocesados ↗</a></div>',
            unsafe_allow_html=True,
        )
    st.divider()
    st.markdown("**Cómo funciona**")
    st.write("La aplicación recupera fragmentos relevantes de la base vectorial, los incorpora como contexto y genera una respuesta con Groq. El historial se mantiene separado por conversación.")
else:
    st.markdown('<h1 class="home-title">Alberdi</h1>', unsafe_allow_html=True)
    st.write('“La Constitución es la ley de las leyes”')

    if not groq_api_key.strip():
        st.info("Agregá tu API key de Groq en la barra lateral para continuar.", icon="🗝️")
    else:
        user_id = get_user_id(groq_api_key.strip())

        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if prompt := st.chat_input("Escribí tu pregunta sobre la Constitución..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                try:
                    result = get_pipeline().process(
                        prompt,
                        user_id=user_id,
                        api_key=groq_api_key.strip(),
                    )
                    answer = result.get("answer", "No se obtuvo respuesta.")
                    st.markdown(answer)

                except RuntimeError as exc:
                    if str(exc) == "INVALID_API_KEY":
                        answer = "La API key de Groq no es válida. Cambiala en la barra lateral."
                        st.error(answer)
                    else:
                        answer = f"Error al procesar la consulta: {exc}"
                        st.error(answer)

                except Exception as exc:
                    answer = f"Error al procesar la consulta: {exc}"
                    st.error(answer)

            st.session_state.messages.append({"role": "assistant", "content": answer})
