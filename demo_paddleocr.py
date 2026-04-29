from paddleocr import PaddleOCR
import pypdfium2 as pdfium
import numpy as np
import re
import json
import os
from datetime import datetime

FISIER_TEST = "teste/test1.pdf"  # Fisierele trebuie sa fie de tip: .pdf, .jpg, .png

print("[0/3] Incarcare modele neuronale PaddleOCR...")
ocr = PaddleOCR(use_angle_cls=True, lang="ro", show_log=False)


def extrage_text_cu_paddle(cale_fisier):
    """Citeste imagini sau PDF-uri folosind Deep Learning si returneaza textul brut."""
    print(f"[1/3] Rulare PaddleOCR pe documentul: {cale_fisier}...")
    text_brut = ""

    if cale_fisier.lower().endswith(".pdf"):
        pdf = pdfium.PdfDocument(cale_fisier)

        for index_pagina in range(len(pdf)):
            print(f"      -> Procesez pagina {index_pagina + 1} din {len(pdf)}...")
            pagina = pdf[index_pagina]

            imagine_pil = pagina.render(scale=4).to_pil()

            imagine_np = np.array(imagine_pil)

            rezultate = ocr.ocr(imagine_np)
            if rezultate and rezultate[0] is not None:
                for linie in rezultate[0]:
                    text_gasit = linie[1][0]
                    text_brut += text_gasit + "\n"
        pdf.close()
    else:
        rezultate = ocr.ocr(cale_fisier)
        if rezultate and rezultate[0] is not None:
            for linie in rezultate[0]:
                text_gasit = linie[1][0]
                text_brut += text_gasit + "\n"

    return text_brut


def extrage_date_structurate(text_brut):
    """Parseaza textul extras de PaddleOCR unde datele sunt una sub alta."""
    print("[2/3] Parsare text (Algoritm Multiline pt Tabele)...")
    rezultate = []

    linii = [linie.strip() for linie in text_brut.split("\n") if linie.strip()]

    i = 0
    while i < len(linii) - 2:
        nume_curent = linii[i]

        nume_upper = nume_curent.upper()
        if len(nume_curent) < 4 or any(
            x in nume_upper
            for x in [
                "MEDICALE",
                "PAGINA",
                "BULETIN",
                "DATA",
                "NUME",
                "ANALIZA",
                "REZULTAT",
            ]
        ):
            i += 1
            continue

        if re.search(r"^[-a-zA-Z\(\*\d]", nume_curent):
            linie_curatata = linii[i + 1].replace("10^", " 10^")
            urmatoarea_linie = re.sub(r"(\d)10([36])", r"\1 10^\2", linie_curatata)
            a_treia_linie = linii[i + 2]

            match_valoare = re.search(
                r"([<>]?\d+[\.,]?\d*)(?:\s*10\^|\s*[a-zA-Z/%])?", urmatoarea_linie
            )

            if match_valoare and (
                "-" in a_treia_linie
                or "/" in a_treia_linie
                or "ref" in a_treia_linie.lower()
                or "<" in a_treia_linie
                or ">" in a_treia_linie
            ):

                valoare_str = match_valoare.group(1).replace(",", ".")

                try:
                    valoare_num = float(valoare_str.replace("<", "").replace(">", ""))

                    rezultate.append(
                        {
                            "analiza": nume_curent,
                            "valoare_extrasa": urmatoarea_linie,
                            "valoare_numerica": valoare_num,
                            "referinta": a_treia_linie,
                        }
                    )
                    i += 3
                    continue
                except ValueError:
                    pass
        i += 1

    return rezultate


def extrage_date_pacient(text_brut):
    """Extrage datele personale din antetul buletinului de analize."""
    date_pacient = {
        "nume": "Necunoscut",
        "prenume": "Necunoscut",
        "cnp": None,
        "sex": None,
        "data_recoltare": datetime.now().strftime("%d/%m/%Y"),
        "data_nasterii": "1900-01-01",
    }

    # 1. Extragere CNP
    match_cnp = re.search(r"(?<!\d)([1-9]\d{12})(?!\d)", text_brut)
    if match_cnp:
        date_pacient["cnp"] = match_cnp.group(1)

        # Dedublam data nasterii din CNP
        an = int(date_pacient["cnp"][1:3])
        luna = date_pacient["cnp"][3:5]
        zi = date_pacient["cnp"][5:7]
        secol = 1900 if date_pacient["cnp"][0] in ["1", "2"] else 2000
        date_pacient["data_nasterii"] = f"{secol + an}-{luna}-{zi}"

    # 2. Extragere Sex
    match_sex = re.search(r"Sex[\s:]*([MF])", text_brut, re.IGNORECASE)
    if match_sex:
        date_pacient["sex"] = match_sex.group(1).upper()

    # 3. Extragere Data Recoltare / Cerere
    match_data = re.search(
        r"(?:recoltare|cerere)[\s:]*(\d{2}[./-]\d{2}[./-]\d{4})",
        text_brut,
        re.IGNORECASE,
    )
    if match_data:
        date_pacient["data_recoltare"] = (
            match_data.group(1).replace(".", "-").replace("/", "-")
        )

    # 4. Extragere Nume
    match_nume = re.search(
        r"Nume[\s:]*([A-Za-z\-]+)\s+([A-Za-z\-]+)", text_brut, re.IGNORECASE
    )
    if match_nume:
        date_pacient["nume"] = match_nume.group(1).capitalize()
        date_pacient["prenume"] = match_nume.group(2).capitalize()

    return date_pacient


# DEMO
if __name__ == "__main__":
    print("\n=== START DEMO PADDLE-OCR (IMG & PDF) ===")
    try:
        if not os.path.exists(FISIER_TEST):
            raise FileNotFoundError(f"Nu am gasit fisierul '{FISIER_TEST}'.")

        text_extras = extrage_text_cu_paddle(FISIER_TEST)

        # print(text_extras)

        date_finale = extrage_date_structurate(text_extras)
        date_pacient = extrage_date_pacient(text_extras)

        print("\n✅ SUCCES! Datele au fost structurate pentru Baza de Date:")
        print(json.dumps(date_pacient, indent=4, ensure_ascii=False))
        print(json.dumps(date_finale, indent=4, ensure_ascii=False))
        print("=== FINAL DEMO ===\n")

    except FileNotFoundError as e:
        print(f"❌ Eroare: {e}")
    except Exception as e:
        print(f"❌ A aparut o eroare neasteptata: {e}")
