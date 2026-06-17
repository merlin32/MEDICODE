import streamlit as st
import datetime
import tempfile
import os
import hashlib
import pypdfium2 as pdfium
import sys
from src.backend.agents.clinical_analyzer import ruleaza_analiza_avansata
from src.backend.core.pdf_generator import exporta_raport_pdf_pacient

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


if not st.session_state.get("authenticated", False) or not st.session_state.get(
    "current_user"
):
    st.stop()

current_user = st.session_state.current_user

st.title("🏥 MEDICODE")
st.subheader("AI Diagnostic & Tracking Dashboard")
st.warning(
    "⚠️ **DISCLAIMER:** Aplicația oferă informații educaționale bazate pe AI. Nu înlocuiește sfatul medicului."
)
st.markdown("---")

if not st.session_state.current_user.get("cheie_api_gemini"):
    st.warning("⚠️ **Nu ai configurat încă cheia API.**")
    st.markdown("Pentru a putea evalua analizele, te rugăm să îți configurezi contul:")
    # st.page_link face navigarea nativă și fluidă în aceeași fereastră
    st.page_link("views/profil.py", label="Mergi la Profilul Meu", icon="⚙️")
    st.stop()

st.markdown("### Încarcă buletinul de analize")


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
    "Înălțime (cm)", min_value=100, max_value=230, step=1, help="Introduceți înălțimea"
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
    "Formate acceptate: PDF, PNG, JPG, JPEG (Puteți selecta mai multe pagini)",
    type=["pdf", "png", "jpg", "jpeg"],
    accept_multiple_files=True,
)

