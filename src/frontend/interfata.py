import os
import shutil
import subprocess
import time
import sys
import requests
import streamlit as st

os.environ["FLAGS_enable_pir_api"] = "0"
os.environ["FLAGS_use_mkldnn"] = "0"

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.frontend.views.autentificare import (  # noqa: E402
    clear_cookie_and_reload,
    ensure_auth_schema,
    get_user_by_id,
    initialize_session_state,
    render_auth_page,
)

st.set_page_config(page_title="MEDICODE", page_icon="🏥", layout="centered")


@st.cache_resource(show_spinner=False)
def initializare_automata_ai_local():
    """Verifică și configurează automat Ollama și modelul MedGemma (Rulează o singură dată)."""
    if not shutil.which("ollama"):
        st.error("❌ Serviciul Ollama nu a fost găsit pe acest calculator!")
        st.info("Te rugăm să descarci și să instalezi Ollama de pe https://ollama.com")
        st.stop()

    try:
        requests.get("http://localhost:11434", timeout=2)
    except requests.exceptions.ConnectionError:
        with st.spinner("🚀 Pornim serviciul local Ollama în fundal..."):
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            time.sleep(5)

    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=5)
        if r.status_code == 200:
            modele_instalate = [m["name"] for m in r.json().get("models", [])]
            model_cautat = "hf.co/gguf-org/medgemma-1.5-4b-it-gguf:Q4_0"
            are_medgemma = any("medgemma" in m.lower() for m in modele_instalate)

            if not are_medgemma:
                with st.spinner("📥 Descarcăm modelul medical MedGemma (2.8 GB)..."):
                    subprocess.run(
                        ["ollama", "pull", model_cautat], stdout=subprocess.DEVNULL
                    )
    except Exception as e:
        print(f"Avertisment la inițializarea AI-ului: {e}")


initializare_automata_ai_local()

st.markdown(
    """
    <style>
    div[data-testid="InputInstructions"] { display: none !important; }
    input::-ms-reveal, input::-ms-clear, input::-webkit-credentials-auto-fill-button { display: none !important; }
    [data-testid="stSidebarNav"] { display: none !important; }
    [data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] {
        background-color: transparent;
        border-radius: 12px !important;
        margin: 6px 0px !important;
        padding: 12px 16px !important;
        text-decoration: none !important;
        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1) !important;
        border: 1px solid transparent;
        display: flex;
        align-items: center;
    }
    [data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]:hover {
        transform: translateX(6px);
        background-color: rgba(255, 75, 75, 0.08) !important;
        border-color: rgba(255, 75, 75, 0.3);
        box-shadow: 0 4px 12px rgba(255, 75, 75, 0.1) !important;
    }
    [data-testid="stSidebar"] [data-testid="stPageLink-NavLink"][data-active="true"],
    [data-testid="stSidebar"] [data-testid="stPageLink-NavLink"][aria-current="page"] {
        background: linear-gradient(90deg, #ff4b4b 0%, #ff6b6b 100%) !important;
        box-shadow: 0 4px 15px rgba(255, 75, 75, 0.3) !important;
        border: none !important;
        transform: scale(1.02);
    }
    [data-testid="stSidebar"] [data-testid="stPageLink-NavLink"][data-active="true"] p,
    [data-testid="stSidebar"] [data-testid="stPageLink-NavLink"][aria-current="page"] p {
        color: white !important;
        font-weight: 600 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

pagina_evaluare = st.Page(
    "views/evaluare.py", title="Încărcare & evaluare", icon="📄", url_path="evaluare"
)
pagina_istoric = st.Page(
    "views/istoric.py", title="Istoric medical", icon="📈", url_path="istoric"
)
pagina_profil = st.Page(
    "views/profil.py", title="Profilul meu", icon="⚙️", url_path="profil"
)
pagina_login = st.Page(
    render_auth_page, title="Autentificare", icon="🔒", url_path="login"
)

ensure_auth_schema()
initialize_session_state()

if st.session_state.authenticated and st.session_state.current_user_id is not None:
    if not st.session_state.current_user:
        date_utilizator = get_user_by_id(st.session_state.current_user_id)
        if date_utilizator:
            st.session_state.current_user = dict(date_utilizator)
        else:
            clear_cookie_and_reload()

    current_user = st.session_state.current_user
    pagini_autentificate = [pagina_evaluare, pagina_istoric, pagina_profil]

    nav = st.navigation(pagini_autentificate, position="hidden")

    st.sidebar.markdown("### 👤 Utilizator curent")
    st.sidebar.success(
        f"{current_user.get('prenume', '')} {current_user.get('nume', '')}".strip()
    )
    st.sidebar.markdown("---")

    st.sidebar.markdown("### 🗺️ Meniu")
    for pagina in pagini_autentificate:
        st.sidebar.page_link(pagina, label=pagina.title, icon=pagina.icon)

    st.sidebar.markdown("---")
    if st.sidebar.button("Deconectare", type="secondary"):
        clear_cookie_and_reload()

    nav.run()
else:
    nav = st.navigation([pagina_login], position="hidden")
    nav.run()
