import datetime
import hashlib
import os
import secrets
import sqlite3
import streamlit as st
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.backend.db.db_connection import (  # noqa: E402
    DatabaseConnection,
    get_database_path,
) 

try:
    from streamlit_cookies_controller import CookieController  # type: ignore

    # Adăugăm un "key" constant pentru a nu reseta componenta la refresh
    cookie_controller = CookieController(key="medicode_cookies")
except ImportError:
    CookieController = None  # type: ignore
    cookie_controller = None


st.set_page_config(page_title="MEDICODE", page_icon="🏥", layout="centered")

# --- CSS PENTRU ASCUNDEREA OPȚIUNII 'SELECT ALL' LA NIVEL GLOBAL ---
st.markdown(
    """
    <style>
    /* Ascunde instrucțiunile */
    div[data-testid="InputInstructions"] {
        display: none !important;
    }

    /* Ascunde Ochiul Parolei din Browser */
    input::-ms-reveal,
    input::-ms-clear,
    input::-webkit-credentials-auto-fill-button {
        display: none !important;
    }
    
    /* Ascundem meniul nativ complet (deoarece noi îl construim manual jos) */
    [data-testid="stSidebarNav"] {
        display: none !important;
    }

    /* Design pentru link-urile generate de st.page_link */
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

    /* Efect de hover: Butonul glisează ușor la dreapta și se colorează */
    [data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]:hover {
        transform: translateX(6px);
        background-color: rgba(255, 75, 75, 0.08) !important;
        border-color: rgba(255, 75, 75, 0.3);
        box-shadow: 0 4px 12px rgba(255, 75, 75, 0.1) !important;
    }

    /* Stilul pentru PAGINA ACTIVĂ (cea pe care te afli) */
    [data-testid="stSidebar"] [data-testid="stPageLink-NavLink"][data-active="true"],
    [data-testid="stSidebar"] [data-testid="stPageLink-NavLink"][aria-current="page"] {
        background: linear-gradient(90deg, #ff4b4b 0%, #ff6b6b 100%) !important;
        box-shadow: 0 4px 15px rgba(255, 75, 75, 0.3) !important;
        border: none !important;
        transform: scale(1.02);
    }

    /* Asigurăm că iconița și textul paginii active sunt albe pentru contrast maxim */
    [data-testid="stSidebar"] [data-testid="stPageLink-NavLink"][data-active="true"] p,
    [data-testid="stSidebar"] [data-testid="stPageLink-NavLink"][aria-current="page"] p {
        color: white !important;
        font-weight: 600 !important;
    }
    
    </style>
    """,
    unsafe_allow_html=True,
)

PBKDF2_ITERATIONS = 120_000


# ==========================================
# GESTIONAREA COOKIE-URILOR
# ==========================================
def set_cookie_and_reload(user_id):
    st.session_state.logout_requested = False
    st.session_state.authenticated = True
    st.session_state.current_user_id = int(user_id)

    user_data = get_user_by_id(user_id)
    if user_data:
        st.session_state.current_user = dict(user_data)

    # Salvăm ID-ul într-un flag pentru ca funcția de inițializare să scrie cookie-ul în siguranță
    # la următoarea randare (ca să nu fie ucis de rerun)
    st.session_state.pending_cookie = user_id

    st.rerun()  # Folosim rerun, NU switch_page


def clear_cookie_and_reload():
    """Deconectare nativă folosind starea Streamlit, fără JavaScript."""
    # Resetăm starea internă pentru a intra pe modul "deconectat"
    st.session_state.authenticated = False
    st.session_state.current_user_id = None
    st.session_state.current_user = None
    st.session_state.page = "📄 Încărcare & Evaluare"
    st.query_params.clear()

    # Activăm scutul: îi spune aplicației să șteargă cookie-ul imediat după repornire
    st.session_state.clear_cookie_on_next_run = True

    # Repornim instantaneu. Tranziția va fi invizibilă și fluidă.
    st.rerun()