if fisiere_incarcate:
    toate_fisierele_sunt_valide = True

    for fisier in fisiere_incarcate:
        extensie = fisier.name.split(".")[-1].lower()

        if extensie in ["png", "jpg", "jpeg"]:
            from src.backend.core.image_validator import verifica_calitate_imagine

            with tempfile.NamedTemporaryFile(
                delete=False, suffix=f".{extensie}"
            ) as tmp:
                tmp.write(fisier.getvalue())
                tmp_path = tmp.name

            este_valida, mesaj_eroare = verifica_calitate_imagine(tmp_path)
            os.remove(tmp_path)

            if not este_valida:
                toate_fisierele_sunt_valide = False
                st.warning(f"⚠️ **{fisier.name}**: {mesaj_eroare}")

    if toate_fisierele_sunt_valide:
        if st.button("🚀 Începe analiza", type="primary"):
            if not clinica_aleasa or (
                clinica_aleasa == "Alta clinica..." and not clinica_finala.strip()
            ):
                st.error(
                    "⚠️ Te rugăm să selectezi sau să introduci numele clinicii înainte de a începe analiza!"
                )
            else:
                if "paddle_incarcat" not in st.session_state:
                    with st.spinner(
                        "⚙️ Se inițializează motorul vizual avansat (PaddleOCR). Această operațiune durează mai mult la prima rulare..."
                    ):
                        # Importul modulului va declanșa încărcarea modelelor Paddle în memorie
                        from src.backend.core.ocr_engine import (
                            extrage_text_cu_paddle_local,
                        )

                        st.session_state.paddle_incarcat = True
                try:
                    toate_datele_ocr = []

                    for fisier in fisiere_incarcate:
                        extensie = fisier.name.split(".")[-1].lower()

                        with tempfile.NamedTemporaryFile(
                            delete=False, suffix=f".{extensie}"
                        ) as tmp:
                            tmp.write(fisier.getvalue())
                            cale_originala = tmp.name

                        try:
                            if extensie == "pdf":
                                from src.backend.core.ocr_engine import (
                                    extrage_text_nativ_pdf,
                                    extrage_date_structurate_local,
                                )
                                from src.backend.core.ai_extractor import (
                                    extrage_date_din_text,
                                    extrage_date_din_imagine,
                                )

                                with st.spinner(
                                    f"📄 Citim documentul PDF: {fisier.name}..."
                                ):
                                    text_brut = extrage_text_nativ_pdf(cale_originala)

                                    if len(text_brut.strip()) < 50:
                                        st.toast(
                                            "⚠️ PDF Scanat detectat! Trecem pe citire vizuală...",
                                            icon="🔄",
                                        )

                                        pdf = pdfium.PdfDocument(cale_originala)
                                        for i in range(len(pdf)):
                                            pagina = pdf[i]
                                            imagine_pil = pagina.render(
                                                scale=3
                                            ).to_pil()

                                            with tempfile.NamedTemporaryFile(
                                                delete=False, suffix=".jpg"
                                            ) as tmp_img:
                                                imagine_pil.save(tmp_img.name)
                                                tmp_img_path = tmp_img.name

                                            try:
                                                date_structurate = (
                                                    extrage_date_din_imagine(
                                                        tmp_img_path
                                                    )
                                                )
                                                if not date_structurate:
                                                    raise Exception(
                                                        "API-ul a returnat gol"
                                                    )
                                            except Exception as api_err:
                                                st.warning(
                                                    f"⚠️ Eroare API Cloud ({api_err}). Folosim OCR-ul local..."
                                                )
                                                from src.backend.core.ocr_engine import (
                                                    extrage_text_cu_paddle_local,
                                                )

                                                txt_local = (
                                                    extrage_text_cu_paddle_local(
                                                        tmp_img_path
                                                    )
                                                )
                                                date_structurate = (
                                                    extrage_date_structurate_local(
                                                        txt_local
                                                    )
                                                )

                                            toate_datele_ocr.extend(date_structurate)
                                            os.remove(tmp_img_path)
                                        pdf.close()

                                    else:
                                        try:
                                            date_structurate = extrage_date_din_text(
                                                text_brut
                                            )
                                            if not date_structurate:
                                                raise Exception("API-ul a returnat gol")
                                        except Exception:
                                            st.warning(
                                                "⚠️ Eroare 503 API Cloud - serviciu momentan indisponibil. Folosim Parser-ul local de rezervă..."
                                            )
                                            date_structurate = (
                                                extrage_date_structurate_local(
                                                    text_brut
                                                )
                                            )

                                        toate_datele_ocr.extend(date_structurate)

                            elif extensie in ["png", "jpg", "jpeg"]:
                                from src.backend.core.ai_extractor import (
                                    extrage_date_din_imagine,
                                )
                                from src.backend.core.ocr_engine import (
                                    extrage_text_cu_paddle_local,
                                    extrage_date_structurate_local,
                                )

                                with st.spinner(
                                    f"👁️ Analizăm vizual imaginea: {fisier.name}..."
                                ):
                                    try:
                                        date_structurate = extrage_date_din_imagine(
                                            cale_originala
                                        )
                                        if not date_structurate:
                                            raise Exception("API-ul a returnat gol")
                                    except Exception as e:
                                        st.warning(
                                            f"⚠️ Serviciul Cloud e offline.\n{e}.\nTrecem pe extragerea locală..."
                                        )
                                        text_local = extrage_text_cu_paddle_local(
                                            cale_originala
                                        )
                                        date_structurate = (
                                            extrage_date_structurate_local(text_local)
                                        )

                                    toate_datele_ocr.extend(date_structurate)

                        except Exception as e:
                            st.error(
                                f"Eroare la procesarea fișierului {fisier.name}: {e}"
                            )
                        finally:
                            if os.path.exists(cale_originala):
                                os.remove(cale_originala)

                    id_user_curent = current_user["id_utilizator"]
                    sex_user_curent = current_user["sex"]
                    data_rec_str = data_recoltare.strftime("%Y-%m-%d")

                    upload_hash = hashlib.sha256()
                    for fisier in fisiere_incarcate:
                        upload_hash.update(fisier.name.encode("utf-8"))
                        upload_hash.update(fisier.type.encode("utf-8"))
                        upload_hash.update(fisier.getvalue())
                    upload_hash_value = upload_hash.hexdigest()

                    from src.backend.db.inserare_BD import (
                        proceseaza_si_salveaza_buletin,
                        finalizeaza_analiza,
                    )

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

                    if not upload_allowed:
                        st.warning(
                            "⚠️ Acest fișier a fost deja încărcat și procesat cu succes anterior..."
                        )
                    else:
                        finalizeaza_analiza(id_sesiune)

                        if sesiune_reutilizata:
                            st.info("⚠️ Această sesiune de analize a fost reluată...")

                        biomarkeri_procesati = []

                        if len(rezultate_salvate) > 0:
                            for rez in rezultate_salvate:
                                val = rez["valoare"]
                                ref_min = rez["min"]
                                ref_max = rez["max"]
                                um = rez.get("um", "")
                                is_bool = rez.get("is_bool", 0)

                                stare = "OPTIM_VERDE"

                                if is_bool == 1:
                                    if val != ref_min:
                                        stare = "ANOMALIE_ROSU"
                                    text_val = (
                                        "Pozitiv/DA" if val == 1.0 else "Negativ/NU"
                                    )
                                    text_ref = (
                                        "Pozitiv/DA" if ref_min == 1.0 else "Negativ/NU"
                                    )
                                    text_afisat = f"{rez['nume']}: {text_val} (Referință: {text_ref})"
                                else:
                                    if val < ref_min:
                                        stare = "SCAZUT_ROSU"
                                    elif val > ref_max:
                                        stare = "CRESCUT_ROSU"
                                    else:
                                        interval = ref_max - ref_min
                                        if interval > 0:
                                            if (val - ref_min) / interval <= 0.05:
                                                stare = "BORDERLINE_MIN_GALBEN"
                                            elif (ref_max - val) / interval <= 0.05:
                                                stare = "BORDERLINE_MAX_GALBEN"
                                    text_afisat = f"{rez['nume']}: {val} {um} (Referință: {ref_min} - {ref_max})"

                                biomarkeri_procesati.append(
                                    {
                                        "nume": rez["nume"],
                                        "valoare": val,
                                        "ref_min": ref_min,
                                        "ref_max": ref_max,
                                        "um": um,
                                        "stare": stare,
                                        "text_afisat": text_afisat,
                                    }
                                )

                        st.markdown("### 🗣️ Ce înseamnă analizele tale?")

                        if len(rezultate_salvate) == 0:
                            st.info(
                                "Niciun biomarker din document nu a putut fi citit."
                            )
                        else:
                            with st.spinner(
                                "AI-ul formulează explicația simplificată..."
                            ):
                                text_explicativ_ai = ruleaza_analiza_avansata(
                                    pacient_id=current_user["id_utilizator"],
                                    id_sesiune=id_sesiune,
                                    greutate=greutate,
                                    inaltime=inaltime,
                                )
                                from src.backend.db.db_connection import (
                                    DatabaseConnection,
                                )

                                conn_db = DatabaseConnection().connection
                                conn_db.execute(
                                    "UPDATE Analize SET raport_text = ? WHERE id_sesiune = ?",
                                    (text_explicativ_ai, id_sesiune),
                                )
                                conn_db.commit()
                            st.success(
                                "Raportul tău medical a fost generat cu succes! Descarcă PDF-ul de mai jos."
                            )

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
                                file_name=f"Interpretare_{current_user['prenume']}_{current_user['nume']}_{data_recoltare}.pdf",
                                mime="application/pdf",
                                type="primary",
                            )
                except Exception as e:
                    import traceback

                    st.error(f"Eroare: {e}")
                    st.error(f"Traceback complet:\n{traceback.format_exc()}")
