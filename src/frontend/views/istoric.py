import streamlit as st
import pandas as pd
import datetime
import sys
import os
import sqlite3
from src.backend.db.db_connection import DatabaseConnection
from src.backend.core.pdf_generator import exporta_raport_pdf_pacient

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

current_user = st.session_state.current_user

st.title("📈 Istoric & Evoluție")
st.markdown("Urmărește evoluția biomarkerilor și descarcă rapoartele anterioare.")
st.markdown("---")

db_instance = DatabaseConnection()
conn = db_instance.connection
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

try:
    # 1. GENERARE GRAFICE DINAMICE
    st.subheader("📊 Analiza Evolutivă a Biomarkerilor")

    # Preluăm toți biomarkerii unici ai pacientului
    cursor.execute(
        """
        SELECT DISTINCT b.nume_biomarker 
        FROM Valori_Masurate vm
        JOIN Biomarkeri b ON vm.id_biomarker = b.id_biomarker
        JOIN Analize a ON vm.id_sesiune = a.id_sesiune
        WHERE a.id_utilizator = ? AND b.is_bool = 0
        ORDER BY b.nume_biomarker
    """,
        (current_user["id_utilizator"],),
    )
    lista_biomarkeri = [row["nume_biomarker"] for row in cursor.fetchall()]

    if lista_biomarkeri:
        biomarker_ales = st.selectbox(
            "Selectează biomarkerul pentru a vizualiza evoluția:", lista_biomarkeri
        )

        # Extragem valorile în timp pentru biomarkerul selectat
        cursor.execute(
            """
            SELECT a.data_recoltare, vm.val_mas 
            FROM Valori_Masurate vm
            JOIN Biomarkeri b ON vm.id_biomarker = b.id_biomarker
            JOIN Analize a ON vm.id_sesiune = a.id_sesiune
            WHERE a.id_utilizator = ? AND b.nume_biomarker = ?
            ORDER BY a.data_recoltare ASC
        """,
            (current_user["id_utilizator"], biomarker_ales),
        )
        date_grafic = cursor.fetchall()

        if len(date_grafic) > 0:
            df_grafic = pd.DataFrame([dict(r) for r in date_grafic])
            # Setăm data ca index pentru ca Streamlit să randeze axa X corect
            df_grafic.set_index("data_recoltare", inplace=True)
            df_grafic.rename(columns={"val_mas": biomarker_ales}, inplace=True)

            st.line_chart(df_grafic)
        else:
            st.info("Nu există suficiente date salvate pentru a desena un grafic.")
    else:
        st.info("Nu există analize numerice înregistrate pentru a genera grafice.")

    st.markdown("---")

    # 2. AFIȘAREA RAPOARTELOR PDF (Fără tabele brute)
    st.subheader("📁 Arhiva Rapoartelor Medicale (PDF)")

    cursor.execute(
        """
        SELECT a.id_sesiune, a.data_recoltare, a.raport_text, c.nume_clinica
        FROM Analize a
        JOIN Clinici c ON a.id_clinica = c.id_clinica
        WHERE a.id_utilizator = ? AND a.finalizata = 1
        ORDER BY a.data_recoltare DESC
    """,
        (current_user["id_utilizator"],),
    )
    sesiuni_salvate = cursor.fetchall()

    if not sesiuni_salvate:
        st.caption("Nu aveți nicio sesiune de analize salvată în istoric.")
    else:
        for sesiune in sesiuni_salvate:
            id_s = sesiune["id_sesiune"]
            data_rec_str = sesiune["data_recoltare"]
            nume_clinica = sesiune["nume_clinica"]
            raport_ai = sesiune["raport_text"]

            with st.expander(f"📋 Raport din {data_rec_str} ({nume_clinica})"):
                if raport_ai:
                    # Afișăm textul în interfață pentru citire rapidă
                    st.write(raport_ai)

                    # Buton pentru PDF
                    data_obj = datetime.datetime.strptime(
                        data_rec_str, "%Y-%m-%d"
                    ).date()
                    pdf_bytes = exporta_raport_pdf_pacient(
                        text_ai=raport_ai,
                        user_data=current_user,
                        clinica=nume_clinica,
                        data_rec=data_obj,
                    )

                    st.download_button(
                        label="📥 Descarcă Formatul PDF",
                        data=pdf_bytes,
                        file_name=f"Raport_MEDICODE_{data_rec_str}.pdf",
                        mime="application/pdf",
                        key=f"dl_pdf_{id_s}",
                    )
                else:
                    st.info("Această sesiune nu conține o interpretare AI generată.")

except Exception as err_istoric:
    st.error(f"Eroare la încărcarea istoricului: {err_istoric}")