def get_saved_user_id():
    """Citește cookie-ul din headerele HTTP sau din componentă, ignorând erorile de inițializare."""
    if hasattr(st, "context") and hasattr(st.context, "cookies"):
        cookies = st.context.cookies
        if "medicode_user_id" in cookies:
            val = cookies["medicode_user_id"]
            if val and str(val).strip() not in ["", "None"]:
                return val

    if cookie_controller:
        try:
            saved_user_id = cookie_controller.get("medicode_user_id")
            if saved_user_id and str(saved_user_id).strip() not in ["", "None"]:
                return saved_user_id
        except TypeError:
            # Componenta web nu s-a sincronizat încă (dicționarul de cookie-uri este None)
            pass
        except Exception:
            # Captăm orice altă eroare de la controller pentru a nu bloca aplicația
            pass

    return None


# ==========================================
# BAZA DE DATE & SCHEMĂ
# ==========================================
def get_db_connection():
    db_instance = DatabaseConnection()
    conn = db_instance.connection
    conn.row_factory = sqlite3.Row
    return conn


def ensure_auth_schema():
    db_path = get_database_path()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    try:
        tabela_exista = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='Utilizatori'"
        ).fetchone()

        if tabela_exista:
            existing_columns = {
                row[1]
                for row in conn.execute("PRAGMA table_info(Utilizatori)").fetchall()
            }
            if "parola_hash" not in existing_columns:
                conn.execute("ALTER TABLE Utilizatori ADD COLUMN parola_hash TEXT")

            # Schema upgrade pentru gestionarea upload-urilor duplicate
            analize_exista = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='Analize'"
            ).fetchone()
            if analize_exista:
                analize_columns = {
                    row[1]
                    for row in conn.execute("PRAGMA table_info(Analize)").fetchall()
                }
                if "upload_hash" not in analize_columns:
                    conn.execute("ALTER TABLE Analize ADD COLUMN upload_hash TEXT")
                if "finalizata" not in analize_columns:
                    conn.execute(
                        "ALTER TABLE Analize ADD COLUMN finalizata INTEGER DEFAULT 0"
                    )
                conn.execute(
                    "CREATE UNIQUE INDEX IF NOT EXISTS idx_analize_upload_hash ON Analize(id_utilizator, upload_hash)"
                )

        conn.execute("""
            CREATE TABLE IF NOT EXISTS Afectiuni (
                nume_afectiune TEXT PRIMARY KEY,
                descriere_generala TEXT
            )
            """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS Utilizator_Afectiune (
                id_utilizator INTEGER NOT NULL,
                nume_afectiune TEXT NOT NULL,
                status TEXT,
                PRIMARY KEY (id_utilizator, nume_afectiune),
                FOREIGN KEY (id_utilizator) REFERENCES Utilizatori(id_utilizator) ON DELETE CASCADE,
                FOREIGN KEY (nume_afectiune) REFERENCES Afectiuni(nume_afectiune) ON DELETE CASCADE
            )
            """)
        conn.commit()
    except Exception as e:
        print(f"Eroare la inițializarea schemei: {e}")
    finally:
        conn.close()


def hash_password(password):
    derived_key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        b"medicode",
        PBKDF2_ITERATIONS,
    )
    return derived_key.hex()


def verify_password(password, expected_hash):
    calculated_hash = hash_password(password)
    return secrets.compare_digest(calculated_hash, expected_hash)


def get_user_by_email(email):
    conn = get_db_connection()
    return conn.execute(
        "SELECT * FROM Utilizatori WHERE lower(email) = lower(?)",
        (email.strip(),),
    ).fetchone()


def get_user_by_id(user_id):
    conn = get_db_connection()
    return conn.execute(
        "SELECT * FROM Utilizatori WHERE id_utilizator = ?",
        (user_id,),
    ).fetchone()


def register_user(form_data):
    conn = get_db_connection()
    existing_user = conn.execute(
        "SELECT id_utilizator, cnp, email, parola_hash FROM Utilizatori WHERE lower(email) = lower(?)",
        (form_data["email"].strip(),),
    ).fetchone()

    password_hash = hash_password(form_data["parola"])

    if existing_user:
        if existing_user["cnp"] != form_data["cnp"]:
            return (
                False,
                "Există deja un cont cu acest email, dar CNP-ul introdus nu corespunde.",
            )
        if existing_user["parola_hash"]:
            return (
                False,
                "Acest utilizator are deja un cont activ. Te poți conecta direct.",
            )

        user_id = existing_user["id_utilizator"]
        conn.execute(
            "UPDATE Utilizatori SET parola_hash = ? WHERE id_utilizator = ?",
            (password_hash, user_id),
        )
    else:
        try:
            cursor = conn.execute(
                """
                INSERT INTO Utilizatori (cnp, nume, prenume, email, sex, data_nasterii, parola_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    form_data["cnp"].strip(),
                    form_data["nume"].strip(),
                    form_data["prenume"].strip(),
                    form_data["email"].strip(),
                    form_data["sex"],
                    form_data["data_nasterii"],
                    password_hash,
                ),
            )
            user_id = cursor.lastrowid
        except sqlite3.IntegrityError as e:
            message = str(e)
            if "Utilizatori.cnp" in message:
                return False, "CNP-ul introdus este deja asociat unui cont existent."
            if "Utilizatori.email" in message:
                return False, "Emailul introdus este deja asociat unui cont existent."
            return False, "Datele introduse sunt deja folosite în baza de date."

    if "afectiuni" in form_data and form_data["afectiuni"]:
        for afectiune in form_data["afectiuni"]:
            conn.execute(
                "INSERT OR IGNORE INTO Afectiuni (nume_afectiune, descriere_generala) VALUES (?, ?)",
                (afectiune, ""),
            )
            conn.execute(
                """
                INSERT OR IGNORE INTO Utilizator_Afectiune (id_utilizator, nume_afectiune, status)
                VALUES (?, ?, ?)
                """,
                (user_id, afectiune, "Actuală"),
            )

    conn.commit()
    return True, user_id


