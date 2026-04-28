import hashlib
import os
import secrets
import sqlite3
import time

import pandas as pd
import streamlit as st

from db_connection import DatabaseConnection
import tempfile
import datetime
from demo_paddleocr import extrage_text_cu_paddle, extrage_date_structurate
from inserare_BD import proceseaza_si_salveaza_buletin
from anomalies_detector.anomalies_detector import genereaza_raport_json


st.set_page_config(page_title="MEDICODE", page_icon="🏥", layout="centered")

PBKDF2_ITERATIONS = 120_000


def get_db_connection():
    db_instance = DatabaseConnection()
    conn = db_instance.connection
    conn.row_factory = sqlite3.Row
    return conn


def ensure_auth_schema():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, 'database', 'MEDICODE')
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    try:
        existing_columns = {row[1] for row in conn.execute("PRAGMA table_info(Utilizatori)").fetchall()}

        if "parola_hash" not in existing_columns:
            conn.execute("ALTER TABLE Utilizatori ADD COLUMN parola_hash TEXT")

        conn.execute("DROP TABLE IF EXISTS Utilizator_Conturi")
        conn.commit()
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
        """
        SELECT *
        FROM Utilizatori
        WHERE lower(email) = lower(?)
        """,
        (email.strip(),),
    ).fetchone()


