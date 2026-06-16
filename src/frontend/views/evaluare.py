import streamlit as st
import datetime
import tempfile
import os
import hashlib
from fpdf import FPDF
import sys

# Acest bloc trebuie să fie prezent în FIECARE fișier din folderul "pages/"
# pentru ca acestea să poată vedea codul din "src/backend/"
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


current_user = st.session_state.current_user

st.title("🏥 MEDICODE")
st.subheader("AI Diagnostic & Tracking Dashboard")
st.warning(
    "⚠️ **DISCLAIMER:** Aplicația oferă informații educaționale bazate pe AI. Nu înlocuiește sfatul medicului."
)
st.markdown("---")


def exporta_raport_pdf_pacient(text_ai, user_data, clinica, data_rec):
    pdf = FPDF()
    pdf.add_page()

    # --- CALE DINAMICĂ CROSS-PLATFORM ---
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Construim rutele către folderul "fonts"
    font_regular = os.path.join(current_dir, "fonts", "PlayfairDisplay-Regular.ttf")
    font_bold = os.path.join(current_dir, "fonts", "PlayfairDisplay-Bold.ttf")
    font_italic = os.path.join(current_dir, "fonts", "PlayfairDisplay-Italic.ttf")

    # Încercăm să înregistrăm fonturile custom; dacă lipsesc, folosim un font
    # Unicode built-in (DejaVuSans) ca fallback care suportă caractere românești
    font_family = "PlayfairDisplay"
    fonts_exist = all(os.path.exists(p) for p in (font_regular, font_bold, font_italic))
    if fonts_exist:
        try:
            pdf.add_font("PlayfairDisplay", "", font_regular, uni=True)
            pdf.add_font("PlayfairDisplay", "B", font_bold, uni=True)
            pdf.add_font("PlayfairDisplay", "I", font_italic, uni=True)
        except Exception:
            fonts_exist = False

    if not fonts_exist:
        font_family = (
            "DejaVuSans"  # Font Unicode built-in care suportă caractere românești
        )

    # Titlu
    pdf.set_font(font_family, "B", 16)
    # Folosim strings normale (Python 3 tratează nativ UTF-8)
    pdf.cell(0, 10, "Explicația Analizelor Tale Medicale", ln=True, align="C")
    pdf.ln(5)

    # Detalii Pacient și Clinică
    # Detalii Pacient și Clinică
    pdf.set_font(font_family, size=11)
    pdf.cell(
        0,
        8,
        f"Pacient: {user_data.get('nume', '')} {user_data.get('prenume', '')}",
        ln=True,
    )
    pdf.cell(0, 8, f"Data Recoltării: {data_rec.strftime('%d/%m/%Y')}", ln=True)
    pdf.cell(0, 8, f"Clinica: {clinica}", ln=True)

    # --- REPARARE COORDONATE TĂIATE ---
    # Luăm poziția Y exactă unde s-a oprit ultimul text și adăugăm o mică marjă de 3mm
    y_dinamic = pdf.get_y() + 3

    # Tragem linia în mod sigur sub numele clinicii
    pdf.line(10, y_dinamic, 200, y_dinamic)

    # Lăsăm un spațiu curat de 10mm sub linie înainte să înceapă textul AI
    pdf.set_y(y_dinamic + 5)
    # ----------------------------------

    # Textul AI-ului (Explicativ)
    pdf.set_font(font_family, size=12)

    # IMPORTANT: Ne asigurăm că string-ul nu conține caractere ciudate de tip byte
    # și curățăm eventualele neconcordanțe de encodare din textul primit de la AI
    text_curat = str(text_ai).encode("utf-8", errors="ignore").decode("utf-8")
    pdf.multi_cell(0, 8, text_curat)

    # Disclaimer
    pdf.ln(15)
    pdf.set_font(font_family, "I", 10)

    disclaimer_text = (
        "DISCLAIMER: Acest document este generat de Inteligența Artificială cu rol strict educativ și explicativ. "
        "Nu înlocuiește în niciun caz consultul, diagnosticul sau tratamentul recomandat de un medic specialist."
    )
    pdf.multi_cell(0, 5, disclaimer_text)

    return bytes(pdf.output())


st.markdown("### Încarcă buletinul de analize")
# --- CÂMPURI BIOMETRICE ---
st.markdown("#### 🧬 Date despre pacient")
col_m1, col_m2 = st.columns(2)
greutate = col_m1.number_input(
    "Greutate (kg)",
    min_value=30.0,
    max_value=250.0,
    step=1.0,
    help="Introduceți greutatea",
)
inaltime = col_m2.number_input(
    "Înălțime (cm)",
    min_value=100,
    max_value=230,
    step=1,
    help="Introduceți înălțimea",
)

imc = 0.0
if greutate > 0 and inaltime > 0:
    imc = greutate / ((inaltime / 100) ** 2)
    st.session_state.temp_imc = imc

st.markdown("#### 🏥 Date despre analize")
clinici_list = [
    "Regina Maria",
    "MedLife",
    "Sanador",
    "Synevo",
    "Bioclinica",
    "Gral Medical",
    "Alta clinica...",
]
clinica_aleasa = st.selectbox(
    "Clinica unde s-au efectuat analizele:",
    options=clinici_list,
    index=None,
    placeholder="Alege clinica",
)

clinica_finala = clinica_aleasa
if clinica_aleasa == "Alta clinica...":
    clinica_finala = st.text_input("Introduceți numele clinicii:")