def login_user(email, password):
    user = get_user_by_email(email)
    if user is None or user["parola_hash"] is None:
        return False, "Nu există un cont activ pentru acest email."
    if not verify_password(password, user["parola_hash"]):
        return False, "Parolă incorectă."
    return True, user["id_utilizator"]


# ==========================================
# INTERFAȚĂ & SESIUNE
# ==========================================
def initialize_session_state():
    # --- 1. Ștergere Cookie Amânată (Logout) ---
    is_logging_out = st.session_state.get("clear_cookie_on_next_run", False)
    if is_logging_out:
        if cookie_controller:
            try:
                cookie_controller.set("medicode_user_id", "", path="/")
            except Exception:
                pass
        st.session_state.clear_cookie_on_next_run = False

    # --- 2. Scriere Cookie Amânată (Login - AICI REZOLVĂM PERSISTENȚA) ---
    if "pending_cookie" in st.session_state:
        if cookie_controller:
            try:
                cookie_controller.set(
                    "medicode_user_id", str(st.session_state.pending_cookie), path="/"
                )
            except Exception:
                pass
        del st.session_state["pending_cookie"]

    # --- 3. Inițializare variabile default ---
    if "logout_requested" not in st.session_state:
        st.session_state.logout_requested = False
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "current_user_id" not in st.session_state:
        st.session_state.current_user_id = None
    if "current_user" not in st.session_state:
        st.session_state.current_user = None
    if "auth_tab_index" not in st.session_state:
        st.session_state.auth_tab_index = 0  # 0 = Conectare, 1 = Înregistrare

    # --- 4. Verificare sesiune activă (Recuperare Cookie) ---
    if not st.session_state.authenticated and not st.session_state.logout_requested:
        if not is_logging_out:
            saved_id = get_saved_user_id()
            if saved_id and str(saved_id).strip() not in ["", "None"]:
                st.session_state.authenticated = True
                st.session_state.current_user_id = int(saved_id)


