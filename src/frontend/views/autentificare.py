import datetime
import hashlib
import os
import secrets
import sqlite3
import sys
import streamlit as st

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.backend.agents.clinical_analyzer import (  # noqa: E402
    normalizeaza_termen_medical,
)
from src.backend.db.db_connection import (  # noqa: E402
    DatabaseConnection,
    get_database_path,
)

try:
    from streamlit_cookies_controller import CookieController  # type: ignore

    cookie_controller = CookieController(key="medicode_cookies")
except ImportError:
    CookieController = None  # type: ignore
    cookie_controller = None

PBKDF2_ITERATIONS = 120_000


def get_db_connection():
    db_instance = DatabaseConnection()
    conn = db_instance.connection
    conn.row_factory = sqlite3.Row
    return conn


_DB_INITIALIZATA = False


def ensure_auth_schema():
    global _DB_INITIALIZATA
    if _DB_INITIALIZATA:
        return

    db_path = get_database_path()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        # Scriptul SQL complet, restructurat pentru execuție sigură (non-destructivă)
        script_structura_completa = """
        -- Tabel Utilizatori
        CREATE TABLE IF NOT EXISTS Utilizatori (
            id_utilizator INTEGER PRIMARY KEY AUTOINCREMENT,
            cnp TEXT UNIQUE NOT NULL CHECK (length(cnp) = 13 AND cnp NOT GLOB '*[^0-9]*'),
            nume TEXT NOT NULL,
            prenume TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL CHECK (email LIKE '%@%'),
            sex TEXT NOT NULL CHECK (sex IN ('F', 'M')),
            data_nasterii DATE NOT NULL,
            parola_hash TEXT NOT NULL,
            cheie_api_gemini TEXT
        );

        -- Tabel Clinici
        CREATE TABLE IF NOT EXISTS Clinici (
            id_clinica INTEGER PRIMARY KEY AUTOINCREMENT,
            nume_clinica TEXT UNIQUE NOT NULL
        );

        -- Tabel Analize (Sesiuni)
        CREATE TABLE IF NOT EXISTS Analize (
            id_sesiune INTEGER PRIMARY KEY AUTOINCREMENT,
            id_utilizator INTEGER NOT NULL,
            id_clinica INTEGER NOT NULL,
            data_recoltare DATE NOT NULL,
            upload_hash TEXT,
            finalizata INTEGER DEFAULT 0,
            raport_text TEXT,
            FOREIGN KEY (id_utilizator) REFERENCES Utilizatori(id_utilizator) ON DELETE CASCADE,
            FOREIGN KEY (id_clinica) REFERENCES Clinici(id_clinica)
        );

        -- Tabel Biomarkeri (Catalogul de Referință)
        CREATE TABLE IF NOT EXISTS Biomarkeri (
            id_biomarker INTEGER PRIMARY KEY AUTOINCREMENT,
            nume_biomarker TEXT NOT NULL,
            ref_max REAL NOT NULL,
            ref_min REAL NOT NULL,
            is_bool BOOLEAN NOT NULL
        );

        -- Tabel Valori_Masurate
        CREATE TABLE IF NOT EXISTS Valori_Masurate (
            id_sesiune INTEGER NOT NULL,
            id_biomarker INTEGER NOT NULL,
            val_mas REAL NOT NULL,
            unit_mas TEXT NOT NULL,
            PRIMARY KEY (id_sesiune, id_biomarker),
            FOREIGN KEY (id_sesiune) REFERENCES Analize(id_sesiune) ON DELETE CASCADE,
            FOREIGN KEY (id_biomarker) REFERENCES Biomarkeri(id_biomarker) ON DELETE RESTRICT
        );

        -- Tabel Afectiuni (Catalogul General)
        CREATE TABLE IF NOT EXISTS Afectiuni (
            nume_afectiune TEXT PRIMARY KEY,
            descriere_generala TEXT
        );

        -- Tabel Asociativ: Utilizator_Afectiune (Relație M-M)
        CREATE TABLE IF NOT EXISTS Utilizator_Afectiune (
            id_utilizator INTEGER NOT NULL,
            nume_afectiune TEXT NOT NULL,
            status TEXT,
            PRIMARY KEY (id_utilizator, nume_afectiune),
            FOREIGN KEY (id_utilizator) REFERENCES Utilizatori(id_utilizator) ON DELETE CASCADE,
            FOREIGN KEY (nume_afectiune) REFERENCES Afectiuni(nume_afectiune) ON DELETE CASCADE
        );

        -- Creare indecși în mod securizat pentru optimizarea vitezei de căutare
        CREATE UNIQUE INDEX IF NOT EXISTS idx_analize_upload_hash ON Analize(id_utilizator, upload_hash);
        CREATE INDEX IF NOT EXISTS idx_utilizatori_email ON Utilizatori(email);
        CREATE INDEX IF NOT EXISTS idx_utilizatori_nume_prenume ON Utilizatori(nume, prenume);
        CREATE INDEX IF NOT EXISTS idx_analize_utilizator ON Analize(id_utilizator);
        CREATE INDEX IF NOT EXISTS idx_clinici_analize ON Clinici(id_clinica);
        """

        conn.executescript(script_structura_completa)

        columns_utilizatori = {
            row[1] for row in conn.execute("PRAGMA table_info(Utilizatori)").fetchall()
        }
        if "cheie_api_gemini" not in columns_utilizatori:
            conn.execute("ALTER TABLE Utilizatori ADD COLUMN cheie_api_gemini TEXT")

        columns_analize = {
            row[1] for row in conn.execute("PRAGMA table_info(Analize)").fetchall()
        }
        if "upload_hash" not in columns_analize:
            conn.execute("ALTER TABLE Analize ADD COLUMN upload_hash TEXT")
        if "finalizata" not in columns_analize:
            conn.execute("ALTER TABLE Analize ADD COLUMN finalizata INTEGER DEFAULT 0")
        if "raport_text" not in columns_analize:
            conn.execute("ALTER TABLE Analize ADD COLUMN raport_text TEXT")

        conn.commit()
        print(
            "[✅] Arhitectura bazei de date MEDICODE a fost validată și inițializată cu succes."
        )
        _DB_INITIALIZATA = True

    except Exception as e:
        print(f"[❌] Eroare critică la inițializarea structurii bazei de date: {e}")
    finally:
        conn.close()