if not clinica_finala:
    clinica_finala = "Nespecificată"

data_recoltare = st.date_input(
    "Data recoltării (cum apare pe foaie):",
    min_value=datetime.date(1900, 1, 1),
    max_value=datetime.date.today(),
    value=datetime.date.today(),
    format="DD/MM/YYYY",
)

fisiere_incarcate = st.file_uploader(
    "Formate acceptate: PDF, PNG, JPG (Puteți încărca mai multe pagini)",
    type=["pdf", "png", "jpg"],
    accept_multiple_files=True,
)

if fisiere_incarcate:
    if st.button("🚀 Începe analiza", type="primary"):
        if not clinica_aleasa or (
            clinica_aleasa == "Alta clinica..." and not clinica_finala.strip()
        ):
            st.error(
                "⚠️ Te rugăm să selectezi sau să introduci numele clinicii înainte de a începe analiza!"
            )
        else:
            with st.spinner("Procesăm documentele medicale..."):
                try:
                    toate_datele_ocr = []

                    from src.backend.core.ocr_engine import (
                        extrage_date_structurate,
                        extrage_text_cu_paddle,
                    )

                    for fisier in fisiere_incarcate:
                        extensie = fisier.name.split(".")[-1]
                        with tempfile.NamedTemporaryFile(
                            delete=False, suffix=f".{extensie}"
                        ) as tmp:
                            tmp.write(fisier.getvalue())
                            tmp_path = tmp.name

                        text_brut = extrage_text_cu_paddle(tmp_path)
                        date_structurate = extrage_date_structurate(text_brut)
                        toate_datele_ocr.extend(date_structurate)
                        os.remove(tmp_path)

                    id_user_curent = current_user["id_utilizator"]
                    sex_user_curent = current_user["sex"]
                    data_rec_str = data_recoltare.strftime("%Y-%m-%d")

                    from src.backend.db.inserare_BD import (
                        proceseaza_si_salveaza_buletin,
                        finalizeaza_analiza,
                    )

                    upload_hash = hashlib.sha256()
                    for fisier in fisiere_incarcate:
                        upload_hash.update(fisier.name.encode("utf-8"))
                        upload_hash.update(fisier.type.encode("utf-8"))
                        upload_hash.update(fisier.getvalue())

                    upload_hash_value = upload_hash.hexdigest()

                    (
                        rezultate_salvate,
                        sesiune_reutilizata,
                        id_sesiune,
                        upload_allowed,
                    ) = proceseaza_si_salveaza_buletin(
                        id_user_curent,
                        data_rec_str,
                        toate_datele_ocr,
                        clinica_finala,
                        upload_hash=upload_hash_value,
                    )

                    # VERIFICARE DUPLICAT FINALIZAT - IESIRE DEVREME
                    if not upload_allowed:
                        st.warning(
                            "⚠️ Acest fișier a fost deja încărcat și procesat cu succes anterior. "
                            "Nu se pot reintroduce rezultatele duplicate."
                        )
                    else:
                        # CONTINUARE DOAR DACA NU E DUPLICAT FINALIZAT
                        from src.backend.core.anomalies_detector import (
                            genereaza_raport_json,
                        )

                        genereaza_raport_json()
                        finalizeaza_analiza(id_sesiune)

                        if sesiune_reutilizata:
                            st.info(
                                "⚠️ Această sesiune de analize a fost reluată după un upload anterior nereușit. Datele vechi au fost înlocuite și nu vor fi dublate."
                            )
                        else:
                            st.success(
                                f"✅ Analiză finalizată! Am extras {len(rezultate_salvate)} biomarkeri."
                            )
                        st.markdown("---")

                        # --- GENERAREA TEXTULUI EXPLICATIV (AI) ---
                        st.markdown("### 🗣️ Ce înseamnă analizele tale?")

                        if len(rezultate_salvate) == 0:
                            st.info(
                                "Niciun biomarker din document nu a putut fi citit."
                            )
                        else:
                            with st.spinner(
                                "AI-ul formulează explicația simplificată..."
                            ):
                                # AICI ADAUGI APELUL CĂTRE AI-UL TĂU.
                                # Exemplu: text_explicativ_ai = genereaza_explicatie_pacient(rezultate_salvate)

                                # Acesta este un text mock temporar până legi funcția reală AI:
                                text_explicativ_ai = "Analizele tale arată în general bine. Glicemia este în limite normale, ceea ce înseamnă că organismul tău procesează corect zahărul. Am observat însă că fierul (sideremia) este puțin sub limita de jos, ceea ce îți poate da uneori o stare de oboseală. Celulele albe sunt la nivel normal, deci nu există semne de infecție."
                            st.write(text_explicativ_ai)

                            # --- EXPORT PDF ---
                            st.markdown("<br>", unsafe_allow_html=True)
                            pdf_bytes = exporta_raport_pdf_pacient(
                                text_ai=text_explicativ_ai,
                                user_data=current_user,
                                clinica=clinica_finala,
                                data_rec=data_recoltare,
                            )

                            st.download_button(
                                label="📥 Descarcă Explicația (PDF)",
                                data=pdf_bytes,
                                file_name=f"Rezultate_Explicate_{current_user['prenume']}_{data_recoltare}.pdf",
                                mime="application/pdf",
                                type="primary",
                            )
                except Exception as e:
                    st.error(f"Eroare: {e}")