def render_auth_page():
    st.title("🏥 MEDICODE")
    st.subheader("Autentificare pacient")

    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] { display: none !important; }
        [data-testid="collapsedControl"] { display: none !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    def update_auth_tab():
        """Callback para actualizar el índice de la pestaña de autenticación"""
        if "auth_action" in st.session_state:
            st.session_state.auth_tab_index = (
                0 if st.session_state.auth_action == "Conectare" else 1
            )

    action = st.radio(
        "Alegeți acțiunea:",
        ["Conectare", "Înregistrare"],
        horizontal=True,
        index=st.session_state.auth_tab_index,
        on_change=update_auth_tab,
        key="auth_action",
    )

    if action == "Conectare":
        with st.form("login_form", clear_on_submit=False):
            email = st.text_input("Email", key="login_email")

            parola = st.text_input(
                "Parolă",
                type="password",
                key="login_parola",
            )

            # Adăugăm textul direct sub căsuța de parolă pentru a fi vizibil instant
            st.caption(
                "💡 *Sfat: Apasă tasta ENTER după parolă pentru conectare rapidă, sau folosește butonul de mai jos.*"
            )

            submit_login = st.form_submit_button(
                "Conectează-te", type="primary", key="login_submit"
            )

        if submit_login:
            if not email or not parola:
                st.error("Completează emailul și parola.")
                return

            success, result = login_user(email, parola)
            if success:
                st.session_state.authenticated = True
                st.session_state.current_user_id = result
                st.session_state.current_user = dict(get_user_by_id(result))
                st.session_state.logout_requested = False
                set_cookie_and_reload(result)
            else:
                st.error(result)

    else:
        with st.form("register_form", clear_on_submit=False):
            row1_col1, row1_col2 = st.columns(2)
            nume = row1_col1.text_input("Nume", key="register_nume")
            prenume = row1_col2.text_input("Prenume", key="register_prenume")

            row2_col1, row2_col2 = st.columns(2)
            cnp = row2_col1.text_input("CNP", key="register_cnp")

            data_nasterii = row2_col2.date_input(
                "Data nașterii",
                min_value=datetime.date(1900, 1, 1),
                max_value=datetime.date.today() - datetime.timedelta(days=3 * 365),
                value=None,
                format="DD/MM/YYYY",
                key="register_data_nasterii",
            )

            row3_col1, row3_col2 = st.columns(2)
            sex = row3_col1.selectbox(
                "Sex Biologic",
                ["M", "F"],
                index=None,
                placeholder="Alege o opțiune",
                key="register_sex",
            )
            email = row3_col2.text_input("Email", key="register_email")

            parola = st.text_input("Parolă", type="password", key="register_parola")
            confirma_parola = st.text_input(
                "Confirmă parola", type="password", key="register_confirma_parola"
            )

            afectiuni_predefinite_dict = {
                "Afecțiuni Cardiovasculare": [
                    "Hipertensiune arterială (HTA)",
                    "Boală cardiacă ischemică",
                    "Insuficiență cardiacă cronică",
                ],
                "Afecțiuni Metabolice și Endocrine": [
                    "Diabet zaharat (Tip 1 și Tip 2)",
                    "Obezitate / Sindrom metabolic",
                    "Boli tiroidiene (Hipotiroidism / Hipertiroidism)",
                ],
                "Afecțiuni Respiratorii": [
                    "Astm bronșic",
                    "Boală pulmonară obstructivă cronică (BPOC)",
                ],
                "Afecțiuni Neurologice și Psihice": [
                    "Boala Alzheimer și alte demențe",
                    "Boala Parkinson",
                    "Scleroză multiplă",
                    "Epilepsie",
                    "Tulburări depresive și de anxietate",
                ],
                "Afecțiuni Oncologice": [
                    "Cancer pulmonar",
                    "Cancer colorectal",
                    "Cancer mamar / de prostată",
                ],
                "Afecțiuni Hepatice și Gastrointestinale": [
                    "Hepatite virale cronice (B, C, D)",
                    "Ciroză hepatică",
                ],
                "Afecțiuni Reumatologice și Osoase": [
                    "Poliartrită reumatoidă și artrită psoriazică",
                    "Osteoporoză",
                    "Spondilită anchilozantă",
                ],
                "Boli Infecțioase și Autoimune": [
                    "Infecția cu HIV / SIDA",
                    "Lupus eritematos sistemic (LES)",
                ],
                "Alte Afecțiuni Cronice": [
                    "Boală cronică de rinichi (Insuficiență renală)",
                    "Glaucom",
                    "Afecțiuni stomatologice cronice (ex. Parodontoză)",
                ],
            }

            # 1. Extragem bolile într-o listă unică și o sortăm alfabetic
            lista_plata_afectiuni = []
            for boli_din_categorie in afectiuni_predefinite_dict.values():
                lista_plata_afectiuni.extend(boli_din_categorie)
            lista_plata_afectiuni.sort()

            # 2. Adăugăm "Altele" la finalul listei pentru logica ta custom
            optiuni_multiselect = lista_plata_afectiuni + ["Altele"]

            # 3. Randăm componenta multiselect cu noile date
            afectiuni_selectate = st.multiselect(
                "Suferiți în prezent de una sau mai dintre următoarele afecțiuni?",
                options=optiuni_multiselect,
                placeholder="Alege o opțiune",
                default=None,
                key="register_afectiuni",
            )

            altele_input = ""
            if "Altele" in afectiuni_selectate:
                altele_input = st.text_input(
                    "Specificați afecțiunea (separate prin virgulă):",
                    key="register_altele_input",
                )

            submit_register = st.form_submit_button(
                "Creează cont", type="primary", key="register_submit"
            )

        if submit_register:
            if not all(
                [nume, prenume, cnp, data_nasterii, email, sex, parola, confirma_parola]
            ):
                st.error(
                    "Completează toate câmpurile obligatorii, inclusiv data nașterii și sexul biologic."
                )
                return
            if len(cnp) != 13 or not cnp.isdigit():
                st.error("CNP-ul trebuie să aibă exact 13 cifre.")
                return
            if "@" not in email:
                st.error("Emailul introdus nu este valid.")
                return
            if parola != confirma_parola:
                st.error("Parolele nu coincid.")
                return
            if "Altele" in afectiuni_selectate and not altele_input.strip():
                st.error(
                    "Ați selectat 'Altele'. Vă rugăm să scrieți numele afecțiunii."
                )
                return

            afectiuni_finale = [af for af in afectiuni_selectate if af != "Altele"]
            if altele_input.strip():
                afectiuni_finale.extend(
                    [
                        a.strip().capitalize()
                        for a in altele_input.split(",")
                        if a.strip()
                    ]
                )

            form_data = {
                "nume": nume,
                "prenume": prenume,
                "cnp": cnp,
                "email": email,
                "sex": sex,
                "data_nasterii": data_nasterii.isoformat(),
                "parola": parola,
                "afectiuni": afectiuni_finale,
            }

            success, result = register_user(form_data)
            if success:
                st.session_state.authenticated = True
                st.session_state.current_user_id = result
                st.session_state.current_user = dict(get_user_by_id(result))
                st.session_state.logout_requested = False
                set_cookie_and_reload(result)
            else:
                st.error(result)


# ==========================================
# DEFINIREA GLOBALĂ A PAGINILOR (INSTANȚE STABILE)
# ==========================================

current_dir = os.path.dirname(os.path.abspath(__file__))
views_dir = os.path.join(current_dir, "views")

# 2. Parametrul `url_path` este OBLIGATORIU aici pentru a preveni ecranul alb pe Windows!
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
# ==========================================
# PUNCTUL DE INTRARE PRINCIPAL (ROUTER MODERN)
# ==========================================

ensure_auth_schema()
initialize_session_state()

if st.session_state.authenticated and st.session_state.current_user_id is not None:
    # 1. Ne asigurăm că avem datele utilizatorului încărcate
    if not st.session_state.current_user:
        date_utilizator = get_user_by_id(st.session_state.current_user_id)
        if date_utilizator:
            st.session_state.current_user = dict(date_utilizator)
        else:
            clear_cookie_and_reload()

    current_user = st.session_state.current_user
    pagini_autentificate = [pagina_evaluare, pagina_istoric, pagina_profil]

    # 2. Inițializăm navigația cu instanțele globale stabile
    nav = st.navigation(pagini_autentificate, position="hidden")

    # =========================================
    # CONSTRUIREA MANUALĂ A SIDEBAR-ULUI
    # =========================================
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

    # Rulăm instanța activă
    nav.run()

else:
    # Configurare navigație securizată pentru vizitatori
    nav = st.navigation([pagina_login], position="hidden")
    nav.run()