def hash_password(password):
    derived_key = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), b"medicode", PBKDF2_ITERATIONS
    )
    return derived_key.hex()


def verify_password(password, expected_hash):
    calculated_hash = hash_password(password)
    return secrets.compare_digest(calculated_hash, expected_hash)


def get_user_by_email(email):
    conn = get_db_connection()
    return conn.execute(
        "SELECT * FROM Utilizatori WHERE lower(email) = lower(?)", (email.strip(),)
    ).fetchone()


def get_user_by_id(user_id):
    conn = get_db_connection()
    return conn.execute(
        "SELECT * FROM Utilizatori WHERE id_utilizator = ?", (user_id,)
    ).fetchone()


def get_saved_user_id():
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
        except Exception:
            pass
    return None


def set_cookie_and_reload(user_id):
    st.session_state.logout_requested = False
    st.session_state.authenticated = True
    st.session_state.current_user_id = int(user_id)
    user_data = get_user_by_id(user_id)
    if user_data:
        st.session_state.current_user = dict(user_data)
    st.session_state.pending_cookie = user_id
    st.rerun()


def clear_cookie_and_reload():
    st.session_state.authenticated = False
    st.session_state.current_user_id = None
    st.session_state.current_user = None
    st.query_params.clear()
    st.session_state.clear_cookie_on_next_run = True
    st.session_state.logout_requested = True

    if cookie_controller:
        try:
            cookie_controller.remove("medicode_user_id")
        except Exception:
            pass

    st.rerun()


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
                "Acest utilizator area deja un cont activ. Te poți conecta direct.",
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
                "INSERT OR IGNORE INTO Utilizator_Afectiune (id_utilizator, nume_afectiune, status) VALUES (?, ?, ?)",
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


