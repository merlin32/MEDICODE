import streamlit as st
import sqlite3
import sys
import os

# Acest bloc trebuie să fie prezent în FIECARE fișier din folderul "pages/"
# pentru ca acestea să poată vedea codul din "src/backend/"
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.backend.db.db_connection import DatabaseConnection #noqa: E402

def get_db_connection():
    db_instance = DatabaseConnection()
    conn = db_instance.connection
    conn.row_factory = sqlite3.Row
    return conn


current_user = st.session_state.current_user
conn = get_db_connection()
id_user = current_user["id_utilizator"]

st.markdown("### 👤 Informații Personale")
col_u1, col_u2 = st.columns(2)
with col_u1:
    st.write(
        f"**Pacient:** {current_user.get('nume', '')} {current_user.get('prenume', '')}"
    )
    email_curat = current_user.get("email", "").replace("@", "<span>@</span>")
    st.markdown(
        f"**Email:** <span style='color: inherit; text-decoration: none;'>{email_curat}</span>",
        unsafe_allow_html=True,
    )
with col_u2:
    st.write(f"**Sex Biologic:** {current_user.get('sex', '')}")
    st.write(f"**Data Nașterii:** {current_user.get('data_nasterii', '')}")

st.markdown("---")
st.markdown("### 🩺 Dosarul Meu de Afecțiuni")

try:
    afectiuni_salvate = conn.execute(
        "SELECT nume_afectiune, status FROM Utilizator_Afectiune WHERE id_utilizator = ?",
        (id_user,),
    ).fetchall()
except Exception:
    afectiuni_salvate = []

af_actuale = [a for a in afectiuni_salvate if a["status"] == "Actuală"]
af_vindecate = [a for a in afectiuni_salvate if a["status"] == "Vindecată"]

col_stanga, col_dreapta = st.columns(2)

with col_stanga:
    st.markdown("#### 🚨 Actuale")
    if not af_actuale:
        st.caption("Nicio afecțiune activă înregistrată.")
    else:
        for af in af_actuale:
            with st.container(border=True):
                st.write(f"**{af['nume_afectiune']}**")
                if st.button(
                    "Marchează ca Vindecat", key=f"btn_v_{af['nume_afectiune']}"
                ):
                    conn.execute(
                        "UPDATE Utilizator_Afectiune SET status = 'Vindecată' WHERE id_utilizator = ? AND nume_afectiune = ?",
                        (id_user, af["nume_afectiune"]),
                    )
                    conn.commit()
                    st.rerun()

with col_dreapta:
    st.markdown("#### ✅ Vindecate")
    if not af_vindecate:
        st.caption("Nicio afecțiune în remisie.")
    else:
        for af in af_vindecate:
            with st.container(border=True):
                st.write(f"**{af['nume_afectiune']}**")
                if st.button(
                    "Reactivează afecțiunea", key=f"btn_a_{af['nume_afectiune']}"
                ):
                    conn.execute(
                        "UPDATE Utilizator_Afectiune SET status = 'Actuală' WHERE id_utilizator = ? AND nume_afectiune = ?",
                        (id_user, af["nume_afectiune"]),
                    )
                    conn.commit()
                    st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

with st.expander("➕ Înregistrează o afecțiune nouă în istoric"):
    afectiuni_sugerate = {
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

    # 1. Extragem toate bolile din dicționar într-o singură listă plată
    lista_plata_afectiuni = []
    for boli_din_categorie in afectiuni_sugerate.values():
        lista_plata_afectiuni.extend(boli_din_categorie)

    # Opțional, dar recomandat: sortăm lista alfabetic pentru o căutare mai ușoară
    lista_plata_afectiuni.sort()

    # 2. Unim opțiunea manuală cu lista plată generată
    optiuni_dropdown = ["Altă afecțiune (Scrie mai jos)..."]
    optiuni_dropdown.extend(lista_plata_afectiuni)

    # 3. Trimitem lista corectă către componenta Streamlit
    af_selectata = st.selectbox(
        "Selectați afecțiunea:",
        options=optiuni_dropdown,
        index=None,
        placeholder="Alege o opțiune",
    )

    nume_afectiune_final = ""

    if af_selectata == "Altă afecțiune (Scrie mai jos)...":
        nume_afectiune_final = st.text_input("Numele afecțiunii medicale:")
    elif af_selectata:
        nume_afectiune_final = af_selectata

    stare_af = st.selectbox(
        "Status clinic:",
        ["Actuală", "Vindecată"],
        index=None,
        placeholder="Alege o opțiune",
    )

    if st.button("Adaugă în dosar", type="primary"):
        if not af_selectata:
            st.error("Vă rugăm să alegeți o afecțiune din listă.")
        elif not stare_af:
            st.error("Vă rugăm să selectați statusul clinic.")
        else:
            nume_af_curat = nume_afectiune_final.strip()
            if nume_af_curat:
                exista_deja = conn.execute(
                    "SELECT status FROM Utilizator_Afectiune WHERE id_utilizator = ? AND nume_afectiune = ?",
                    (id_user, nume_af_curat),
                ).fetchone()

                if exista_deja and exista_deja["status"] == stare_af:
                    st.error(
                        f"Afecțiunea '{nume_af_curat}' figurează deja cu statusul '{stare_af}'!"
                    )
                else:
                    conn.execute(
                        "INSERT OR IGNORE INTO Afectiuni (nume_afectiune) VALUES (?)",
                        [nume_af_curat],
                    )
                    if exista_deja:
                        conn.execute(
                            "UPDATE Utilizator_Afectiune SET status = ? WHERE id_utilizator = ? AND nume_afectiune = ?",
                            (stare_af, id_user, nume_af_curat),
                        )
                    else:
                        conn.execute(
                            "INSERT INTO Utilizator_Afectiune (id_utilizator, nume_afectiune, status) VALUES (?, ?, ?)",
                            (id_user, nume_af_curat, stare_af),
                        )
                    conn.commit()
                    st.success(f"Afecțiunea '{nume_af_curat}' a fost salvată!")
                    st.rerun()
            else:
                st.error("Numele afecțiunii nu poate fi lăsat gol.")