def get_user_by_id(user_id):
    conn = get_db_connection()
    return conn.execute(
        """
        SELECT *
        FROM Utilizatori
        WHERE id_utilizator = ?
        """,
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
            return False, "Există deja un cont cu acest email, dar CNP-ul introdus nu corespunde."

        if existing_user["parola_hash"]:
            return False, "Acest utilizator are deja un cont activ. Te poți conecta direct."

        conn.execute(
            """
            UPDATE Utilizatori
            SET parola_hash = ?
            WHERE id_utilizator = ?
            """,
            (password_hash, existing_user["id_utilizator"]),
        )
        conn.commit()
        return True, existing_user["id_utilizator"]

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
    conn.commit()
    return True, cursor.lastrowid


def login_user(email, password):
    user = get_user_by_email(email)
    if user is None or user["parola_hash"] is None:
        return False, "Nu există un cont activ pentru acest email."

    if not verify_password(password, user["parola_hash"]):
        return False, "Parolă incorectă."

    return True, user["id_utilizator"]


def initialize_session_state():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "current_user_id" not in st.session_state:
        st.session_state.current_user_id = None
    if "current_user" not in st.session_state:
        st.session_state.current_user = None


def rerun_app():
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()


def logout():
    st.session_state.authenticated = False
    st.session_state.current_user_id = None
    st.session_state.current_user = None
    rerun_app()


def render_dashboard():
    current_user = st.session_state.current_user or {}

    st.sidebar.success(f"Conectat ca {current_user.get('prenume', '')} {current_user.get('nume', '')}".strip())
    if st.sidebar.button("Deconectare"):
        logout()

    st.title("🏥 MEDICODE")
    st.subheader("AI Diagnostic & Tracking Dashboard")

    st.warning("⚠️ **DISCLAIMER:** Aplicația oferă informații educaționale bazate pe AI. Nu înlocuiește sfatul medicului.")

    tab1, tab2 = st.tabs(["📄 1. Încărcare & Evaluare", "📈 2. Istoric Medical"])

    with tab1:
        st.markdown("### Încarcă buletinul de analize")
        data_recoltare = st.date_input("Data Recoltării (cum apare pe foaie):", datetime.date.today())
        
        fisiere_incarcate = st.file_uploader(
            "Formate acceptate: PDF, PNG, JPG (Puteți selecta mai multe pagini)", 
            type=["pdf", "png", "jpg"], 
            accept_multiple_files=True
        )

        if fisiere_incarcate:
            if st.button("🚀 Începe analiza", type="primary"):
                with st.spinner("Procesăm documentele, evaluăm medical și actualizăm baza de date..."):
                    try:
                        toate_datele_ocr = []
                        
                        # 1. OCR
                        for fisier in fisiere_incarcate:
                            extensie = fisier.name.split('.')[-1]
                            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{extensie}") as tmp:
                                tmp.write(fisier.getvalue())
                                tmp_path = tmp.name
                            
                            text_brut = extrage_text_cu_paddle(tmp_path)
                            date_structurate = extrage_date_structurate(text_brut)
                            toate_datele_ocr.extend(date_structurate)
                            os.remove(tmp_path)

                        # 2. Salvare BD & Obținere Evaluare Culori
                        id_user_curent = current_user['id_utilizator']
                        sex_user_curent = current_user['sex']
                        data_rec_str = data_recoltare.strftime("%Y-%m-%d")
                        
                        rezultate_salvate = proceseaza_si_salveaza_buletin(id_user_curent, sex_user_curent, data_rec_str, toate_datele_ocr)

                        # 3. Rulare script anomalies_detector pentru a genera raportul JSON cu alertele globale
                        genereaza_raport_json()

                        # 4. Afișarea în interfață cu Roșu/Galben/Verde
                        st.success(f"✅ Analiză finalizată! Am extras și salvat {len(rezultate_salvate)} rezultate medicale.")
                        st.markdown("---")
                        st.markdown("### 📊 Rezultatele Analizei Curente")

                        if len(rezultate_salvate) == 0:
                            st.info("Niciun biomarker din document nu a făcut match cu baza de date.")
                        else:
                            for rez in rezultate_salvate:
                                text_afisat = f"**{rez['nume']}**: {rez['valoare']} {rez['um']} *(Referință: {rez['min']} - {rez['max']})*"
                                
                                if rez['stare'] == "OPTIM_VERDE":
                                    st.success(f"✅ {text_afisat} ➔ 🟢 **OPTIM**")
                                    
                                elif rez['stare'] == "BORDERLINE_MIN_GALBEN":
                                    st.warning(f"⚠️ {text_afisat} ➔ 🟡 **APROAPE DE LIMITA INFERIOARĂ**")
                                    
                                elif rez['stare'] == "BORDERLINE_MAX_GALBEN":
                                    st.warning(f"⚠️ {text_afisat} ➔ 🟡 **APROAPE DE LIMITA SUPERIOARĂ**")
                                    
                                elif rez['stare'] == "SCAZUT_ROSU":
                                    st.error(f"📉 {text_afisat} ➔ 🔴 **ANOMALIE: SCĂZUT**")
                                    
                                elif rez['stare'] == "CRESCUT_ROSU":
                                    st.error(f"📈 {text_afisat} ➔ 🔴 **ANOMALIE: CRESCUT**")
                                
                    except Exception as e:
                        st.error(f"A intervenit o problemă: {e}")

    with tab2:
        st.markdown("### 📈 Evoluția Biomarkerilor")
        st.markdown("Selectează un biomarker pentru a vedea tendința din ultimele luni.")

        date_istoric = pd.DataFrame(
            {
                "Glicemie (mg/dL)": [95, 105, 115],
                "Sideremie (µg/dL)": [80, 60, 45],
            },
            index=["Octombrie 2025", "Decembrie 2025", "Februarie 2026"],
        )

        st.line_chart(date_istoric)

        st.markdown("#### 📁 Sesiuni anterioare (Sânge)")
        with st.expander("Sesiune - Decembrie 2025"):
            st.write("Aici vei putea vedea detaliile vechi preluate din SQLite.")
        with st.expander("Sesiune - Octombrie 2025"):
            st.write("Toate valorile au fost în limite normale.")


def render_auth_page():
    st.title("🏥 MEDICODE")
    st.subheader("Autentificare")
    st.write("Creează un cont nou sau conectează-te pentru a continua către panoul medical.")

    action = st.radio("Alege acțiunea", ["Conectare", "Înregistrare"], horizontal=True)

    if action == "Conectare":
        with st.form("login_form"):
            email = st.text_input("Email")
            parola = st.text_input("Parolă", type="password")
            submitted = st.form_submit_button("Conectează-te")

        if submitted:
            if not email or not parola:
                st.error("Completează emailul și parola.")
                return

            success, result = login_user(email, parola)
            if success:
                st.session_state.authenticated = True
                st.session_state.current_user_id = result
                st.session_state.current_user = dict(get_user_by_id(result))
                st.success("Autentificare reușită.")
                rerun_app()

            st.error(result)

    else:
        with st.form("register_form"):
            col1, col2 = st.columns(2)
            with col1:
                nume = st.text_input("Nume")
                cnp = st.text_input("CNP")
                sex = st.selectbox("Sex", ["M", "F"])
            with col2:
                prenume = st.text_input("Prenume")
                data_nasterii = st.date_input("Data nașterii")
                email = st.text_input("Email")

            parola = st.text_input("Parolă", type="password")
            confirma_parola = st.text_input("Confirmă parola", type="password")
            submitted = st.form_submit_button("Creează cont")

        if submitted:
            if not all([nume, prenume, cnp, email, parola, confirma_parola]):
                st.error("Completează toate câmpurile obligatorii.")
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

            form_data = {
                "nume": nume,
                "prenume": prenume,
                "cnp": cnp,
                "email": email,
                "sex": sex,
                "data_nasterii": data_nasterii.isoformat(),
                "parola": parola,
            }

            success, result = register_user(form_data)
            if success:
                st.session_state.authenticated = True
                st.session_state.current_user_id = result
                st.session_state.current_user = dict(get_user_by_id(result))
                st.success("Cont creat și utilizator autentificat.")
                rerun_app()

            st.error(result)


ensure_auth_schema()
initialize_session_state()

if st.session_state.authenticated and st.session_state.current_user_id is not None:
    st.session_state.current_user = dict(get_user_by_id(st.session_state.current_user_id))
    render_dashboard()
else:
    render_auth_page()