def initialize_session_state():
    is_logging_out = st.session_state.get("clear_cookie_on_next_run", False)
    if is_logging_out:
        if cookie_controller:
            try:
                cookie_controller.remove("medicode_user_id")
            except Exception:
                pass
        st.session_state.clear_cookie_on_next_run = False

    if "pending_cookie" in st.session_state:
        if cookie_controller:
            try:
                cookie_controller.set(
                    "medicode_user_id", str(st.session_state.pending_cookie), path="/"
                )
            except Exception:
                pass
        del st.session_state["pending_cookie"]

    st.session_state.setdefault("logout_requested", False)
    st.session_state.setdefault("authenticated", False)
    st.session_state.setdefault("current_user_id", None)
    st.session_state.setdefault("current_user", None)
    st.session_state.setdefault("auth_tab_index", 0)

    if (
        not st.session_state.authenticated
        and not st.session_state.logout_requested
        and not is_logging_out
    ):
        saved_id = get_saved_user_id()
        if saved_id and str(saved_id).strip() not in ["", "None"]:
            st.session_state.authenticated = True
            st.session_state.current_user_id = int(saved_id)


def render_auth_page():
    st.title("🏥 MEDICODE")
    st.subheader("Autentificare pacient")

    st.markdown(
        """<style>[data-testid="stSidebar"] { display: none !important; } [data-testid="collapsedControl"] { display: none !important; }</style>""",
        unsafe_allow_html=True,
    )

    action = st.radio(
        "Alegeți acțiunea:",
        ["Conectare", "Înregistrare"],
        horizontal=True,
        index=st.session_state.auth_tab_index,
    )
    st.session_state.auth_tab_index = 0 if action == "Conectare" else 1

    if action == "Conectare":
        with st.form("login_form", clear_on_submit=False):
            email = st.text_input("Email", key="login_email")
            parola = st.text_input("Parolă", type="password", key="login_parola")
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
                max_value=datetime.date.today(),
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
                    "Diabet zaharat (Tip 1)",
                    "Diabet zaharat (Tip 2)",
                    "Obezitate",
                    "Sindrom metabolic",
                    "Hipotiroidism",
                    "Hipertiroidism",
                ],
                "Afecțiuni Respiratorii": [
                    "Astm bronșic",
                    "Boală pulmonară obstructivă cronică (BPOC)",
                ],
                "Afecțiuni Neurologice și Psihice": [
                    "Boala Alzheimer",
                    "Boala Parkinson",
                    "Scleroză multiplă",
                    "Epilepsie",
                    "Tulburări de anxietate",
                    "Tulburări depresive",
                ],
                "Afecțiuni Oncologice": [
                    "Cancer pulmonar",
                    "Cancer colorectal",
                    "Cancer mamar",
                    "Cancer de prostată",
                ],
                "Afecțiuni Hepatice și Gastrointestinale": [
                    "Hepatita B",
                    "Hepatita C",
                    "Hepatita D",
                    "Ciroză hepatică",
                ],
                "Afecțiuni Reumatologice și Osoase": [
                    "Poliartrită reumatoidă",
                    "Artrită psoriazică",
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
                    "Parodontoză",
                ],
            }

            lista_plata_afectiuni = []
            for boli_din_categorie in afectiuni_predefinite_dict.values():
                lista_plata_afectiuni.extend(boli_din_categorie)
            lista_plata_afectiuni.sort()

            optiuni_multiselect = lista_plata_afectiuni + ["Altele"]
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
                afectiuni_introduse = [
                    a.strip() for a in altele_input.split(",") if a.strip()
                ]
                with st.spinner(
                    "🧠 AI-ul analizează și standardizează termenii medicali introduși..."
                ):
                    for af_brut in afectiuni_introduse:
                        af_normalizat = normalizeaza_termen_medical(af_brut)
                        afectiuni_finale.append(af_normalizat)

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
                st.success(
                    "✅ Contul a fost creat cu succes! Te redirecționăm la Conectare..."
                )
                import time

                time.sleep(5)

                st.session_state.auth_tab_index = 0
                st.rerun()
            else:
                st.error(result)
