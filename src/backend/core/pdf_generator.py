import os
import datetime
from fpdf import FPDF


def exporta_raport_pdf_pacient(text_ai, user_data, clinica, data_rec):
    text_ai = text_ai.replace("µ", "u").replace("\xb5", "u")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Navigăm sigur către folderul frontend plecând de la rădăcina proiectului
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
    frontend_dir = os.path.join(project_root, "src", "frontend")

    font_regular = os.path.join(frontend_dir, "fonts", "PlayfairDisplay-Regular.ttf")
    font_bold = os.path.join(frontend_dir, "fonts", "PlayfairDisplay-Bold.ttf")
    font_italic = os.path.join(frontend_dir, "fonts", "PlayfairDisplay-Italic.ttf")

    # Am eliminat parametrul 'uni=True' deoarece fpdf2 suportă caracterele speciale nativ
    pdf.add_font("PlayfairDisplay", "", font_regular)
    pdf.add_font("PlayfairDisplay", "B", font_bold)
    pdf.add_font("PlayfairDisplay", "I", font_italic)
    font_family = "PlayfairDisplay"

    # --- ANTET ---
    pdf.set_fill_color(41, 128, 185)
    pdf.rect(0, 0, 210, 30, "F")

    logo_path = os.path.join(frontend_dir, "assets", "logo.jpeg")
    if os.path.exists(logo_path):
        try:
            # Încercăm afișarea; dacă eșuează (ex: format corupt), ignorăm discret
            pdf.image(logo_path, x=10, y=5, w=20)
        except Exception:
            pass

    pdf.set_text_color(255, 255, 255)
    pdf.set_font(font_family, "B", 20)
    pdf.set_xy(35, 10)
    pdf.cell(0, 10, "MEDICODE", ln=False)

    pdf.set_font(font_family, "", 12)
    pdf.set_xy(35, 18)
    pdf.cell(0, 10, "Raport Medical Generat de Inteligența Artificială", ln=True)

    # --- DATE PACIENT ---
    pdf.set_y(35)
    pdf.set_text_color(44, 62, 80)
    pdf.set_font(font_family, "B", 11)

    nume_pacient = f"{user_data.get('nume', '')} {user_data.get('prenume', '')}"

    pdf.set_fill_color(240, 244, 248)  # Gri deschis
    pdf.rect(10, 35, 190, 25, "F")

    pdf.set_xy(12, 38)
    pdf.cell(90, 6, f"Pacient: {nume_pacient}", ln=False)
    pdf.cell(
        90,
        6,
        f"Data Generării: {datetime.date.today().strftime('%d/%m/%Y')}",
        ln=True,
        align="R",
    )

    pdf.set_x(12)
    pdf.set_font(font_family, "", 11)
    pdf.cell(90, 6, f"Laborator/Clinică: {clinica}", ln=False)
    pdf.cell(
        90, 6, f"Data Recoltării: {data_rec.strftime('%d/%m/%Y')}", ln=True, align="R"
    )

    pdf.ln(10)

    # --- TEXT AI ---
    pdf.set_text_color(0, 0, 0)
    pdf.set_font(font_family, size=11)
    text_curat = str(text_ai).encode("utf-8", errors="ignore").decode("utf-8")

    # Textul va fi justificat (align="J")
    try:
        pdf.multi_cell(0, 6, text_curat, align="J", markdown=True)
    except TypeError:
        # Fallback de siguranță în caz că versiunea de fpdf2 este mai veche
        pdf.multi_cell(0, 6, text_curat, align="J")

    # --- DISCLAIMER ---
    pdf.ln(15)
    pdf.set_text_color(127, 140, 141)
    pdf.set_font(font_family, "I", 9)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)

    disclaimer_text = (
        "AVERTISMENT MEDICAL: Acest document este un raport generat algoritmic de Inteligența Artificială "
        "și are un rol strict educațional. Informațiile prezentate NU reprezintă un diagnostic oficial "
        "și NU înlocuiesc o consultație medicală autorizată. Vă rugăm să prezentați acest document "
        "medicului curant."
    )
    pdf.multi_cell(0, 4, disclaimer_text, align="C")

    return bytes(pdf.output())
